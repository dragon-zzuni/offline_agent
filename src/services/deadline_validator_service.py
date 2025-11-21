# -*- coding: utf-8 -*-
"""
마감일 검증 서비스

규칙 기반으로 추출된 마감일을 LLM으로 검증하여 정확도를 높입니다.
"""
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from src.services import LLMClient

logger = logging.getLogger(__name__)


class DeadlineValidatorService:
    """마감일 검증 서비스
    
    규칙 기반으로 추출된 마감일이 실제로 유효한지 LLM으로 검증합니다.
    """
    
    def __init__(self, llm_client: Optional[LLMClient] = None):
        """
        Args:
            llm_client: LLM 클라이언트 (None이면 새로 생성)
        """
        self.llm_client = llm_client or LLMClient()
        logger.info("DeadlineValidatorService 초기화 완료")
    
    def validate_deadline(
        self,
        text: str,
        extracted_deadline: Optional[datetime],
        message_time: Optional[datetime] = None
    ) -> Optional[datetime]:
        """마감일 검증
        
        Args:
            text: 원본 텍스트 (subject + body)
            extracted_deadline: 규칙 기반으로 추출된 마감일
            message_time: 메시지 수신 시간 (기준 시간)
            
        Returns:
            검증된 마감일 (유효하지 않으면 None)
        """
        # 마감일이 없으면 검증 불필요
        if not extracted_deadline:
            return None
        
        # 텍스트가 너무 짧으면 검증 스킵
        if not text or len(text.strip()) < 10:
            return extracted_deadline
        
        # LLM으로 검증 (시간도 함께 추출)
        try:
            validated_deadline = self._validate_with_llm(text, extracted_deadline, message_time)
            
            if validated_deadline:
                logger.info(f"✅ 마감일 검증 성공: {validated_deadline.strftime('%Y-%m-%d %H:%M')}")
                return validated_deadline
            else:
                logger.info(f"❌ 마감일 검증 실패: {extracted_deadline.strftime('%Y-%m-%d')} (질문/과거 표현)")
                return None
                
        except Exception as e:
            logger.error(f"마감일 검증 오류: {e}")
            # 오류 시 원본 마감일 유지 (보수적 접근)
            return extracted_deadline
    
    def _validate_with_llm(
        self,
        text: str,
        deadline: datetime,
        message_time: Optional[datetime]
    ) -> Optional[datetime]:
        """LLM으로 마감일 유효성 검증 및 시간 추출
        
        Args:
            text: 원본 텍스트
            deadline: 추출된 마감일
            message_time: 메시지 수신 시간
            
        Returns:
            유효한 마감일 (시간 업데이트됨) 또는 None (무효)
        """
        # 메시지 시간 포맷팅
        msg_time_str = ""
        if message_time:
            msg_time_str = f"\n메시지 수신 시간: {message_time.strftime('%Y-%m-%d %H:%M')}"
        
        deadline_str = deadline.strftime('%Y-%m-%d')
        
        prompt = f"""다음 메시지에서 추출된 마감일이 실제로 유효한 마감일인지 판단하고, 정확한 마감 시간을 추출해주세요.

메시지 내용:
{text[:500]}
{msg_time_str}

추출된 마감일: {deadline_str}

다음 경우는 **유효하지 않은** 마감일입니다:
1. 질문 형태 ("언제까지 가능하신가요?", "언제까지 공유해주실 수 있을까요?")
2. 과거 완료 표현 ("오늘 리뷰한", "오늘 진행한", "오늘 완료된")
3. 단순 정보 공유 ("오늘 진행 상황", "오늘 회의 내용")
4. 불확실한 표현 ("가능하면", "여유 있을 때")

다음 경우는 **유효한** 마감일입니다:
1. 명확한 요청 + 날짜 ("내일까지 제출해주세요", "12월 20일까지 완료 부탁드립니다")
2. 마감 표현 ("오늘 중으로 검토 부탁", "내일까지 피드백 주세요")

**마감 시간 추출 규칙:**
- "오늘 중으로", "오늘까지" → 18:00
- "내일까지" (시간 명시 없음) → 18:00
- "내일 오전까지" → 12:00
- "내일 오후까지" → 18:00
- "내일 저녁까지" → 21:00
- "X시까지" → 명시된 시간
- "X시 Y분까지" → 명시된 시간

판단 결과를 다음 형식으로 답변해주세요:
VALID: [YES/NO]
TIME: [HH:MM] (유효한 경우만, 예: 12:00, 18:00)
REASON: [한 줄 이유]

예시 1:
VALID: NO
TIME: N/A
REASON: "언제까지 공유해주실 수 있을까요?"는 질문이므로 마감일이 아님

예시 2:
VALID: YES
TIME: 12:00
REASON: "내일 오전까지"는 명확한 마감 요청이며 오전은 12:00
"""
        
        try:
            llm_response = self.llm_client.generate(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,  # 낮은 온도로 일관성 확보
                max_tokens=100
            )
            
            result = llm_response.content.strip()
            result_upper = result.upper()
            
            # 응답 파싱
            if "VALID: YES" in result_upper:
                # 시간 추출
                if "TIME:" in result_upper:
                    time_line = [line for line in result.split('\n') if 'TIME:' in line.upper()]
                    if time_line:
                        time_str = time_line[0].split(':', 1)[1].strip()
                        # HH:MM 형식 파싱
                        import re
                        time_match = re.search(r'(\d{1,2}):(\d{2})', time_str)
                        if time_match:
                            hour = int(time_match.group(1))
                            minute = int(time_match.group(2))
                            # deadline의 시간 부분 업데이트
                            deadline = deadline.replace(hour=hour, minute=minute, second=0, microsecond=0)
                            logger.info(f"✅ 마감 시간 추출: {hour:02d}:{minute:02d}")
                
                # 이유 추출
                if "REASON:" in result_upper:
                    reason = result.split("REASON:")[1].strip().split('\n')[0]
                    logger.debug(f"마감일 유효: {reason}")
                
                return deadline  # 업데이트된 deadline 반환
            elif "VALID: NO" in result_upper:
                # 이유 추출
                if "REASON:" in result_upper:
                    reason = result.split("REASON:")[1].strip().split('\n')[0]
                    logger.debug(f"마감일 무효: {reason}")
                return None  # 무효
            else:
                # 파싱 실패 시 보수적으로 유효로 처리
                logger.warning(f"LLM 응답 파싱 실패: {result}")
                return deadline  # 원본 deadline 반환
                
        except Exception as e:
            logger.error(f"LLM 검증 오류: {e}")
            # 오류 시 보수적으로 원본 deadline 반환
            return deadline
    
    def has_deadline_keyword(self, text: str) -> bool:
        """마감일 관련 키워드가 있는지 확인
        
        Args:
            text: 원본 텍스트
            
        Returns:
            True면 마감일 키워드 있음
        """
        deadline_keywords = [
            "까지", "마감", "deadline", "제출", "due", "완료", 
            "내일", "오늘", "월", "일", "요일"
        ]
        
        text_lower = text.lower()
        return any(kw in text_lower for kw in deadline_keywords)
    
    def should_validate(self, text: str) -> bool:
        """마감일 검증이 필요한지 판단
        
        Args:
            text: 원본 텍스트
            
        Returns:
            True면 검증 필요, False면 불필요
        """
        # 마감일 키워드가 없으면 검증 불필요
        if not self.has_deadline_keyword(text):
            return False
        
        # 의문문 패턴 (질문)
        question_patterns = [
            "언제까지", "언제쯤", "가능하신가요", "가능할까요",
            "주실 수 있을까요", "주실 수 있나요", "알려주세요",
            "when can", "when could", "is it possible"
        ]
        
        text_lower = text.lower()
        
        # 질문 패턴이 있으면 검증 필요
        for pattern in question_patterns:
            if pattern in text_lower:
                return True
        
        # 과거 완료 패턴
        past_patterns = [
            "리뷰한", "진행한", "완료된", "작성한", "정리한",
            "reviewed", "completed", "finished"
        ]
        
        for pattern in past_patterns:
            if pattern in text_lower:
                return True
        
        # 기본적으로 검증 불필요 (규칙 기반 결과 신뢰)
        return False
