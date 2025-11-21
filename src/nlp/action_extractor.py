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
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

# DeadlineValidatorService는 필요 시 lazy import
_deadline_validator = None


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
    
    def __init__(self, enable_llm_validation: bool = True):
        """
        Args:
            enable_llm_validation: LLM 기반 마감일 검증 활성화 여부 (기본값: True)
        """
        self.enable_llm_validation = enable_llm_validation
        self._message_summary = None  # MessageSummarizer 결과 캐시
        
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
            "부탁", "주세요", "주시길", "해주세요", "해주세요.", "정리해줘",
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
    
    def set_message_summary(self, summary_data: dict):
        """MessageSummarizer 결과 설정
        
        Args:
            summary_data: MessageSummarizer에서 분석한 결과 (validated_deadlines 포함)
        """
        self._message_summary = summary_data
        validated_deadlines = summary_data.get('validated_deadlines', [])
        if validated_deadlines:
            logger.debug(f"MessageSummarizer 결과 설정: {len(validated_deadlines)}개 검증된 마감일")
    
    def clear_message_summary(self):
        """MessageSummarizer 결과 초기화"""
        self._message_summary = None
    
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
        
        # sender_email이 없으면 sender에서 이메일 추출 시도
        if not sender_email and sender and "@" in sender:
            sender_email = sender
        
        # 메시지 수신 시간 추출 (마감일 기준 시간)
        message_time = None
        for time_field in ['sent_at', 'date', 'timestamp', 'created_at']:
            if time_field in message_data and message_data[time_field]:
                try:
                    from utils.datetime_utils import parse_iso_datetime
                    message_time = parse_iso_datetime(message_data[time_field])
                    break
                except:
                    pass
        
        # 전체 텍스트 (LLM 검증용)
        full_text = f"{subject}\n{content}"
        
        # 인스턴스 변수로 저장 (하위 메서드에서 사용)
        self._current_full_text = full_text
        self._current_message_time = message_time
        
        # 메시지 수신 시각 추출 (마감일 계산 기준)
        # 주의: simulated_datetime은 시뮬레이션 "현재 시각"이므로 사용하지 않음
        # date 필드가 실제 메시지 수신 시각
        message_date_str = message_data.get("date") or message_data.get("sent_at") or message_data.get("timestamp")
        self._reference_date = self._parse_message_date(message_date_str) if message_date_str else datetime.now()
        
        # 단순 인사/확인 메시지 필터링 (TODO 생성 안 함)
        if self._is_simple_acknowledgment(content, subject):
            logger.debug(f"단순 확인 메시지 필터링: {content[:50]}...")
            return []
        
        # 과거 완료 + 정보 공유 메시지 필터링 (TODO 생성 안 함)
        if self._is_past_info_sharing(content):
            logger.debug(f"과거 완료 정보 공유 메시지 필터링: {content[:50]}...")
            return []
        msg_id = message_data.get("msg_id", f"msg_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        
        # ✅ 중요: 사용자(PM)가 보낸 메시지는 TODO로 만들지 않음
        if sender_email and sender_email.lower() == user_email.lower():
            logger.debug(f"⏭️ 사용자가 보낸 메시지 스킵: {msg_id}")
            return []
        
        # 이메일 주소가 없는 경우 sender 이름으로 체크 (chat 메시지)
        if not sender_email and sender:
            # PM 이름 목록 (이정두, lee_jd 등)
            pm_names = ["kim jihoon", "이정두", "lee_jd", "leejd"]
            if any(pm_name in sender.lower() for pm_name in pm_names):
                logger.debug(f"⏭️ 사용자가 보낸 메시지 스킵 (이름 기반): {msg_id}, sender={sender}")
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
                self._extract_generic_requests(combined_text, sender, msg_id, full_text, message_time)
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

    def _extract_generic_requests(self, text: str, sender: str, msg_id: str, full_text: str = None, message_time: datetime = None) -> List[ActionItem]:
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
                    deadline=self._extract_deadline(normalized, full_text, message_time),
                    priority=priority,
                    assignee="나",
                    requester=sender,
                    source_message_id=msg_id,
                    context={"extracted_from": "generic_sentence"},
                )
            )

        # 글머리표나 리스트 형태의 요청도 액션으로 변환
        for bullet in self._extract_bullet_requests(text.splitlines(), sender, msg_id, full_text, message_time):
            actions.append(bullet)
        return actions

    def _extract_bullet_requests(
        self, lines: List[str], sender: str, msg_id: str, full_text: str = None, message_time: datetime = None
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
                    deadline=self._extract_deadline(line, full_text, message_time),
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
        """요청 표현인지 판단 (정보 공유/과거형/조건부 제안 제외)"""
        # 정보 공유 표현 (액션 아님) - 강화
        info_sharing_patterns = [
            "공유드립니다", "공유합니다", "안내드립니다", "안내합니다",
            "알려드립니다", "알립니다", "전달드립니다", "전달합니다",
            "보고드립니다", "보고합니다", "말씀드립니다",
            "공유 드립니다", "안내 드립니다", "알려 드립니다",
            "업데이트드립니다", "업데이트 드립니다",
            "for your information", "fyi", "just letting you know",
            "update you", "inform you", "share with you",
            # 일정 공유 패턴 추가
            "오늘의 일정", "오늘의 계획", "오늘의 주요", "오늘의 목표",
            "일정을 공유", "계획을 공유", "일정에 따라", "계획에 따라",
            "다음과 같이 진행", "아래와 같이 진행", "다음과 같이 업무",
            "현재 집중 작업", "현재 작업", "진행 상황 공유",
            "작업 계획", "업무 계획", "일정 정리", "계획 정리"
        ]
        
        # 과거형/완료형 표현 (액션 아님)
        past_tense_patterns = [
            "했습니다", "했어요", "했네요", "했음", "했다",
            "완료했", "진행했", "처리했", "확인했", "검토했",
            "보냈습니다", "전달했", "공유했", "작성했",
            "completed", "finished", "done", "sent", "shared"
        ]
        
        # 조건부 제안 표현 (액션 아님)
        conditional_offer_patterns = [
            "필요하시면", "필요하면", "원하시면", "원하면",
            "궁금하시면", "궁금하면", "관심있으시면",
            "언제든", "언제든지", "편하실 때", "시간되실 때",
            "if you need", "if needed", "if you want", "anytime", "whenever"
        ]
        
        # 정보 공유 표현이면 요청 아님
        if any(pattern in lowered for pattern in info_sharing_patterns):
            return False
        
        # 과거형 표현이면 요청 아님
        if any(pattern in lowered for pattern in past_tense_patterns):
            return False
        
        # 조건부 제안 표현이면 요청 아님
        if any(pattern in lowered for pattern in conditional_offer_patterns):
            return False
        
        # 요청 마커 체크
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
        
        # 문맥이 요청 표현인지 체크 (과거형/정보 공유 제외)
        context_lower = context.lower()
        if not self._looks_like_request(context_lower):
            logger.debug(f"키워드 '{keyword}' 주변 문맥이 요청 표현이 아님: {context[:50]}...")
            return None
        
        # 액션 제목 생성
        title = self._generate_action_title(action_type, context)
        
        # 우선순위 결정
        priority = self._determine_priority(text)
        
        # 데드라인 추출
        deadline = self._extract_deadline(
            text,
            getattr(self, '_current_full_text', None),
            getattr(self, '_current_message_time', None)
        )
        
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
        
        # 문맥이 요청 표현인지 체크 (과거형/정보 공유 제외)
        context_lower = context.lower()
        if not self._looks_like_request(context_lower):
            logger.debug(f"패턴 매칭 문맥이 요청 표현이 아님: {context[:50]}...")
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
    
    def _extract_deadline(self, text: str, full_text: Optional[str] = None, message_time: Optional[datetime] = None) -> Optional[datetime]:
        """데드라인 추출 (MessageSummarizer 검증 결과 우선 활용)
        
        Args:
            text: 분석할 텍스트 (문장 또는 단락)
            full_text: 전체 메시지 텍스트 (LLM 검증용, 선택)
            message_time: 메시지 수신 시간 (기준 시간)
            
        Returns:
            검증된 마감일 또는 None
        """
        # 0단계: MessageSummarizer 검증 결과 확인 (이미 LLM이 검증한 경우)
        if hasattr(self, '_message_summary') and self._message_summary:
            validated_deadlines = self._message_summary.get('validated_deadlines', [])
            
            # text에 해당하는 마감일이 있는지 확인
            for vd in validated_deadlines:
                if not vd.get('is_valid'):
                    continue
                
                vd_text = vd.get('text', '')
                vd_date = vd.get('date')
                vd_time = vd.get('time', '18:00')
                
                # text에 마감일 텍스트가 포함되어 있으면 사용
                if vd_text and vd_text in text:
                    try:
                        # 날짜 파싱
                        deadline_dt = datetime.strptime(vd_date, '%Y-%m-%d')
                        
                        # 시간 추가
                        hour, minute = map(int, vd_time.split(':'))
                        deadline_dt = deadline_dt.replace(hour=hour, minute=minute)
                        
                        # timezone 추가
                        if deadline_dt.tzinfo is None:
                            deadline_dt = deadline_dt.replace(tzinfo=timezone.utc)
                        
                        logger.info(
                            f"✅ MessageSummarizer 검증 결과 사용: '{vd_text}' → "
                            f"{deadline_dt.strftime('%Y-%m-%d %H:%M')}"
                        )
                        return deadline_dt
                    except Exception as e:
                        logger.warning(f"MessageSummarizer 마감일 파싱 실패: {e}")
        
        # 1단계: 규칙 기반 추출
        # 날짜 패턴들 (시간 정보 포함, 구체적인 것부터 매칭)
        date_patterns = [
            r"(오늘\s*(?:오전|오후)\s*\d{1,2}시(?:\s*\d{1,2}분)?)",  # 오늘 오후 5시
            r"(내일\s*(?:오전|오후)\s*\d{1,2}시(?:\s*\d{1,2}분)?)",  # 내일 오전 10시
            r"(오늘\s*(?:오전|오후)(?:\s*까지)?)",  # 오늘 오전까지, 오늘 오후까지
            r"(내일\s*(?:오전|오후)(?:\s*까지)?)",  # 내일 오전까지, 내일 오후까지
            r"(\d{1,2}월\s*\d{1,2}일\s*(?:오전|오후)?\s*\d{1,2}시?)",  # 12월 20일 오후 3시
            r"(\d{1,2}월\s*\d{1,2}일)",  # 12월 20일
            r"(\d{1,2}/\d{1,2})",  # 12/20
            r"(\d{4}-\d{2}-\d{2})",  # 2025-12-20
            r"(오늘|내일)",  # 오늘, 내일
            r"(이번 주|다음 주)",  # 이번 주, 다음 주
            r"(\w+요일)"  # 월요일, 화요일 등
        ]
        
        extracted_deadline = None
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                date_str = match.group(1)
                extracted_deadline = self._parse_date_string(date_str)
                if extracted_deadline:
                    break
        
        # 마감일이 없으면 종료
        if not extracted_deadline:
            return None
        
        # 2단계: MessageSummarizer 결과가 없을 때는 규칙 기반만 사용
        # (백그라운드 분석에서 이미 LLM 검증이 진행되므로 중복 호출 방지)
        logger.debug(
            f"규칙 기반 마감일 추출: {extracted_deadline.strftime('%Y-%m-%d %H:%M')} "
            f"(MessageSummarizer 검증 대기 중)"
        )
        return extracted_deadline
    
    def _extract_deadline_from_match(self, match: str, action_type: str) -> Optional[datetime]:
        """매칭된 부분에서 데드라인 추출"""
        if action_type == "deadline":
            return self._parse_date_string(match)
        elif action_type == "meeting":
            return self._parse_time_string(match)
        
        return None
    
    def _parse_date_string(self, date_str: str) -> Optional[datetime]:
        """날짜 문자열 파싱 (메시지 수신 시각 기준)"""
        try:
            # 기준 날짜 (메시지 수신 시각)
            reference_date = getattr(self, '_reference_date', datetime.now())
            
            # 시간 정보 추출 (오전/오후 포함)
            hour = 18  # 기본값
            minute = 0
            
            # "오전까지", "오후까지" 처리 (시간 없이)
            if "오전" in date_str and "까지" in date_str and "시" not in date_str:
                hour = 12  # 오전까지 = 12시 (정오)
                minute = 0
            elif "오후" in date_str and "까지" in date_str and "시" not in date_str:
                hour = 18  # 오후까지 = 18시
                minute = 0
            else:
                # "오후 5시", "오전 10시", "오후 3시 30분" 등 파싱
                time_pattern = r'(오전|오후)\s*(\d{1,2})시(?:\s*(\d{1,2})분)?'
                time_match = re.search(time_pattern, date_str)
                if time_match:
                    period = time_match.group(1)
                    hour_val = int(time_match.group(2))
                    minute_val = int(time_match.group(3)) if time_match.group(3) else 0
                    
                    # 오후 처리
                    if period == "오후" and hour_val < 12:
                        hour = hour_val + 12
                    elif period == "오전":
                        hour = hour_val
                    else:
                        hour = hour_val
                    minute = minute_val
                else:
                    # "5시", "17시", "15시까지" 등 파싱
                    simple_time_pattern = r'(\d{1,2})시(?:\s*(\d{1,2})분)?'
                    simple_time_match = re.search(simple_time_pattern, date_str)
                    if simple_time_match:
                        hour_val = int(simple_time_match.group(1))
                        minute_val = int(simple_time_match.group(2)) if simple_time_match.group(2) else 0
                        
                        # 15시 같은 24시간 형식은 그대로 사용
                        hour = hour_val
                        minute = minute_val
            
            # 오늘, 내일 처리
            if "오늘" in date_str:
                return reference_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
            elif "내일" in date_str:
                tomorrow = reference_date + timedelta(days=1)
                return tomorrow.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # 월/일 형식 (예: 1월 15일)
            month_day_match = re.match(r"(\d{1,2})월\s*(\d{1,2})일", date_str)
            if month_day_match:
                month = int(month_day_match.group(1))
                day = int(month_day_match.group(2))
                year = reference_date.year
                return datetime(year, month, day, 18, 0, 0)
            
            # M/D 형식 (예: 1/15)
            md_match = re.match(r"(\d{1,2})/(\d{1,2})", date_str)
            if md_match:
                month = int(md_match.group(1))
                day = int(md_match.group(2))
                year = reference_date.year
                return datetime(year, month, day, 18, 0, 0)
            
            # 요일 처리 (다음 해당 요일)
            weekdays = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
            for i, weekday in enumerate(weekdays):
                if weekday in date_str:
                    today = reference_date.weekday()
                    days_ahead = (i - today) % 7
                    if days_ahead == 0:  # 오늘이면 내일
                        days_ahead = 7
                    target_date = reference_date + timedelta(days=days_ahead)
                    return target_date.replace(hour=18, minute=0, second=0, microsecond=0)
            
        except Exception as e:
            logger.error(f"날짜 파싱 오류: {e}")
        
        return None
    
    def _parse_message_date(self, date_str: str) -> datetime:
        """메시지 날짜 문자열을 datetime으로 파싱 (timezone-naive로 변환)"""
        try:
            from dateutil import parser
            dt = parser.parse(date_str)
            # timezone 정보 제거 (naive datetime으로 변환)
            if dt.tzinfo is not None:
                dt = dt.replace(tzinfo=None)
            return dt
        except:
            try:
                # ISO 형식 시도
                dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                # timezone 정보 제거
                if dt.tzinfo is not None:
                    dt = dt.replace(tzinfo=None)
                return dt
            except:
                logger.warning(f"메시지 날짜 파싱 실패: {date_str}, 현재 시각 사용")
                return datetime.now()
    
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
    
    def _is_past_info_sharing(self, content: str) -> bool:
        """과거 완료 + 정보 공유 메시지 판별
        
        Args:
            content: 메시지 본문
            
        Returns:
            True if 과거 완료 정보 공유 메시지, False otherwise
        """
        content_lower = content.lower()
        
        # 과거 완료 표현
        past_tense_patterns = [
            '논의한', '진행한', '완료한', '정리한', '검토한', '확인한',
            '작업한', '리뷰한', '분석한', '공유한', '전달한', 
            '정리하였습니다', '완료하였습니다', '진행하였습니다',
            '완료되었습니다', '마무리했습니다', '문서화하여'
        ]
        
        # 정보 공유/제출 표현
        info_sharing_patterns = [
            '공유드립니다', '알려드립니다', '보고드립니다', '안내드립니다',
            '전달드립니다', '공유합니다', '알립니다',
            '제출합니다', '보내겠습니다', '공유해 주시면'
        ]
        
        # 조건부 요청 (선택적)
        conditional_patterns = [
            '필요한 경우', '필요하시면', '궁금하시면', '원하시면'
        ]
        
        has_past = any(pattern in content for pattern in past_tense_patterns)
        has_sharing = any(pattern in content for pattern in info_sharing_patterns)
        has_conditional = any(pattern in content for pattern in conditional_patterns)
        
        # 과거 완료 + 정보 공유 = 정보 전달 목적
        if has_past and has_sharing:
            return True
        
        # 과거 완료 + 조건부 요청 = 정보 전달 목적
        if has_past and has_conditional:
            return True
        
        # 정보 공유 + 조건부 요청만 = 정보 전달 목적
        if has_sharing and has_conditional and not self._has_clear_request(content):
            return True
        
        return False
    
    def _has_clear_request(self, content: str) -> bool:
        """명확한 요청 동사가 있는지 확인"""
        request_verbs = [
            '제출해', '완료해', '검토해', '확인해', '승인해', '참석해',
            '준비해', '작성해', '수정해', '업데이트해', '공유해주', '알려주',
            '부탁드립니다', '부탁합니다', '바랍니다'
        ]
        
        return any(verb in content for verb in request_verbs)
    
    def _is_simple_acknowledgment(self, content: str, subject: str = "") -> bool:
        """단순 인사/확인 메시지 판별
        
        Args:
            content: 메시지 본문
            subject: 메시지 제목
            
        Returns:
            True if 단순 확인 메시지, False otherwise
        """
        # 전체 텍스트
        full_text = f"{subject} {content}".strip()
        content_clean = content.strip()
        
        # 1. 너무 짧은 메시지 (100자 미만) - 단순 확인 패턴
        if len(content_clean) < 100:
            simple_patterns = [
                r"^.*안녕하세요.*확인했습니다\.?$",
                r"^.*안녕하세요.*알겠습니다\.?$",
                r"^.*확인했습니다\.?$",
                r"^.*알겠습니다\.?$",
                r"^.*네,?\s*감사합니다\.?$",
                r"^.*네,?\s*알겠습니다\.?$",
                r"^.*감사합니다\.?$",
                r"^.*고맙습니다\.?$",
                r"^.*수고하세요\.?$",
                r"^.*작업 중입니다\.?$",
                r"^.*진행 중입니다\.?$",
                r"^.*확인했어요\.?$",
                r"^.*알았어요\.?$",
                r"^.*처리하겠습니다\.?$",
                r"^.*진행하겠습니다\.?$",
                r"^.*ok\.?$",
                r"^.*okay\.?$",
                r"^.*got it\.?$",
                r"^.*understood\.?$",
                r"^.*thanks\.?$",
                r"^.*thank you\.?$",
            ]
            
            for pattern in simple_patterns:
                if re.match(pattern, content_clean, re.IGNORECASE | re.DOTALL):
                    logger.debug(f"단순 확인 메시지 필터링 (패턴 매칭): {content_clean[:50]}...")
                    return True
        
        # 2. 인사만 있는 메시지
        greeting_only_patterns = [
            r"^안녕하세요[,.]?\s*$",
            r"^안녕하세요[,.]?\s+[가-힣]+입니다[.]?\s*$",
            r"^hi[,.]?\s*$",
            r"^hello[,.]?\s*$",
            r"^good morning[,.]?\s*$",
            r"^good afternoon[,.]?\s*$",
        ]
        
        for pattern in greeting_only_patterns:
            if re.match(pattern, full_text.strip(), re.IGNORECASE):
                logger.debug(f"인사만 있는 메시지 필터링: {full_text[:50]}...")
                return True
        
        # 3. 단순 상태 보고 (요청 없음) - 매우 짧은 메시지만
        if len(content_clean) < 80:  # 80자 미만만 체크
            status_report_patterns = [
                r"^.*오늘의?\s*(작업|업무)\s*보고\s*드립니다\.?$",
                r"^.*진행\s*상황\s*공유\s*드립니다\.?$",
                r"^.*작업\s*완료\s*보고\s*드립니다\.?$",
            ]
            
            # 요청 키워드가 없으면 단순 보고로 판단
            request_keywords = ["부탁", "요청", "주세요", "해주", "필요", "바랍니다", "검토", "확인", "피드백", "의견"]
            has_request = any(keyword in content_clean for keyword in request_keywords)
            
            if not has_request:
                for pattern in status_report_patterns:
                    if re.match(pattern, content_clean, re.IGNORECASE | re.DOTALL):
                        logger.debug(f"단순 상태 보고 필터링: {content_clean[:50]}...")
                        return True
        
        return False
    
    def _deduplicate_actions(self, actions: List[ActionItem]) -> List[ActionItem]:
        """중복 액션 제거 - 같은 발신자 + 같은 메시지에서 여러 유형의 TODO 생성 방지"""
        if not actions:
            return []
        
        if len(actions) == 1:
            return actions
        
        # 같은 메시지에서 여러 액션이 추출된 경우
        # → 발신자(requester)가 모두 같고, source_message_id도 같음
        # → 우선순위가 가장 높은 유형 1개만 선택
        
        # 유형 우선순위 (높을수록 중요)
        type_priority = {
            "deadline": 6,  # 마감 작업이 가장 중요
            "meeting": 5,   # 미팅 참석
            "task": 4,      # 일반 업무
            "review": 3,    # 문서 검토
            "response": 2,  # 답변 작성
            "documentation": 1,
        }
        
        # 가장 우선순위가 높은 액션 선택
        best_action = max(
            actions,
            key=lambda a: (
                type_priority.get(a.action_type, 0),
                len(a.description)  # 같은 우선순위면 설명이 더 긴 것
            )
        )
        
        if len(actions) > 1:
            logger.debug(
                f"중복 액션 제거: {len(actions)}개 → 1개 "
                f"(발신자: {best_action.requester}, 선택 유형: {best_action.action_type})"
            )
        
        return [best_action]
    
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
