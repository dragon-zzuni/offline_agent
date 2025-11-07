# -*- coding: utf-8 -*-
"""
액션 추출기 - 메시지에서 필요한 액션과 TODO 항목을 추출
"""
import asyncio
import logging
import json
import re
import uuid
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class ActionItem:
    """액션 아이템 데이터 클래스"""
    action_id: str
    action_type: str  # meeting, task, deadline, response, review, etc.
    title: str
    description: str
    deadline: Optional[datetime]
    priority: str  # high, medium, low
    assignee: str  # 나에게 할당된 작업
    requester: str  # 요청자
    source_message_id: str
    context: Dict  # 추가 컨텍스트 정보
    created_at: datetime = None
    status: str = "pending"  # pending, in_progress, completed, cancelled
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
    
    def to_dict(self) -> Dict:
        """딕셔너리로 변환"""
        return {
            "action_id": self.action_id,
            "action_type": self.action_type,
            "title": self.title,
            "description": self.description,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "priority": self.priority,
            "assignee": self.assignee,
            "requester": self.requester,
            "source_message_id": self.source_message_id,
            "context": self.context,
            "created_at": self.created_at.isoformat(),
            "status": self.status
        }


class ActionExtractor:
    """액션 추출기"""
    
    def __init__(self):
        # 액션 타입별 패턴 정의
        self.action_patterns = {
            "meeting": {
                "keywords": ["미팅", "meeting", "회의", "conference", "화상", "video call"],
                "patterns": [
                    r"(\d{1,2}:\d{2}|\d{1,2}시).*?미팅",
                    r"미팅.*?(\d{1,2}:\d{2}|\d{1,2}시)",
                    r"(\d{1,2}월\s*\d{1,2}일).*?회의",
                    r"회의.*?(\d{1,2}월\s*\d{1,2}일)"
                ]
            },
            "task": {
                "keywords": ["작업", "task", "업무", "프로젝트", "project", "과제"],
                "patterns": [
                    r"(\w+).*?작업.*?요청",
                    r"(\w+).*?프로젝트.*?진행",
                    r"(\w+).*?업무.*?처리"
                ]
            },
            "deadline": {
                "keywords": ["데드라인", "deadline", "기한", "마감", "제출", "완료"],
                "patterns": [
                    r"(\d{1,2}월\s*\d{1,2}일).*?까지",
                    r"(\d{1,2}/\d{1,2}).*?마감",
                    r"(오늘|내일|이번 주|다음 주).*?까지",
                    r"(\w+요일).*?제출"
                ]
            },
            "review": {
                "keywords": ["검토", "review", "확인", "check", "피드백", "feedback", "업데이트"],
                "patterns": [
                    r"(\w+).*?검토.*?부탁",
                    r"(\w+).*?확인.*?요청",
                    r"(\w+).*?피드백.*?주세요"
                ]
            },
            "response": {
                "keywords": ["답변", "response", "회신", "reply", "응답"],
                "patterns": [
                    r"답변.*?부탁",
                    r"회신.*?요청",
                    r"응답.*?기다립니다"
                ]
            }
        }
        
        # 우선순위 키워드
        self.priority_keywords = {
            "high": ["긴급", "urgent", "asap", "즉시", "바로", "지금"],
            "medium": ["중요", "important", "우선", "빠르게"],
            "low": ["여유", "편한", "시간"]
        }
        self.generic_request_markers = [
            # 한국어 요청 표현
            "부탁", "요청", "주세요", "주시길", "해주세요", "해주세요.", "정리해줘",
            "확인해줘", "확인 부탁", "지원 부탁", "도와줘", "도움", "협조",
            "공유", "전달", "보내", "알려", "말씀", "드립니다", "드려요",
            "필요합니다", "필요해요", "바랍니다", "바래요", "감사하겠습니다",
            "부탁드립니다", "부탁드려요", "요청드립니다", "요청드려요",
            "해주시면", "주시면", "주실", "해주실", "주시기", "해주시기",
            "검토", "리뷰", "피드백", "의견", "코멘트", "승인", "결재",
            "준비", "작성", "수정", "변경", "추가", "삭제", "업데이트",
            # 영어 요청 표현
            "can you", "could you", "please", "pls", "plz", 
            "let me know", "share", "update", "send", "provide",
            "check", "review", "follow up", "후속", "feedback",
            "need", "require", "request", "ask", "would you",
            "kindly", "appreciate", "thanks", "thank you",
        ]
        self.meeting_markers = ["콜", "sync", "standup", "huddle", "회의", "미팅", "meeting", "call", "conference"]
        self.deadline_markers = ["까지", "마감", "deadline", "제출", "due", "완료", "납기", "기한"]
        self.response_markers = ["답장", "답변", "회신", "reply", "response", "응답", "피드백"]
        self._bullet_pattern = re.compile(r"^[\-\*\•\·\d\)\(]+\s*")
    
    def extract_actions(self, message_data: Dict, user_email: str = "pm.1@quickchat.dev") -> List[ActionItem]:
        """메시지에서 액션 추출
        
        Args:
            message_data: 메시지 데이터
            user_email: 사용자(PM) 이메일 주소 (기본값: pm.1@quickchat.dev)
            
        Returns:
            액션 아이템 리스트
            
        Note:
            사용자(PM)에게 **온** 메시지만 TODO로 변환합니다.
            사용자가 **보낸** 메시지는 제외됩니다.
        """
        content = message_data.get("body", "") or message_data.get("content", "")
        subject = message_data.get("subject", "")
        sender = message_data.get("sender", "")
        sender_email = message_data.get("sender_email", "")
        msg_id = message_data.get("msg_id", f"msg_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        
        # ✅ 중요: 사용자(PM)가 보낸 메시지는 TODO로 만들지 않음
        if sender_email and sender_email.lower() == user_email.lower():
            logger.debug(f"⏭️ 사용자가 보낸 메시지 스킵: {msg_id}")
            return []
        
        # 이메일 주소가 없는 경우 sender 이름으로 체크 (chat 메시지)
        if not sender_email and sender and "kim jihoon" in sender.lower():
            logger.debug(f"⏭️ 사용자가 보낸 메시지 스킵 (이름 기반): {msg_id}")
            return []
        
        actions = []
        combined_text = f"{subject} {content}".strip()
        
        # 각 액션 타입별로 추출
        for action_type, config in self.action_patterns.items():
            extracted_actions = self._extract_action_type(
                content, subject, sender, msg_id, action_type, config
            )
            actions.extend(extracted_actions)
        
        # 문장 단위의 일반 요청 추출 (키워드가 없어도 요청 표현 감지)
        if combined_text:
            actions.extend(
                self._extract_generic_requests(combined_text, sender, msg_id)
            )

        # 중복 제거 및 정리
        actions = self._deduplicate_actions(actions)
        
        if actions:
            logger.info(f"🎯 {len(actions)}개의 액션 추출: {msg_id} (발신자: {sender})")
        return actions
    
    def _extract_action_type(self, content: str, subject: str, sender: str, 
                           msg_id: str, action_type: str, config: Dict) -> List[ActionItem]:
        """특정 액션 타입 추출"""
        actions = []
        text = f"{subject} {content}"
        
        # 키워드 기반 추출
        for keyword in config["keywords"]:
            if keyword in text.lower():
                action = self._create_action_from_keyword(
                    text, keyword, action_type, sender, msg_id
                )
                if action:
                    actions.append(action)
        
        # 패턴 기반 추출
        for pattern in config["patterns"]:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                action = self._create_action_from_pattern(
                    text, match, action_type, sender, msg_id, pattern
                )
                if action:
                    actions.append(action)
        
        return actions

    def _extract_generic_requests(self, text: str, sender: str, msg_id: str) -> List[ActionItem]:
        """명시적 키워드가 없어도 요청 어조를 감지해 액션을 생성한다."""
        actions: List[ActionItem] = []
        for sentence in self._split_sentences(text):
            normalized = sentence.strip()
            # 최소 길이를 8자로 낮춤 (더 짧은 요청도 감지)
            if len(normalized) < 8:
                continue
            lowered = normalized.lower()
            if not self._looks_like_request(lowered):
                continue
            inferred_type = self._infer_action_type_from_sentence(lowered)
            priority = self._determine_priority(normalized)
            actions.append(
                ActionItem(
                    action_id=f"{inferred_type}_{uuid.uuid4().hex[:12]}",
                    action_type=inferred_type,
                    title=self._generate_action_title(inferred_type, normalized),
                    description=normalized,
                    deadline=self._extract_deadline(normalized),
                    priority=priority,
                    assignee="나",
                    requester=sender,
                    source_message_id=msg_id,
                    context={"extracted_from": "generic_sentence"},
                )
            )

        # 글머리표나 리스트 형태의 요청도 액션으로 변환
        for bullet in self._extract_bullet_requests(text.splitlines(), sender, msg_id):
            actions.append(bullet)
        return actions

    def _extract_bullet_requests(
        self, lines: List[str], sender: str, msg_id: str
    ) -> List[ActionItem]:
        actions: List[ActionItem] = []
        for raw_line in lines:
            line = self._bullet_pattern.sub("", raw_line or "").strip()
            # 최소 길이를 5자로 낮춤 (짧은 리스트 항목도 감지)
            if len(line) < 5:
                continue
            lowered = line.lower()
            if not self._looks_like_request(lowered):
                continue
            inferred_type = self._infer_action_type_from_sentence(lowered)
            actions.append(
                ActionItem(
                    action_id=f"{inferred_type}_{uuid.uuid4().hex[:12]}",
                    action_type=inferred_type,
                    title=self._generate_action_title(inferred_type, line),
                    description=line,
                    deadline=self._extract_deadline(line),
                    priority=self._determine_priority(line),
                    assignee="나",
                    requester=sender,
                    source_message_id=msg_id,
                    context={"extracted_from": "bullet"},
                )
            )
        return actions

    def _split_sentences(self, text: str) -> List[str]:
        """간단한 문장 분할 - 더 세밀하게 분할하여 더 많은 요청 감지"""
        if not text:
            return []
        # 다양한 문장 종결 패턴으로 분할
        fragments = re.split(r"[.!?\n]+\s*|니다[\s,]|요[\s,]|습니다[\s,]|ㅂ니다[\s,]", text)
        return [frag.strip() for frag in fragments if frag and frag.strip()]

    def _looks_like_request(self, lowered: str) -> bool:
        return any(marker in lowered for marker in self.generic_request_markers)

    def _infer_action_type_from_sentence(self, lowered: str) -> str:
        if any(marker in lowered for marker in self.meeting_markers):
            return "meeting"
        if any(marker in lowered for marker in self.deadline_markers):
            return "deadline"
        if any(marker in lowered for marker in self.response_markers):
            return "response"
        if any(term in lowered for term in self.action_patterns["review"]["keywords"]):
            return "review"
        return "task"
    
    def _create_action_from_keyword(self, text: str, keyword: str, action_type: str, 
                                  sender: str, msg_id: str) -> Optional[ActionItem]:
        """키워드로부터 액션 생성"""
        # 키워드 주변 문맥 추출
        context = self._extract_context_around_keyword(text, keyword)
        
        if not context:
            return None
        
        # 액션 제목 생성
        title = self._generate_action_title(action_type, context)
        
        # 우선순위 결정
        priority = self._determine_priority(text)
        
        # 데드라인 추출
        deadline = self._extract_deadline(text)
        
        return ActionItem(
            action_id=f"{action_type}_{uuid.uuid4().hex[:12]}",
            action_type=action_type,
            title=title,
            description=context,
            deadline=deadline,
            priority=priority,
            assignee="나",
            requester=sender,
            source_message_id=msg_id,
            context={"keyword": keyword, "extracted_from": "keyword"}
        )
    
    def _create_action_from_pattern(self, text: str, match: str, action_type: str, 
                                  sender: str, msg_id: str, pattern: str) -> Optional[ActionItem]:
        """패턴 매칭으로부터 액션 생성"""
        match_text = " ".join(m for m in match if m) if isinstance(match, tuple) else match

        # 매칭된 부분 주변 문맥 추출
        context = self._extract_context_around_match(text, match_text)
        
        if not context:
            return None
        
        # 액션 제목 생성
        title = self._generate_action_title(action_type, context)
        
        # 우선순위 결정
        priority = self._determine_priority(text)
        
        # 데드라인 추출 (특별히 패턴에서)
        deadline = self._extract_deadline_from_match(match_text, action_type)
        
        return ActionItem(
            action_id=f"{action_type}_{uuid.uuid4().hex[:12]}",
            action_type=action_type,
            title=title,
            description=context,
            deadline=deadline,
            priority=priority,
            assignee="나",
            requester=sender,
            source_message_id=msg_id,
            context={"match": match_text, "pattern": pattern, "extracted_from": "pattern"}
        )
    
    def _extract_context_around_keyword(self, text: str, keyword: str) -> str:
        """키워드 주변 문맥 추출"""
        keyword_pos = text.lower().find(keyword.lower())
        if keyword_pos == -1:
            return ""
        
        # 키워드 앞뒤로 100자씩 추출
        start = max(0, keyword_pos - 100)
        end = min(len(text), keyword_pos + len(keyword) + 100)
        
        context = text[start:end].strip()
        return context
    
    def _extract_context_around_match(self, text: str, match: str) -> str:
        """매칭된 부분 주변 문맥 추출"""
        match_pos = text.find(match)
        if match_pos == -1:
            return ""
        
        # 매칭 부분 앞뒤로 150자씩 추출
        start = max(0, match_pos - 150)
        end = min(len(text), match_pos + len(match) + 150)
        
        context = text[start:end].strip()
        return context
    
    def _generate_action_title(self, action_type: str, context: str) -> str:
        """액션 제목 생성 - 간결한 타입별 제목"""
        titles = {
            "meeting": "미팅참석",
            "task": "업무처리",
            "deadline": "마감작업",
            "review": "문서검토",
            "response": "답변작성"
        }
        
        # 간결한 제목 반환 (중복 제거는 description 기반으로 처리)
        return titles.get(action_type, "액션수행")
    
    def _determine_priority(self, text: str) -> str:
        """우선순위 결정"""
        text_lower = text.lower()
        
        for priority, keywords in self.priority_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                return priority
        
        return "medium"  # 기본값
    
    def _extract_deadline(self, text: str) -> Optional[datetime]:
        """데드라인 추출"""
        # 날짜 패턴들
        date_patterns = [
            r"(\d{1,2}월\s*\d{1,2}일)",
            r"(\d{1,2}/\d{1,2})",
            r"(\d{4}-\d{2}-\d{2})",
            r"(오늘|내일|이번 주|다음 주)",
            r"(\w+요일)"
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                date_str = match.group(1)
                return self._parse_date_string(date_str)
        
        return None
    
    def _extract_deadline_from_match(self, match: str, action_type: str) -> Optional[datetime]:
        """매칭된 부분에서 데드라인 추출"""
        if action_type == "deadline":
            return self._parse_date_string(match)
        elif action_type == "meeting":
            return self._parse_time_string(match)
        
        return None
    
    def _parse_date_string(self, date_str: str) -> Optional[datetime]:
        """날짜 문자열 파싱"""
        try:
            # 오늘, 내일 처리
            if "오늘" in date_str:
                return datetime.now().replace(hour=18, minute=0, second=0, microsecond=0)
            elif "내일" in date_str:
                tomorrow = datetime.now() + timedelta(days=1)
                return tomorrow.replace(hour=18, minute=0, second=0, microsecond=0)
            
            # 월/일 형식 (예: 1월 15일)
            month_day_match = re.match(r"(\d{1,2})월\s*(\d{1,2})일", date_str)
            if month_day_match:
                month = int(month_day_match.group(1))
                day = int(month_day_match.group(2))
                year = datetime.now().year
                return datetime(year, month, day, 18, 0, 0)
            
            # M/D 형식 (예: 1/15)
            md_match = re.match(r"(\d{1,2})/(\d{1,2})", date_str)
            if md_match:
                month = int(md_match.group(1))
                day = int(md_match.group(2))
                year = datetime.now().year
                return datetime(year, month, day, 18, 0, 0)
            
            # 요일 처리 (다음 해당 요일)
            weekdays = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
            for i, weekday in enumerate(weekdays):
                if weekday in date_str:
                    today = datetime.now().weekday()
                    days_ahead = (i - today) % 7
                    if days_ahead == 0:  # 오늘이면 내일
                        days_ahead = 7
                    target_date = datetime.now() + timedelta(days=days_ahead)
                    return target_date.replace(hour=18, minute=0, second=0, microsecond=0)
            
        except Exception as e:
            logger.error(f"날짜 파싱 오류: {e}")
        
        return None
    
    def _parse_time_string(self, time_str: str) -> Optional[datetime]:
        """시간 문자열 파싱"""
        try:
            # HH:MM 형식
            time_match = re.match(r"(\d{1,2}):(\d{2})", time_str)
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2))
                today = datetime.now()
                return today.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # H시 형식
            hour_match = re.match(r"(\d{1,2})시", time_str)
            if hour_match:
                hour = int(hour_match.group(1))
                today = datetime.now()
                return today.replace(hour=hour, minute=0, second=0, microsecond=0)
            
        except Exception as e:
            logger.error(f"시간 파싱 오류: {e}")
        
        return None
    
    def _deduplicate_actions(self, actions: List[ActionItem]) -> List[ActionItem]:
        """중복 액션 제거"""
        seen = set()
        unique_actions = []
        
        for action in actions:
            # 제목과 설명의 해시로 중복 체크
            action_key = f"{action.title}_{action.description[:50]}"
            if action_key not in seen:
                seen.add(action_key)
                unique_actions.append(action)
        
        return unique_actions
    
    async def batch_extract_actions(self, messages: List[Dict], user_email: str = "pm.1@quickchat.dev") -> List[ActionItem]:
        """여러 메시지에서 액션 일괄 추출
        
        Args:
            messages: 메시지 리스트
            user_email: 사용자(PM) 이메일 주소
            
        Returns:
            액션 아이템 리스트
        """
        all_actions = []
        
        for message in messages:
            try:
                actions = self.extract_actions(message, user_email=user_email)
                all_actions.extend(actions)
            except Exception as e:
                logger.error(f"메시지 액션 추출 오류: {e}")
                continue
        
        # 우선순위별로 정렬
        priority_order = {"high": 3, "medium": 2, "low": 1}
        all_actions.sort(
            key=lambda x: (priority_order.get(x.priority, 1), x.deadline or datetime.max),
            reverse=True
        )
        
        logger.info(f"🎯 총 {len(all_actions)}개의 액션 추출 완료")
        return all_actions


# 테스트 함수
async def test_action_extractor():
    """액션 추출기 테스트"""
    extractor = ActionExtractor()
    
    test_messages = [
        {
            "msg_id": "msg_001",
            "sender": "김부장",
            "subject": "긴급: 내일 오전 10시 팀 미팅",
            "body": "내일 오전 10시에 3층 회의실에서 긴급 팀 미팅이 있습니다. 프로젝트 데드라인이 당겨져서 즉시 준비가 필요합니다.",
            "content": "내일 오전 10시에 3층 회의실에서 긴급 팀 미팅이 있습니다. 프로젝트 데드라인이 당겨져서 즉시 준비가 필요합니다."
        },
        {
            "msg_id": "msg_002",
            "sender": "박대리",
            "subject": "프로젝트 문서 검토 요청",
            "body": "프로젝트 문서 검토 부탁드립니다. 금요일까지 피드백 주시면 감사하겠습니다.",
            "content": "프로젝트 문서 검토 부탁드립니다. 금요일까지 피드백 주시면 감사하겠습니다."
        },
        {
            "msg_id": "msg_003",
            "sender": "이팀장",
            "subject": "월요일까지 보고서 제출",
            "body": "월요일까지 분기 보고서 제출해주세요. 긴급합니다.",
            "content": "월요일까지 분기 보고서 제출해주세요. 긴급합니다."
        }
    ]
    
    all_actions = await extractor.batch_extract_actions(test_messages)
    
    print(f"🎯 총 {len(all_actions)}개의 액션 추출:")
    for i, action in enumerate(all_actions, 1):
        print(f"\n{i}. {action.action_type.upper()} - {action.title}")
        print(f"   우선순위: {action.priority}")
        print(f"   요청자: {action.requester}")
        if action.deadline:
            print(f"   데드라인: {action.deadline.strftime('%Y-%m-%d %H:%M')}")
        print(f"   설명: {action.description[:100]}...")


if __name__ == "__main__":
    asyncio.run(test_action_extractor())
