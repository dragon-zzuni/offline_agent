# -*- coding: utf-8 -*-
"""
우선순위 분류기 - 메시지의 중요도와 우선순위를 결정
"""
import asyncio
import logging
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import re

from config.settings import PRIORITY_RULES

logger = logging.getLogger(__name__)


@dataclass
class PriorityScore:
    """우선순위 점수 데이터 클래스"""
    overall_score: float  # 0.0 ~ 1.0
    priority_level: str  # high, medium, low
    urgency_score: float
    importance_score: float
    deadline_score: float
    sender_score: float
    keyword_score: float
    reasoning: List[str]
    suggested_action: str
    estimated_time: str  # 예상 처리 시간
    
    def to_dict(self) -> Dict:
        """딕셔너리로 변환"""
        return {
            "overall_score": self.overall_score,
            "priority_level": self.priority_level,
            "urgency_score": self.urgency_score,
            "importance_score": self.importance_score,
            "deadline_score": self.deadline_score,
            "sender_score": self.sender_score,
            "keyword_score": self.keyword_score,
            "reasoning": self.reasoning,
            "suggested_action": self.suggested_action,
            "estimated_time": self.estimated_time
        }


class PriorityRanker:
    """우선순위 분류기"""
    
    def __init__(self, custom_rules: Dict = None):
        self.rules = custom_rules or PRIORITY_RULES
        self.high_priority_keywords = self.rules.get("high_priority_keywords", [])
        self.high_priority_senders = self.rules.get("high_priority_senders", [])
        self.medium_priority_keywords = self.rules.get("medium_priority_keywords", [])
        
        # 가중치 설정
        self.weights = {
            "urgency": 0.3,
            "sender": 0.25,
            "keywords": 0.2,
            "deadline": 0.15,
            "importance": 0.1
        }
    
    def calculate_priority(self, message_data: Dict) -> PriorityScore:
        """메시지 우선순위 계산"""
        content = message_data.get("body", "") or message_data.get("content", "")
        sender = message_data.get("sender", "")
        subject = message_data.get("subject", "")
        date = message_data.get("date", "")
        
        # 각 점수 계산
        urgency_score = self._calculate_urgency_score(content, subject)
        sender_score = self._calculate_sender_score(sender)
        keyword_score = self._calculate_keyword_score(content, subject)
        deadline_score = self._calculate_deadline_score(content, date)
        importance_score = self._calculate_importance_score(content, subject)
        
        # 전체 점수 계산 (가중 평균)
        overall_score = (
            urgency_score * self.weights["urgency"] +
            sender_score * self.weights["sender"] +
            keyword_score * self.weights["keywords"] +
            deadline_score * self.weights["deadline"] +
            importance_score * self.weights["importance"]
        )
        
        # 우선순위 레벨 결정
        priority_level = self._determine_priority_level(overall_score)
        
        # 추론 과정 생성
        reasoning = self._generate_reasoning({
            "urgency": urgency_score,
            "sender": sender_score,
            "keywords": keyword_score,
            "deadline": deadline_score,
            "importance": importance_score
        }, content, sender)
        
        # 권장 액션 및 예상 시간
        suggested_action, estimated_time = self._suggest_action(priority_level, content)
        
        return PriorityScore(
            overall_score=overall_score,
            priority_level=priority_level,
            urgency_score=urgency_score,
            importance_score=importance_score,
            deadline_score=deadline_score,
            sender_score=sender_score,
            keyword_score=keyword_score,
            reasoning=reasoning,
            suggested_action=suggested_action,
            estimated_time=estimated_time
        )
    
    def _calculate_urgency_score(self, content: str, subject: str) -> float:
        """긴급도 점수 계산"""
        text = f"{subject} {content}".lower()
        
        # 긴급 키워드 체크
        urgent_count = sum(1 for keyword in self.high_priority_keywords if keyword in text)
        
        # 시간 관련 표현 체크
        time_expressions = [
            "오늘", "내일", "즉시", "asap", "지금", "바로", "급히",
            "오전", "오후", "점심", "저녁", "밤"
        ]
        time_count = sum(1 for expr in time_expressions if expr in text)
        
        # 점수 계산 (0.0 ~ 1.0)
        score = min(1.0, (urgent_count * 0.4 + time_count * 0.1))
        return score
    
    def _calculate_sender_score(self, sender: str) -> float:
        """발신자 점수 계산"""
        sender_lower = sender.lower()
        
        # 고우선순위 발신자 체크
        if any(high_sender in sender_lower for high_sender in self.high_priority_senders):
            return 1.0
        
        # 직급/역할 키워드 체크
        authority_keywords = [
            "부장", "과장", "팀장", "대표", "사장", "이사", "임원",
            "manager", "director", "ceo", "boss", "supervisor"
        ]
        
        if any(keyword in sender_lower for keyword in authority_keywords):
            return 0.8
        
        # 회사 도메인 체크
        company_domains = ["@company.com", "@회사.com", "@team.com"]
        if any(domain in sender_lower for domain in company_domains):
            return 0.6
        
        # 외부 발신자
        if "@" not in sender_lower:
            return 0.3  # 메신저 메시지 등
        
        return 0.4  # 기본 점수
    
    def _calculate_keyword_score(self, content: str, subject: str) -> float:
        """키워드 점수 계산"""
        text = f"{subject} {content}".lower()
        
        # 고우선순위 키워드
        high_count = sum(1 for keyword in self.high_priority_keywords if keyword in text)
        
        # 중우선순위 키워드
        medium_count = sum(1 for keyword in self.medium_priority_keywords if keyword in text)
        
        # 점수 계산
        score = min(1.0, high_count * 0.6 + medium_count * 0.3)
        return score
    
    def _calculate_deadline_score(self, content: str, date: str) -> float:
        """데드라인 점수 계산"""
        text = content.lower()
        
        # 명시적 데드라인 키워드
        deadline_keywords = [
            "데드라인", "deadline", "기한", "마감", "제출", "완료",
            "오늘까지", "내일까지", "이번 주까지", "다음 주까지"
        ]
        
        deadline_count = sum(1 for keyword in deadline_keywords if keyword in text)
        
        # 날짜 패턴 체크
        date_patterns = [
            r"\d{1,2}월\s*\d{1,2}일",
            r"\d{1,2}/\d{1,2}",
            r"\d{4}-\d{2}-\d{2}",
            r"월요일까지|화요일까지|수요일까지|목요일까지|금요일까지"
        ]
        
        date_count = 0
        for pattern in date_patterns:
            if re.search(pattern, text):
                date_count += 1
        
        # 점수 계산
        score = min(1.0, deadline_count * 0.4 + date_count * 0.3)
        return score
    
    def _calculate_importance_score(self, content: str, subject: str) -> float:
        """중요도 점수 계산"""
        text = f"{subject} {content}".lower()
        
        # 업무 관련 중요 키워드
        importance_keywords = [
            "프로젝트", "project", "계약", "contract", "예산", "budget",
            "고객", "client", "매출", "revenue", "성과", "performance",
            "보고서", "report", "발표", "presentation", "검토", "review"
        ]
        
        importance_count = sum(1 for keyword in importance_keywords if keyword in text)
        
        # 회의/미팅 관련
        meeting_keywords = ["미팅", "meeting", "회의", "conference", "화상", "video"]
        meeting_count = sum(1 for keyword in meeting_keywords if keyword in text)
        
        # 점수 계산
        score = min(1.0, importance_count * 0.4 + meeting_count * 0.3)
        return score
    
    def _determine_priority_level(self, overall_score: float) -> str:
        """우선순위 레벨 결정"""
        if overall_score >= 0.7:
            return "high"
        elif overall_score >= 0.4:
            return "medium"
        else:
            return "low"
    
    def _generate_reasoning(self, scores: Dict, content: str, sender: str) -> List[str]:
        """추론 과정 생성"""
        reasoning = []
        
        if scores["urgency"] > 0.6:
            reasoning.append("긴급 키워드가 포함되어 높은 긴급도를 보임")
        
        if scores["sender"] > 0.7:
            reasoning.append("중요한 발신자로부터 온 메시지")
        
        if scores["keywords"] > 0.5:
            reasoning.append("중요 키워드가 다수 포함됨")
        
        if scores["deadline"] > 0.5:
            reasoning.append("명시적인 데드라인이 있음")
        
        if scores["importance"] > 0.5:
            reasoning.append("업무상 중요한 내용 포함")
        
        if not reasoning:
            reasoning.append("일반적인 메시지")
        
        return reasoning
    
    def _suggest_action(self, priority_level: str, content: str) -> Tuple[str, str]:
        """권장 액션 및 예상 시간 제안"""
        text = content.lower()
        
        if priority_level == "high":
            if any(keyword in text for keyword in ["미팅", "회의", "meeting"]):
                return "즉시 일정 확인 및 준비", "30분"
            elif any(keyword in text for keyword in ["긴급", "urgent", "asap"]):
                return "즉시 처리 필요", "15분"
            else:
                return "우선순위 높게 처리", "1시간"
        
        elif priority_level == "medium":
            if any(keyword in text for keyword in ["검토", "review", "확인"]):
                return "검토 후 답변", "2-3시간"
            elif any(keyword in text for keyword in ["요청", "부탁"]):
                return "요청 사항 검토 및 답변", "1-2시간"
            else:
                return "일반 처리", "반나절"
        
        else:  # low
            return "여유 있을 때 처리", "1일"
    
    async def rank_messages(self, messages: List[Dict]) -> List[Tuple[Dict, PriorityScore]]:
        """여러 메시지 우선순위 분류"""
        ranked_messages = []
        
        for message in messages:
            try:
                priority_score = self.calculate_priority(message)
                ranked_messages.append((message, priority_score))
            except Exception as e:
                logger.error(f"메시지 우선순위 계산 오류: {e}")
                continue
        
        # 전체 점수 기준으로 정렬 (높은 점수부터)
        ranked_messages.sort(key=lambda x: x[1].overall_score, reverse=True)
        
        logger.info(f"🎯 {len(ranked_messages)}개 메시지 우선순위 분류 완료")
        return ranked_messages
    
    def get_priority_stats(self, ranked_messages: List[Tuple[Dict, PriorityScore]]) -> Dict:
        """우선순위 통계"""
        stats = {
            "total": len(ranked_messages),
            "high": 0,
            "medium": 0,
            "low": 0,
            "avg_score": 0.0
        }
        
        total_score = 0.0
        for _, priority_score in ranked_messages:
            stats[priority_score.priority_level] += 1
            total_score += priority_score.overall_score
        
        if stats["total"] > 0:
            stats["avg_score"] = total_score / stats["total"]
        
        return stats


# 테스트 함수
async def test_priority_ranker():
    """우선순위 분류기 테스트"""
    ranker = PriorityRanker()
    
    test_messages = [
        {
            "sender": "김부장",
            "subject": "긴급: 내일 오전 10시 팀 미팅",
            "body": "내일 오전 10시에 3층 회의실에서 긴급 팀 미팅이 있습니다. 프로젝트 데드라인이 당겨져서 즉시 준비가 필요합니다.",
            "content": "내일 오전 10시에 3층 회의실에서 긴급 팀 미팅이 있습니다. 프로젝트 데드라인이 당겨져서 즉시 준비가 필요합니다.",
            "date": "2024-01-15"
        },
        {
            "sender": "박대리",
            "subject": "프로젝트 문서 검토 요청",
            "body": "프로젝트 문서 검토 부탁드립니다. 금요일까지 피드백 주시면 감사하겠습니다.",
            "content": "프로젝트 문서 검토 부탁드립니다. 금요일까지 피드백 주시면 감사하겠습니다.",
            "date": "2024-01-15"
        },
        {
            "sender": "이동료",
            "subject": "점심 같이 드실까요?",
            "body": "오늘 점심 같이 드실까요? 새로운 식당이 생겼다고 해서 가보려고 합니다.",
            "content": "오늘 점심 같이 드실까요? 새로운 식당이 생겼다고 해서 가보려고 합니다.",
            "date": "2024-01-15"
        }
    ]
    
    ranked_messages = await ranker.rank_messages(test_messages)
    
    print("🎯 우선순위 분류 결과:")
    for i, (message, priority_score) in enumerate(ranked_messages, 1):
        print(f"\n{i}. {priority_score.priority_level.upper()} (점수: {priority_score.overall_score:.2f})")
        print(f"   제목: {message['subject']}")
        print(f"   발신자: {message['sender']}")
        print(f"   추론: {'; '.join(priority_score.reasoning)}")
        print(f"   권장 액션: {priority_score.suggested_action} ({priority_score.estimated_time})")
    
    stats = ranker.get_priority_stats(ranked_messages)
    print(f"\n📊 통계: 총 {stats['total']}개 (High: {stats['high']}, Medium: {stats['medium']}, Low: {stats['low']})")


if __name__ == "__main__":
    asyncio.run(test_priority_ranker())
