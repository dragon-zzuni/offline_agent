# -*- coding: utf-8 -*-
"""
그룹화된 요약 데이터 모델
일/주/월 단위로 그룹화된 메시지의 요약 정보를 담는 데이터 클래스
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


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
            "top_senders": self.top_senders
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
            top_senders=data.get("top_senders", [])
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
            top_senders=top_senders
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
