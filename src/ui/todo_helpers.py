# -*- coding: utf-8 -*-
"""
TODO 패널 헬퍼 함수들
"""
import json
from datetime import datetime, timezone
from typing import Optional, List, Dict
from PyQt6.QtWidgets import QLabel


# 한국어 이름 처리 상수
_KOREAN_NAME_SUFFIXES = ("선생님", "팀장", "부장", "님", "씨")
_KOREAN_PARTICLES = (
    "께서", "에서", "에게", "으로", "로", "와", "과", "은", "는", "이", "가",
    "을", "를", "도", "만", "부터", "까지", "에게서", "밖에", "로서", "로써",
    "이라서", "라서", "이라도", "라도", "이며", "이며도"
)


def _parse_iso_dt(s: str | None) -> Optional[datetime]:
    """ISO 형식 날짜 문자열 파싱"""
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        try:
            return datetime.fromisoformat(s)
        except Exception:
            return None


def _created_ts(todo: dict) -> float:
    """TODO 생성 시간 타임스탬프 반환"""
    created = todo.get("created_at")
    dt = _parse_iso_dt(created)
    return dt.timestamp() if dt else 0.0


def _normalize_korean_name(token: str) -> str:
    """한국어 이름 정규화 (존댓말, 조사 제거)"""
    base = token.strip()
    for suffix in _KOREAN_NAME_SUFFIXES:
        if base.endswith(suffix) and len(base) > len(suffix):
            base = base[:-len(suffix)]
            break
    changed = True
    while changed and len(base) > 2:
        changed = False
        for suffix in _KOREAN_PARTICLES:
            if base.endswith(suffix) and len(base) > len(suffix):
                base = base[:-len(suffix)]
                changed = True
                break
    return base.strip()


def _create_recipient_type_badge(recipient_type: str) -> Optional[QLabel]:
    """수신 타입 배지 생성 (CC, BCC)"""
    recipient_type = (recipient_type or "to").lower()
    
    if recipient_type == "cc":
        badge = QLabel("참조(CC)")
        badge.setStyleSheet(
            "color:#92400E; background:#FEF3C7; "
            "padding:2px 6px; border-radius:8px; font-weight:600;"
        )
        return badge
    elif recipient_type == "bcc":
        badge = QLabel("숨은참조(BCC)")
        badge.setStyleSheet(
            "color:#92400E; background:#FEF3C7; "
            "padding:2px 6px; border-radius:8px; font-weight:600;"
        )
        return badge
    
    return None


def _create_source_type_badge(source_type: str) -> QLabel:
    """소스 타입 배지 생성 (메일, 메시지)"""
    source_type = (source_type or "메시지").strip()
    
    if source_type == "메일":
        badge = QLabel("📧 메일")
        badge.setStyleSheet(
            "color:#1E40AF; background:#DBEAFE; "
            "padding:2px 6px; border-radius:8px; font-weight:600; font-size:10px;"
        )
    else:
        badge = QLabel("💬 메시지")
        badge.setStyleSheet(
            "color:#065F46; background:#D1FAE5; "
            "padding:2px 6px; border-radius:8px; font-weight:600; font-size:10px;"
        )
    
    return badge


def _deadline_badge(todo: dict) -> Optional[tuple[str, str, str]]:
    """데드라인 배지 정보 반환 (텍스트, 전경색, 배경색)"""
    deadline = todo.get("deadline_ts") or todo.get("deadline")
    dt = _parse_iso_dt(deadline)
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    diff_hours = (dt - now).total_seconds() / 3600.0
    if diff_hours < 0:
        return ("마감 지남", "#991B1B", "#FEE2E2")
    if diff_hours < 1:
        return ("1시간 이내", "#1F2937", "#FEF3C7")
    if diff_hours < 24:
        return (f"{int(diff_hours)}시간 남음", "#1D4ED8", "#DBEAFE")
    days = int(diff_hours // 24)
    return (f"D-{days}", "#1D4ED8", "#DBEAFE")


def _evidence_count(todo: dict) -> int:
    """근거 개수 반환"""
    evidence = todo.get("evidence")
    if isinstance(evidence, list):
        return len(evidence)
    try:
        return len(json.loads(evidence or "[]"))
    except Exception:
        return 0


def _source_message_dict(todo: dict) -> dict:
    """소스 메시지를 dict로 변환"""
    src = todo.get("source_message")
    if not src:
        return {}
    if isinstance(src, str):
        try:
            src = json.loads(src)
        except Exception:
            return {}
    if isinstance(src, dict):
        return src
    return {}


def _is_unread(todo: dict) -> bool:
    """TODO가 읽지 않은 상태인지 확인"""
    if todo.get("_viewed"):
        return False
    
    created_at = todo.get("created_at")
    if created_at:
        try:
            from utils.datetime_utils import parse_iso_datetime
            
            created_dt = parse_iso_datetime(created_at)
            if created_dt:
                now = datetime.now(timezone.utc)
                if (now - created_dt).total_seconds() > 300:  # 5분
                    return False
        except Exception:
            pass
    
    src = _source_message_dict(todo)
    if not src:
        return False
    
    return not src.get("is_read", True)


def _priority_sort_key(todo: dict):
    """우선순위 정렬 키"""
    order = {"high": 0, "medium": 1, "low": 2}
    idx = order.get((todo.get("priority") or "").lower(), 3)
    return (idx, -_created_ts(todo))
