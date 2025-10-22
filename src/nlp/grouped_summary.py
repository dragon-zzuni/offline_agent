# -*- coding: utf-8 -*-
"""
그룹화된 요약 데이터 모델

일/주/월 단위로 그룹화된 메시지의 요약 정보를 담는 데이터 클래스와
주제 추출 기능을 제공합니다.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
from collections import Counter
import logging

logger = logging.getLogger(__name__)


# 주제 카테고리 키워드 매핑
TOPIC_KEYWORDS = {
    "미팅": {
        "keywords": ["미팅", "회의", "체크인", "리뷰", "meeting", "review", "standup", "sync"],
        "priority": 1
    },
    "보고서": {
        "keywords": ["보고서", "리포트", "업데이트", "공유", "report", "update", "share", "status"],
        "priority": 2
    },
    "검토": {
        "keywords": ["검토", "리뷰", "피드백", "승인", "review", "feedback", "approval", "approve"],
        "priority": 3
    },
    "개발": {
        "keywords": ["개발", "구현", "코딩", "작업", "develop", "implement", "code", "feature"],
        "priority": 4
    },
    "버그": {
        "keywords": ["버그", "이슈", "문제", "수정", "bug", "issue", "problem", "fix", "error"],
        "priority": 5
    },
    "배포": {
        "keywords": ["배포", "릴리스", "출시", "deploy", "release", "launch", "production"],
        "priority": 6
    },
    "테스트": {
        "keywords": ["테스트", "QA", "검증", "test", "testing", "qa", "verify", "validation"],
        "priority": 7
    },
    "디자인": {
        "keywords": ["디자인", "UI", "UX", "design", "interface", "mockup", "wireframe"],
        "priority": 8
    },
    "일정": {
        "keywords": ["일정", "스케줄", "마감", "연기", "schedule", "deadline", "timeline", "delay"],
        "priority": 9
    },
    "승인": {
        "keywords": ["승인", "결재", "확인", "approval", "confirm", "sign-off", "authorize"],
        "priority": 10
    }
}


@dataclass
class GroupedSummary:
    """그룹화된 메시지 요약 데이터 클래스"""
    
    period_start: datetime
    period_end: datetime
    unit: str  # "daily", "weekly", "monthly"
    total_messages: int
    email_count: int
    messenger_count: int
    summary_text: str
    key_points: List[str] = field(default_factory=list)
    priority_distribution: Dict[str, int] = field(default_factory=dict)
    top_senders: List[tuple[str, int]] = field(default_factory=list)
    message_ids: List[str] = field(default_factory=list)  # 이 그룹에 속한 메시지 ID 목록
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "unit": self.unit,
            "total_messages": self.total_messages,
            "email_count": self.email_count,
            "messenger_count": self.messenger_count,
            "summary_text": self.summary_text,
            "key_points": self.key_points,
            "priority_distribution": self.priority_distribution,
            "top_senders": self.top_senders,
            "message_ids": self.message_ids
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GroupedSummary':
        """딕셔너리에서 생성"""
        return cls(
            period_start=datetime.fromisoformat(data["period_start"]),
            period_end=datetime.fromisoformat(data["period_end"]),
            unit=data["unit"],
            total_messages=data["total_messages"],
            email_count=data["email_count"],
            messenger_count=data["messenger_count"],
            summary_text=data["summary_text"],
            key_points=data.get("key_points", []),
            priority_distribution=data.get("priority_distribution", {}),
            top_senders=data.get("top_senders", []),
            message_ids=data.get("message_ids", [])
        )
    
    @classmethod
    def from_messages(
        cls,
        messages: List[Dict[str, Any]],
        period_start: datetime,
        period_end: datetime,
        unit: str,
        summary_text: str = "",
        key_points: Optional[List[str]] = None
    ) -> 'GroupedSummary':
        """
        메시지 리스트로부터 GroupedSummary 생성
        통계 정보를 자동으로 계산
        
        Args:
            messages: 메시지 리스트
            period_start: 기간 시작
            period_end: 기간 종료
            unit: 그룹화 단위
            summary_text: 요약 텍스트 (선택)
            key_points: 핵심 포인트 (선택)
            
        Returns:
            GroupedSummary 인스턴스
        """
        # 메시지 타입별 카운트
        email_count = sum(1 for m in messages if m.get("type") == "email")
        messenger_count = sum(1 for m in messages if m.get("type") == "messenger")
        
        # 우선순위 분포 계산
        priority_dist = cls._calculate_priority_distribution(messages)
        
        # 주요 발신자 계산
        top_senders = cls._calculate_top_senders(messages, top_n=5)
        
        # 메시지 ID 수집
        message_ids = []
        for msg in messages:
            # 다양한 ID 필드 시도 (msg_id가 주요 필드)
            msg_id = msg.get("msg_id") or msg.get("id") or msg.get("message_id") or msg.get("_id")
            if msg_id:
                message_ids.append(str(msg_id))
        
        logger.debug(f"GroupedSummary.from_messages: 수집된 message_ids 수 = {len(message_ids)}/{len(messages)}")
        
        return cls(
            period_start=period_start,
            period_end=period_end,
            unit=unit,
            total_messages=len(messages),
            email_count=email_count,
            messenger_count=messenger_count,
            summary_text=summary_text,
            key_points=key_points or [],
            priority_distribution=priority_dist,
            top_senders=top_senders,
            message_ids=message_ids
        )
    
    @staticmethod
    def _calculate_priority_distribution(messages: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        메시지의 우선순위 분포 계산
        
        Args:
            messages: 메시지 리스트
            
        Returns:
            우선순위별 카운트 딕셔너리
        """
        distribution = {"high": 0, "medium": 0, "low": 0}
        
        for message in messages:
            # 메시지에 우선순위 정보가 있으면 사용
            priority = message.get("priority", "low")
            
            # metadata에 우선순위가 있을 수도 있음
            if not priority or priority == "low":
                metadata = message.get("metadata", {})
                priority = metadata.get("priority", "low")
            
            # 정규화
            priority = str(priority).lower()
            if priority in distribution:
                distribution[priority] += 1
            else:
                distribution["low"] += 1
        
        return distribution
    
    @staticmethod
    def _calculate_top_senders(
        messages: List[Dict[str, Any]],
        top_n: int = 5
    ) -> List[tuple[str, int]]:
        """
        주요 발신자 계산 (메시지 수 기준)
        
        Args:
            messages: 메시지 리스트
            top_n: 상위 N명
            
        Returns:
            (발신자, 메시지 수) 튜플 리스트
        """
        sender_counts: Dict[str, int] = {}
        
        for message in messages:
            sender = message.get("sender", "Unknown")
            sender_counts[sender] = sender_counts.get(sender, 0) + 1
        
        # 메시지 수 기준 내림차순 정렬
        sorted_senders = sorted(
            sender_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return sorted_senders[:top_n]
    
    def get_period_label(self) -> str:
        """기간을 사람이 읽기 쉬운 형식으로 반환"""
        if self.unit == "daily":
            return self.period_start.strftime("%Y년 %m월 %d일")
        elif self.unit == "weekly":
            end_date = self.period_end.strftime("%m월 %d일")
            return f"{self.period_start.strftime('%Y년 %m월 %d일')} ~ {end_date}"
        elif self.unit == "monthly":
            return self.period_start.strftime("%Y년 %m월")
        else:
            return f"{self.period_start.date()} ~ {self.period_end.date()}"
    
    def get_statistics_summary(self) -> str:
        """통계 정보를 문자열로 반환"""
        lines = []
        lines.append(f"총 {self.total_messages}건")
        lines.append(f"이메일 {self.email_count}건, 메신저 {self.messenger_count}건")
        
        if self.priority_distribution:
            high = self.priority_distribution.get("high", 0)
            medium = self.priority_distribution.get("medium", 0)
            low = self.priority_distribution.get("low", 0)
            lines.append(f"우선순위: High {high}건, Medium {medium}건, Low {low}건")
        
        if self.top_senders:
            top_sender_name, top_sender_count = self.top_senders[0]
            lines.append(f"주요 발신자: {top_sender_name} ({top_sender_count}건)")
        
        return " | ".join(lines)


def extract_topics(messages: List[Dict[str, Any]], max_topics: int = 3) -> List[str]:
    """메시지 리스트에서 주요 주제를 추출합니다.
    
    메시지 내용과 제목을 분석하여 가장 많이 언급된 주제를 반환합니다.
    각 주제는 우선순위에 따라 가중치가 부여됩니다.
    
    Args:
        messages: 메시지 리스트
        max_topics: 최대 추출할 주제 수 (기본값: 3)
        
    Returns:
        추출된 주제 리스트 (점수 기준 내림차순)
        
    Examples:
        >>> messages = [
        ...     {"content": "미팅 일정 확인", "subject": "회의 안내"},
        ...     {"content": "버그 수정 완료", "subject": "이슈 해결"}
        ... ]
        >>> extract_topics(messages, max_topics=2)
        ['미팅', '버그']
    """
    if not messages:
        return []
    
    # Counter를 사용하여 주제별 점수 계산
    topic_scores = Counter()
    
    for message in messages:
        # 메시지 내용 추출
        content = _extract_message_content(message)
        
        # 제목 추출
        subject = message.get("subject", "")
        
        # 전체 텍스트 (소문자 변환)
        full_text = f"{subject} {content}".lower()
        
        # 각 주제 카테고리의 키워드 매칭
        for topic, config in TOPIC_KEYWORDS.items():
            keywords = config["keywords"]
            priority = config["priority"]
            
            # 키워드 매칭 횟수 계산
            matches = sum(1 for keyword in keywords if keyword.lower() in full_text)
            
            if matches > 0:
                # 우선순위가 높을수록 가중치 부여 (priority가 낮을수록 중요)
                weight = 11 - priority
                topic_scores[topic] += matches * weight
    
    # 상위 N개 주제 반환
    return [topic for topic, score in topic_scores.most_common(max_topics)]


def _extract_message_content(message: Dict[str, Any]) -> str:
    """메시지에서 내용 텍스트를 추출합니다.
    
    Args:
        message: 메시지 딕셔너리
        
    Returns:
        추출된 내용 문자열
    """
    content = message.get("content", "")
    
    if isinstance(content, str):
        return content
    elif isinstance(content, dict):
        return content.get("text", "")
    
    return ""


def generate_improved_summary(
    messages: List[Dict[str, Any]],
    topics: Optional[List[str]] = None,
    priority_dist: Optional[Dict[str, int]] = None,
    top_senders: Optional[List[tuple[str, int]]] = None
) -> str:
    """구조화된 요약 텍스트를 생성합니다.
    
    주제, 우선순위, 주요 발신자 정보를 조합하여 간결한 요약을 생성합니다.
    
    Args:
        messages: 메시지 리스트
        topics: 추출된 주제 리스트 (None이면 자동 추출)
        priority_dist: 우선순위 분포 (None이면 자동 계산)
        top_senders: 주요 발신자 리스트 (None이면 자동 계산)
        
    Returns:
        구조화된 요약 텍스트
        
    Examples:
        >>> messages = [{"content": "미팅 일정", "priority": "high"}]
        >>> generate_improved_summary(messages)
        '미팅 관련 1건 (긴급 1건)'
    """
    if not messages:
        return "메시지 없음"
    
    # 주제 자동 추출
    if topics is None:
        topics = extract_topics(messages, max_topics=2)
    
    # 우선순위 분포 계산
    if priority_dist is None:
        priority_dist = GroupedSummary._calculate_priority_distribution(messages)
    
    # 주요 발신자 계산
    if top_senders is None:
        top_senders = GroupedSummary._calculate_top_senders(messages, top_n=3)
    
    # 요약 텍스트 생성
    summary_parts = []
    
    # 1. 주제 기반 요약
    if topics:
        topic_str = ", ".join(topics)
        summary_parts.append(f"{topic_str} 관련 {len(messages)}건")
    else:
        # 폴백: 메시지 첫 줄 사용
        first_content = _extract_message_content(messages[0])
        first_line = first_content.split('\n')[0][:30] if first_content else "메시지"
        summary_parts.append(f"{first_line}... 외 {len(messages)}건")
    
    # 2. 긴급 메시지 강조
    high_count = priority_dist.get("high", 0)
    if high_count > 0:
        summary_parts.append(f"(긴급 {high_count}건)")
    
    # 3. 주요 발신자 (50% 이상 차지하는 경우만 표시)
    if top_senders:
        top_sender_name, top_sender_count = top_senders[0]
        if top_sender_count >= len(messages) * 0.5:
            summary_parts.append(f"주요: {top_sender_name}")
    
    return " ".join(summary_parts)
