# -*- coding: utf-8 -*-
"""
메시지 필터링 유틸리티

본문 내용 중복 제거, TO/CC/BCC 우선순위 필터링, 짧은 메시지/단순 인사/업데이트 필터링
"""
import logging
import hashlib
from typing import List, Dict, Any, Set, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)


def filter_duplicate_content(messages: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], int]:
    """본문 내용 중복 제거
    
    같은 본문 내용을 가진 메시지는 하나만 유지합니다.
    발신자가 다르더라도 내용이 같으면 중복으로 간주합니다.
    body가 비어있으면 subject를 사용합니다.
    
    Args:
        messages: 메시지 리스트
        
    Returns:
        (필터링된 메시지 리스트, 제거된 메시지 수)
    """
    seen_content_hashes: Set[str] = set()
    filtered_messages = []
    removed_count = 0
    
    for message in messages:
        # 본문 내용 추출 (body가 비어있으면 subject 사용)
        content = (message.get("body") or message.get("content") or "").strip()
        subject = (message.get("subject") or "").strip()
        
        # body가 비어있으면 subject를 content로 사용
        if not content and subject:
            content = subject
        
        if not content:
            # 내용도 제목도 없으면 그대로 유지
            filtered_messages.append(message)
            continue
        
        # 본문 해시 생성 (SHA256)
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        
        if content_hash in seen_content_hashes:
            # 중복 내용
            removed_count += 1
            logger.debug(
                f"본문 중복 제거: msg_id={message.get('msg_id')}, "
                f"sender={message.get('sender')}, content={content[:50]}..."
            )
        else:
            # 새로운 내용
            seen_content_hashes.add(content_hash)
            filtered_messages.append(message)
    
    if removed_count > 0:
        logger.info(f"📝 본문 내용 중복 제거: {removed_count}개 제거")
    
    return filtered_messages, removed_count


def filter_by_recipient_type(messages: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """TO/CC/BCC 우선순위 기반 중복 제거
    
    같은 발신자(sender) + 같은 제목(subject)을 가진 메시지 중
    TO > CC > BCC 우선순위로 하나만 유지합니다.
    
    Args:
        messages: 메시지 리스트
        
    Returns:
        (필터링된 메시지 리스트, 통계 딕셔너리)
        통계: {"to_kept": int, "cc_kept": int, "bcc_kept": int, "removed": int}
    """
    PRIORITY_ORDER = {"to": 3, "cc": 2, "bcc": 1}
    
    # 발신자 + 제목으로 그룹화
    groups: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    
    for message in messages:
        sender = message.get("sender", "")
        subject = message.get("subject", "")
        
        # 이메일만 필터링 (채팅 메시지는 제외)
        if message.get("platform") != "email":
            groups[(sender, subject)].append(message)
            continue
        
        # 발신자 + 제목으로 그룹화
        key = (sender, subject)
        groups[key].append(message)
    
    # 각 그룹에서 우선순위가 가장 높은 메시지 선택
    filtered_messages = []
    stats = {"to_kept": 0, "cc_kept": 0, "bcc_kept": 0, "removed": 0}
    
    for (sender, subject), group in groups.items():
        if len(group) == 1:
            # 그룹에 메시지가 하나만 있으면 그대로 유지
            filtered_messages.append(group[0])
            recipient_type = group[0].get("recipient_type", "to").lower()
            if recipient_type in stats:
                stats[f"{recipient_type}_kept"] += 1
        else:
            # 여러 메시지가 있으면 우선순위로 선택
            # recipient_type 기준으로 정렬 (TO > CC > BCC)
            sorted_group = sorted(
                group,
                key=lambda m: PRIORITY_ORDER.get(m.get("recipient_type", "to").lower(), 0),
                reverse=True
            )
            
            # 가장 우선순위가 높은 메시지 선택
            selected = sorted_group[0]
            filtered_messages.append(selected)
            
            recipient_type = selected.get("recipient_type", "to").lower()
            if recipient_type in stats:
                stats[f"{recipient_type}_kept"] += 1
            
            # 제거된 메시지 수 계산
            removed = len(group) - 1
            stats["removed"] += removed
            
            if removed > 0:
                logger.debug(
                    f"TO/CC/BCC 중복 제거: sender={sender}, subject={subject[:30]}, "
                    f"kept={recipient_type.upper()}, removed={removed}개"
                )
    
    if stats["removed"] > 0:
        logger.info(
            f"📧 TO/CC/BCC 중복 제거: {stats['removed']}개 제거 "
            f"(TO {stats['to_kept']}개, CC {stats['cc_kept']}개, BCC {stats['bcc_kept']}개 유지)"
        )
    
    return filtered_messages, stats


def filter_short_and_simple_messages(messages: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """짧은 메시지, 단순 인사말, 단순 업데이트 필터링
    
    Args:
        messages: 메시지 리스트
        
    Returns:
        (필터링된 메시지 리스트, 통계 딕셔너리)
        통계: {"too_short": int, "simple_greeting": int, "simple_update": int}
    """
    filtered_messages = []
    stats = {"too_short": 0, "simple_greeting": 0, "simple_update": 0}
    
    # 단순 인사말 패턴
    GREETING_PATTERNS = [
        "안녕하세요", "감사합니다", "수고하세요", "고생하셨습니다",
        "hello", "hi", "thanks", "thank you", "good morning", "good afternoon"
    ]
    
    # 단순 업데이트 패턴
    UPDATE_PATTERNS = [
        "업데이트드립니다", "공유드립니다", "안내드립니다",
        "진행 상황", "현재 작업", "작업 계획", "업무 계획",
        "for your information", "fyi", "update you", "inform you"
    ]
    
    for message in messages:
        content = (message.get("body") or message.get("content") or "").strip()
        subject = (message.get("subject") or "").strip()
        
        # body가 비어있으면 subject를 content로 사용
        if not content and subject:
            content = subject
        
        combined = f"{subject} {content}".lower()
        
        # 1. 너무 짧은 메시지 (20자 미만)
        if len(content) < 20:
            stats["too_short"] += 1
            logger.debug(
                f"짧은 메시지 제거: msg_id={message.get('msg_id')}, "
                f"length={len(content)}, content={content[:50]}"
            )
            continue
        
        # 2. 단순 인사말
        is_greeting = any(pattern in combined for pattern in GREETING_PATTERNS)
        if is_greeting and len(content) < 100:  # 100자 미만이면서 인사말 패턴
            stats["simple_greeting"] += 1
            logger.debug(
                f"단순 인사말 제거: msg_id={message.get('msg_id')}, "
                f"content={content[:50]}"
            )
            continue
        
        # 3. 단순 업데이트 (액션 요청 키워드 없음)
        is_update = any(pattern in combined for pattern in UPDATE_PATTERNS)
        action_keywords = ["부탁", "요청", "주세요", "해주", "필요", "바랍니다", "검토", "확인", "피드백", "의견"]
        has_action = any(keyword in combined for keyword in action_keywords)
        
        if is_update and not has_action:
            stats["simple_update"] += 1
            logger.debug(
                f"단순 업데이트 제거: msg_id={message.get('msg_id')}, "
                f"content={content[:50]}"
            )
            continue
        
        # 필터링 통과
        filtered_messages.append(message)
    
    total_removed = stats["too_short"] + stats["simple_greeting"] + stats["simple_update"]
    if total_removed > 0:
        logger.info(
            f"🔍 짧은/단순 메시지 제거: {total_removed}개 "
            f"(짧음 {stats['too_short']}개, 인사 {stats['simple_greeting']}개, "
            f"업데이트 {stats['simple_update']}개)"
        )
    
    return filtered_messages, stats


def apply_all_filters(messages: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """모든 필터링 적용
    
    1. 본문 내용 중복 제거
    2. 짧은 메시지/단순 인사/업데이트 제거
    3. TO/CC/BCC 우선순위 필터링
    
    Args:
        messages: 메시지 리스트
        
    Returns:
        (필터링된 메시지 리스트, 전체 통계)
    """
    original_count = len(messages)
    
    # 1. 본문 내용 중복 제거
    messages, content_dup_count = filter_duplicate_content(messages)
    
    # 2. 짧은 메시지/단순 인사/업데이트 제거
    messages, short_simple_stats = filter_short_and_simple_messages(messages)
    
    # 3. TO/CC/BCC 우선순위 필터링
    messages, recipient_stats = filter_by_recipient_type(messages)
    
    # 전체 통계
    total_stats = {
        "original_count": original_count,
        "filtered_count": len(messages),
        "removed_count": original_count - len(messages),
        "content_duplicate": content_dup_count,
        "too_short": short_simple_stats["too_short"],
        "simple_greeting": short_simple_stats["simple_greeting"],
        "simple_update": short_simple_stats["simple_update"],
        "recipient_type_removed": recipient_stats["removed"],
        "to_kept": recipient_stats["to_kept"],
        "cc_kept": recipient_stats["cc_kept"],
        "bcc_kept": recipient_stats["bcc_kept"]
    }
    
    logger.info(
        f"✅ 전체 필터링 완료: {original_count}개 → {len(messages)}개 "
        f"({original_count - len(messages)}개 제거)"
    )
    
    return messages, total_stats
