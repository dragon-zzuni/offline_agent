# -*- coding: utf-8 -*-
"""
메시지 요약 모듈 - LLM을 사용하여 이메일/메신저 메시지 요약
"""
import asyncio
import logging
import json
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import functools
import requests

from config.settings import LLM_CONFIG, PRIORITY_RULES

logger = logging.getLogger(__name__)






@dataclass
class MessageSummary:
    """메시지 요약 데이터 클래스"""
    original_id: str
    summary: str
    key_points: List[str]
    sentiment: str  # positive, negative, neutral
    urgency_level: str  # high, medium, low
    action_required: bool
    suggested_response: Optional[str] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
    
    def to_dict(self) -> Dict:
        """딕셔너리로 변환"""
        return {
            "original_id": self.original_id,
            "summary": self.summary,
            "key_points": self.key_points,
            "sentiment": self.sentiment,
            "urgency_level": self.urgency_level,
            "action_required": self.action_required,
            "suggested_response": self.suggested_response,
            "created_at": self.created_at.isoformat()
        }

class MessageSummarizer:
    """메시지 요약기"""
    
    def _build_transcript(self, messages: List[Dict], max_chars: int = 12000) -> str:
        """여러 메시지를 시간순으로 묶어 한 번에 요약할 수 있는 전개문 생성"""
        rows, total = [], 0

        def _ts(m):
            return (m.get("date") or m.get("timestamp") or m.get("datetime") or "")

        for m in sorted(messages, key=_ts):
            sender = (m.get("sender") or m.get("username") or "").strip()
            text   = (m.get("content") or m.get("body") or m.get("message") or "").strip()
            if not text:
                continue
            if (m.get("type") == "system") or (sender.lower() == "system"):
                continue

            line = f"{sender}: {text}"
            if total + len(line) > max_chars:
                break
            rows.append(line)
            total += len(line) + 1

        return "\n".join(rows)

    def _conversation_prompt(self, transcript: str) -> str:
        return f"""
    아래는 여러 사람이 주고받은 대화 전체입니다. 대화 흐름을 분석해 **순수 JSON만** 출력하세요.
    반드시 소문자 json이라는 단어를 포함한 json 문자열로 출력하세요.

    <대화>
    {transcript}

    JSON 스키마:
    {{
    "summary": "대화 전체 핵심 요약 (3~6문장)",
    "key_points": ["핵심 포인트 1", "핵심 포인트 2"],
    "decisions": ["확정된 결정 사항"],
    "unresolved": ["미해결/후속 필요 이슈"],
    "risks": ["리스크/주의사항"],
    "action_items": [
        {{"title":"해야 할 일", "priority":"High|Medium|Low", "owner":"선택", "due":"선택"}}
    ]
    }}
    """

    class ConversationSummary:
        def __init__(self, data: Dict):
            self.summary      = data.get("summary", "")
            self.key_points   = data.get("key_points", [])
            self.decisions    = data.get("decisions", [])
            self.unresolved   = data.get("unresolved", [])
            self.risks        = data.get("risks", [])
            self.action_items = data.get("action_items", [])

        def to_text(self) -> str:
            parts = []
            parts.append("■ 대화 흐름 요약")
            parts.append("="*60)
            parts.append(self.summary or "(요약 없음)")
            parts.append("")
            parts.append("■ 핵심 포인트")
            parts.append("- " + "\n- ".join(self.key_points or ["(없음)"]))
            parts.append("")
            if self.decisions:
                parts.append("■ 결정 사항")
                parts.append("- " + "\n- ".join(self.decisions))
                parts.append("")
            if self.unresolved:
                parts.append("■ 미해결/후속 필요")
                parts.append("- " + "\n- ".join(self.unresolved))
                parts.append("")
            if self.risks:
                parts.append("■ 리스크/주의")
                parts.append("- " + "\n- ".join(self.risks))
                parts.append("")
            if self.action_items:
                parts.append("■ 실행 항목(우선순위)")
                parts.append("="*60)
                for i,a in enumerate(self.action_items,1):
                    parts.append(f"{i}. [{a.get('priority','Low')}] {a.get('title','')}"
                                + (f" (담당:{a.get('owner')})" if a.get('owner') else "")
                                + (f" (기한:{a.get('due')})" if a.get('due') else ""))
            return "\n".join(parts)

    async def summarize_conversation(self, messages: List[Dict]) -> Dict:
        """대화 전체를 1회 호출로 요약하여 dict(JSON)으로 반환"""
        transcript = self._build_transcript(messages, max_chars=12000)
        if not transcript or not self.is_available or not self.chat_url:
            return {"summary": "", "key_points": [], "decisions": [], "unresolved": [], "risks": [], "action_items": []}

        prompt = self._conversation_prompt(transcript)
        resp_json = await self._call_chat_completion(
            [
                {"role": "system", "content": "당신은 회의/대화 요약 전문가입니다. 액션아이템을 명확히 뽑습니다."},
                {"role": "user", "content": prompt},
            ],
            force_json=True,
            max_tokens=self.max_tokens,
        )
        if not resp_json:
            return {"summary": "", "key_points": [], "decisions": [], "unresolved": [], "risks": [], "action_items": []}

        choices = resp_json.get("choices") or []
        text = ""
        if choices:
            message = choices[0].get("message") or {}
            text = (message.get("content") or "").strip().strip("`")

        s, e = text.find("{"), text.rfind("}") + 1
        try:
            return json.loads(text[s:e])
        except Exception:
            return {"summary": text, "key_points": [], "decisions": [], "unresolved": [], "risks": [], "action_items": []}

    def __init__(self, api_key: str = None):
        self.provider = (LLM_CONFIG.get("provider") or "azure").lower()
        self.model = LLM_CONFIG.get("model", "openrouter/auto")
        self.max_tokens = LLM_CONFIG.get("max_tokens", 1000)
        self.temperature = LLM_CONFIG.get("temperature", 0.3)

        self.is_available = False
        self.chat_url: Optional[str] = None
        self.headers: Dict[str, str] = {}
        self.payload_model: Optional[str] = self.model
        self.session = requests.Session()

        if self.provider == "azure":
            key = api_key or LLM_CONFIG.get("azure_api_key") or os.getenv("AZURE_OPENAI_KEY")
            endpoint = (LLM_CONFIG.get("azure_endpoint") or os.getenv("AZURE_OPENAI_ENDPOINT") or "").rstrip("/")
            deployment = LLM_CONFIG.get("azure_deployment") or os.getenv("AZURE_OPENAI_DEPLOYMENT")
            api_version = LLM_CONFIG.get("azure_api_version") or os.getenv("AZURE_OPENAI_API_VERSION") or "2024-02-15"
            if key and endpoint and deployment:
                self.chat_url = f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"
                self.headers = {"api-key": key, "Content-Type": "application/json"}
                self.payload_model = None
                self.is_available = True
        elif self.provider == "openrouter":
            key = api_key or LLM_CONFIG.get("openrouter_api_key") or os.getenv("OPENROUTER_API_KEY")
            base_url = LLM_CONFIG.get("openrouter_base_url") or "https://openrouter.ai/api/v1"
            if key:
                self.chat_url = f"{base_url}/chat/completions"
                self.headers = {
                    "Authorization": f"Bearer {key}",
                    "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", "https://github.com/dragon-zzuni/smart_assistant"),
                    "X-Title": os.getenv("OPENROUTER_APP_NAME", "smart_assistant"),
                    "Content-Type": "application/json",
                }
                self.is_available = True
        elif self.provider == "openai":
            key = api_key or LLM_CONFIG.get("openai_api_key") or os.getenv("OPENAI_API_KEY")
            if key:
                self.chat_url = "https://api.openai.com/v1/chat/completions"
                self.headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
                self.is_available = True

        if not self.is_available:
            logger.warning("LLM API 키가 설정되지 않았습니다. 기본 요약 모드로 동작합니다.")

    async def _call_chat_completion(self, messages: List[Dict], force_json: bool = False, max_tokens: Optional[int] = None) -> Optional[Dict]:
        if not self.is_available or not self.chat_url:
            return None

        payload: Dict[str, object] = {"messages": messages}
        if self.provider != "azure":
            payload["temperature"] = self.temperature
        token_limit = max_tokens if max_tokens is not None else self.max_tokens
        if token_limit is not None:
            if self.provider == "azure":
                # Azure GPT-5 chat API requires max_completion_tokens and pins temperature to the default.
                payload["max_completion_tokens"] = token_limit
            else:
                payload["max_tokens"] = token_limit

        if self.payload_model:
            payload["model"] = self.payload_model

        if self.provider == "azure":
            if force_json:
                payload["response_format"] = {"type": "json_object"}
        else:
            if force_json or self.provider == "openai":
                payload["response_format"] = {"type": "json_object"}

        logger.info("[Summarizer][LLM] provider=%s messages=%s", self.provider, json.dumps(messages, ensure_ascii=False)[:400])

        def _request():
            resp = self.session.post(self.chat_url, headers=self.headers, json=payload, timeout=40)
            resp.raise_for_status()
            return resp.json()

        # Retry logic with exponential backoff for 429 errors
        max_retries = 3
        base_delay = 2  # seconds - Rate limit 발생 시 재시도 대기 시간
        
        for attempt in range(max_retries):
            try:
                data = await asyncio.to_thread(_request)
                logger.debug("[Summarizer][LLM] response=%s", json.dumps(data, ensure_ascii=False)[:500])
                return data
            except Exception as exc:
                error_str = str(exc)
                
                # Check if it's a 429 (Too Many Requests) error
                if "429" in error_str and attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)  # Exponential backoff: 5s, 10s, 20s
                    logger.warning(f"[Summarizer][LLM] 429 Rate Limit - 재시도 {attempt + 1}/{max_retries} (대기: {delay}초)")
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.warning("[Summarizer][LLM] request error: %s", exc)
                    return None
        
        return None

    async def summarize_message(self, content: str, sender: str = "", subject: str = "") -> MessageSummary:
        if self.is_available and self.chat_url:
            try:
                return await self._llm_summarize(content, sender, subject)
            except Exception as exc:
                logger.error(f"메시지 요약 오류: {exc}")
        return self._basic_summarize(content, sender, subject)
    
    def _create_summarization_prompt(self, content: str, sender: str, subject: str) -> str:
        """요약 프롬프트 생성"""
        prompt = f"""
다음 메시지를 분석하여 JSON 형식으로 답변해주세요. 반드시 소문자 json이라는 단어를 포함한 json 문자열로만 응답하세요:

발신자: {sender}
제목: {subject}
내용: {content[:2000]}

다음 형식으로 분석해주세요:
{{
    "summary": "메시지의 핵심 내용을 2-3문장으로 요약",
    "key_points": ["핵심 포인트 1", "핵심 포인트 2", "핵심 포인트 3"],
    "sentiment": "positive/negative/neutral 중 하나",
    "urgency_level": "high/medium/low 중 하나",
    "action_required": true/false,
    "suggested_response": "권장 응답 내용 (선택사항)"
}}

## action_required 판단 기준 (매우 중요!)

이 메시지가 **수신자(PM)에게 구체적인 행동을 요구하는지** 신중하게 판단하세요.

### ✅ action_required = true (TODO 생성)

**1. 명확한 요청 동사가 있는 경우**
- "검토해 주세요", "확인 부탁드립니다", "피드백 주세요"
- "참석해 주세요", "제출해 주세요", "승인 부탁드립니다"
- "답변 부탁드립니다", "회신 부탁드립니다"

**2. 미래 일정에 대한 참석/준비 요청**
- "내일 미팅에 참석해 주세요"
- "다음 주 발표 준비 부탁드립니다"
- "금요일까지 보고서 제출 바랍니다"

**3. 의사결정이나 승인 요청**
- "이 안건에 대해 결정 부탁드립니다"
- "예산 승인 요청드립니다"

**4. 구체적인 작업 할당**
- "이 태스크를 담당해 주세요"
- "코드 리뷰 부탁드립니다"

### ❌ action_required = false (TODO 생성 안 함)

**1. 정보 공유 목적**
- "공유드립니다", "안내드립니다", "알려드립니다"
- "업데이트 드립니다", "보고드립니다"
- "for your information", "FYI", "just letting you know"
- **판단 기준**: 발신자가 일방적으로 정보를 전달하는 경우

**2. 과거 사건 보고**
- "미팅에서 논의했습니다", "작업을 완료했습니다"
- "검토를 진행했습니다", "확인했습니다"
- "completed", "finished", "done"
- **판단 기준**: 이미 끝난 일에 대한 보고

**3. 조건부 제안 (선택적)**
- "필요하시면 말씀해 주세요", "궁금하시면 연락 주세요"
- "원하시면 도와드리겠습니다", "언제든 말씀해 주세요"
- "if you need", "if you want", "anytime"
- **판단 기준**: 수신자가 원할 때만 행동하면 되는 경우

**4. 단순 인사/확인**
- "확인했습니다", "알겠습니다", "감사합니다"
- "수고하셨습니다", "잘 부탁드립니다"
- **판단 기준**: 구체적인 행동 요구가 없는 경우

**5. 진행 상황 공유 (요청 없음)**
- "현재 작업 중입니다", "진행 상황 공유드립니다"
- "오늘의 일정을 공유합니다", "작업 계획을 안내드립니다"
- **판단 기준**: 발신자의 계획/상태를 알리는 것뿐

**6. 빈 내용이나 템플릿**
- 표만 있고 내용이 없는 경우
- "안녕하세요, [이름]입니다" 같은 인사만 있는 경우
- **판단 기준**: 실질적인 내용이 없는 경우

### 🔍 애매한 경우 판단 방법

**질문 1**: 수신자가 이 메시지를 읽고 **반드시 해야 할 구체적인 행동**이 있는가?
- YES → action_required = true
- NO → action_required = false

**질문 2**: 발신자가 **수신자의 응답이나 행동을 기대**하는가?
- YES → action_required = true
- NO → action_required = false

**질문 3**: 이 메시지의 주요 목적이 **정보 전달**인가, **행동 요청**인가?
- 정보 전달 → action_required = false
- 행동 요청 → action_required = true

### 📝 추가 판단 기준

- **"요청:" 섹션 헤더**만 있고 실제 요청 내용이 없으면 → false
- **과거형 + 정보 공유**가 함께 있으면 → false
- **조건부 표현 + 선택적 제안**이면 → false
- **미래 일정 + 명확한 요청**이면 → true

## 기타 분석 기준

- urgency_level: 긴급 키워드(긴급, urgent, asap, 즉시, 오늘까지, deadline)가 있으면 high
- sentiment: 긍정적/부정적/중립적 톤 분석
"""
        return prompt

    async def _llm_summarize(self, content: str, sender: str = "", subject: str = "") -> MessageSummary:
        prompt = self._create_summarization_prompt(content, sender, subject)
        resp_json = await self._call_chat_completion(
            [
                {"role": "system", "content": "당신은 업무용 메시지 분석 전문가입니다. 이메일과 메신저 메시지를 분석하여 요약, 핵심 포인트, 감정, 긴급도, 필요한 액션을 파악합니다."},
                {"role": "user", "content": prompt},
            ],
            force_json=True,
        )

        if not resp_json:
            raise RuntimeError("LLM 응답이 비어 있습니다.")

        choices = resp_json.get("choices") or []
        result_text = ""
        if choices:
            message = choices[0].get("message") or {}
            result_text = message.get("content") or ""
        return self._parse_llm_response(result_text, sender)
    
    def _parse_llm_response(self, response_text: str, sender: str) -> MessageSummary:
        """LLM 응답 파싱"""
        try:
            # JSON 추출
            response_text = (response_text or "").strip().strip("`")
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = response_text[start_idx:end_idx]
                data = json.loads(json_str)
                
                return MessageSummary(
                    original_id=f"summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    summary=data.get("summary", ""),
                    key_points=data.get("key_points", []),
                    sentiment=data.get("sentiment", "neutral"),
                    urgency_level=data.get("urgency_level", "low"),
                    action_required=data.get("action_required", False),
                    suggested_response=data.get("suggested_response")
                )
        except Exception as e:
            logger.error(f"LLM 응답 파싱 오류: {e}")
        
        # 파싱 실패 시 기본 요약
        return self._basic_summarize(response_text, sender)
    
    def _basic_summarize(self, content: str, sender: str = "", subject: str = "") -> MessageSummary:
        """기본 요약 (LLM 없이)"""
        # 간단한 키워드 기반 분석
        urgency_keywords = PRIORITY_RULES.get("high_priority_keywords", [])
        action_keywords = ["요청", "부탁", "미팅", "회의", "보고서", "제출", "검토", "확인"]
        
        content_lower = content.lower()
        
        # 긴급도 분석
        urgency_level = "low"
        for keyword in urgency_keywords:
            if keyword in content_lower:
                urgency_level = "high"
                break
        
        # 액션 필요성 분석
        action_required = any(keyword in content_lower for keyword in action_keywords)
        
        # 감정 분석 (간단한 키워드 기반)
        positive_words = ["감사", "좋", "잘", "성공", "완료", "수고"]
        negative_words = ["문제", "오류", "실패", "늦", "미완료", "불만"]
        
        sentiment = "neutral"
        if any(word in content_lower for word in positive_words):
            sentiment = "positive"
        elif any(word in content_lower for word in negative_words):
            sentiment = "negative"
        
        # 기본 요약 생성
        summary = content[:200] + "..." if len(content) > 200 else content
        
        # 핵심 포인트 추출 (간단한 문장 분할)
        sentences = content.split('.')[:3]
        key_points = [s.strip() for s in sentences if s.strip()]
        
        return MessageSummary(
            original_id=f"basic_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            summary=summary,
            key_points=key_points,
            sentiment=sentiment,
            urgency_level=urgency_level,
            action_required=action_required
        )
    
    async def batch_summarize(self, messages: List[Dict], batch_callback=None, batch_size: int = 40) -> List[MessageSummary]:
        """여러 메시지를 배치 단위로 요약. 입력 순서를 보존합니다.
        
        Args:
            messages: 요약할 메시지 리스트
            batch_callback: 각 배치 완료 시 호출할 콜백 함수 (batch_idx, total_batches, batch_results)
            batch_size: 배치 크기 (기본값: 40)
        """
        if not messages:
            return []

        # 동시 실행 상한 (리밋/속도 균형용) - Rate limit 발생 시 자동 재시도
        CONCURRENCY = 3
        sem = asyncio.Semaphore(CONCURRENCY)

        results: List[MessageSummary] = [None] * len(messages)  # 입력 순서 유지용
        
        # 배치로 나누기
        total_messages = len(messages)
        num_batches = (total_messages + batch_size - 1) // batch_size
        
        logger.info(f"📝 {total_messages}개 메시지를 {num_batches}개 배치로 나누어 분석 시작 (배치 크기: {batch_size})")

        async def one(i: int, m: Dict):
            content = (m.get("content") or m.get("body") or "").strip()
            sender  = (m.get("sender")  or "").strip()
            subject = (m.get("subject") or "").strip()

            # 내용이 비면 호출하지 않고 기본 요약
            if not content:
                s = self._basic_summarize(content, sender, subject)
                s.original_id = m.get("msg_id") or s.original_id
                results[i] = s
                return

            try:
                async with sem:
                    # Rate limit 회피를 위한 요청 간 지연 (0.2초) - 429 발생 시 자동 재시도
                    if i > 0:
                        await asyncio.sleep(0.2)
                    
                    s = await self.summarize_message(content, sender, subject)
                    # ✅ 요약 객체에 원본 메시지 ID 연결 (핵심)
                    s.original_id = m.get("msg_id") or s.original_id
                    results[i] = s
            except Exception as e:
                logger.error(f"메시지 요약 오류 (index={i}): {e}")
                s = self._basic_summarize(content, sender, subject)
                s.original_id = m.get("msg_id") or s.original_id
                results[i] = s
        
        # 배치별로 처리
        for batch_idx in range(num_batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, total_messages)
            batch_messages = messages[start_idx:end_idx]
            
            logger.info(f"   📦 배치 {batch_idx + 1}/{num_batches}: {len(batch_messages)}개 메시지 분석 중...")
            
            # 배치 내 메시지들을 동시에 처리
            await asyncio.gather(*[asyncio.create_task(one(start_idx + i, m)) for i, m in enumerate(batch_messages)])
            
            # 배치 완료 - 현재까지의 결과 추출
            batch_results = results[start_idx:end_idx]
            completed_count = sum(1 for r in results[:end_idx] if r is not None)
            
            logger.info(f"   ✅ 배치 {batch_idx + 1}/{num_batches} 완료 (누적: {completed_count}/{total_messages}개)")
            
            # 콜백 호출 (있는 경우)
            if batch_callback:
                try:
                    await batch_callback(batch_idx + 1, num_batches, batch_results, completed_count)
                except Exception as e:
                    logger.error(f"배치 콜백 오류: {e}")

        logger.info(f"📝 {sum(1 for r in results if r is not None)}개 메시지 요약 완료")
        return results

    
    def _extract_deadlines(self, content: str) -> List[str]:
        """데드라인 추출"""
        import re
        
        deadline_patterns = [
            r"(\d{1,2}월\s*\d{1,2}일)",
            r"(\d{1,2}/\d{1,2})",
            r"(\d{4}-\d{2}-\d{2})",
            r"(오늘까지|내일까지|이번 주까지|다음 주까지)",
            r"(월요일까지|화요일까지|수요일까지|목요일까지|금요일까지)"
        ]
        
        deadlines = []
        for pattern in deadline_patterns:
            matches = re.findall(pattern, content)
            deadlines.extend(matches)
        
        return deadlines
    
    def _extract_meeting_info(self, content: str) -> Dict:
        """미팅 정보 추출"""
        import re
        
        meeting_info = {}
        
        # 시간 패턴
        time_pattern = r"(\d{1,2}:\d{2}|\d{1,2}시|\d{1,2}월\s*\d{1,2}일\s*\d{1,2}시)"
        time_matches = re.findall(time_pattern, content)
        if time_matches:
            meeting_info["time"] = time_matches[0]
        
        # 장소 패턴
        location_pattern = r"(회의실|오피스|사무실|카페|식당|\d+층|\w+룸)"
        location_matches = re.findall(location_pattern, content)
        if location_matches:
            meeting_info["location"] = location_matches[0]
        
        return meeting_info
    
    async def summarize_group(
        self,
        messages: List[Dict],
        group_label: str = ""
    ) -> Dict[str, Any]:
        """
        그룹화된 메시지들을 통합하여 요약
        이메일과 메신저 메시지를 모두 포함하여 처리
        
        Args:
            messages: 그룹 내 메시지 리스트
            group_label: 그룹 레이블 (예: "2025-01-15", "2025년 1월 3주차")
            
        Returns:
            요약 정보 딕셔너리
        """
        if not messages:
            return {
                "summary": "",
                "key_points": [],
                "decisions": [],
                "unresolved": [],
                "risks": [],
                "action_items": []
            }
        
        # 메시지 타입별 분류
        email_messages = [m for m in messages if m.get("type") == "email"]
        messenger_messages = [m for m in messages if m.get("type") == "messenger"]
        
        logger.info(
            f"📝 그룹 요약 시작 ({group_label}): "
            f"이메일 {len(email_messages)}건, 메신저 {len(messenger_messages)}건"
        )
        
        # 통합 요약 생성 (대화 요약 메서드 활용)
        summary_result = await self.summarize_conversation(messages)
        
        # 추가 메타데이터 포함
        summary_result["group_label"] = group_label
        summary_result["total_messages"] = len(messages)
        summary_result["email_count"] = len(email_messages)
        summary_result["messenger_count"] = len(messenger_messages)
        
        return summary_result
    
    async def batch_summarize_groups(
        self,
        grouped_messages: Dict[str, List[Dict]],
        unit: str = "daily"
    ) -> Dict[str, Dict[str, Any]]:
        """
        여러 그룹의 메시지를 동시에 요약
        
        Args:
            grouped_messages: 그룹 키를 키로 하는 메시지 그룹 딕셔너리
            unit: 그룹화 단위 ("daily", "weekly", "monthly")
            
        Returns:
            그룹 키를 키로 하는 요약 결과 딕셔너리
        """
        if not grouped_messages:
            return {}
        
        logger.info(f"📊 {len(grouped_messages)}개 그룹 요약 시작 (단위: {unit})")
        
        # 동시 실행 제한
        CONCURRENCY = 3
        sem = asyncio.Semaphore(CONCURRENCY)
        
        results: Dict[str, Dict[str, Any]] = {}
        
        async def summarize_one_group(group_key: str, messages: List[Dict]):
            try:
                async with sem:
                    # 그룹 레이블 생성
                    if unit == "daily":
                        label = f"{group_key} (일별)"
                    elif unit == "weekly":
                        label = f"{group_key} 주 (주별)"
                    elif unit == "monthly":
                        label = f"{group_key} (월별)"
                    else:
                        label = group_key
                    
                    summary = await self.summarize_group(messages, label)
                    results[group_key] = summary
                    
            except Exception as e:
                logger.error(f"그룹 요약 오류 ({group_key}): {e}")
                results[group_key] = {
                    "summary": f"요약 생성 실패: {str(e)}",
                    "key_points": [],
                    "decisions": [],
                    "unresolved": [],
                    "risks": [],
                    "action_items": [],
                    "group_label": group_key,
                    "total_messages": len(messages),
                    "email_count": sum(1 for m in messages if m.get("type") == "email"),
                    "messenger_count": sum(1 for m in messages if m.get("type") == "messenger")
                }
        
        # 모든 그룹 동시 요약
        tasks = [
            summarize_one_group(group_key, messages)
            for group_key, messages in grouped_messages.items()
        ]
        await asyncio.gather(*tasks)
        
        logger.info(f"✅ {len(results)}개 그룹 요약 완료")
        return results


# 테스트 함수
async def test_summarizer():
    """요약기 테스트"""
    summarizer = MessageSummarizer()
    
    test_messages = [
        {
            "sender": "김과장",
            "subject": "긴급: 내일 오전 10시 팀 미팅",
            "body": "안녕하세요. 내일 오전 10시에 3층 회의실에서 팀 미팅이 있습니다. 프로젝트 진행 상황을 보고하고 다음 주 계획을 논의할 예정입니다. 준비해주세요.",
            "content": "안녕하세요. 내일 오전 10시에 3층 회의실에서 팀 미팅이 있습니다. 프로젝트 진행 상황을 보고하고 다음 주 계획을 논의할 예정입니다. 준비해주세요."
        },
        {
            "sender": "박대리",
            "subject": "프로젝트 문서 검토 요청",
            "body": "프로젝트 문서 검토 부탁드립니다. 금요일까지 피드백 주시면 감사하겠습니다.",
            "content": "프로젝트 문서 검토 부탁드립니다. 금요일까지 피드백 주시면 감사하겠습니다."
        }
    ]
    
    summaries = await summarizer.batch_summarize(test_messages)
    
    print(f"📝 {len(summaries)}개 메시지 요약 완료")
    for summary in summaries:
        print(f"\n- 요약: {summary.summary}")
        print(f"  긴급도: {summary.urgency_level}")
        print(f"  액션 필요: {summary.action_required}")
        print(f"  핵심 포인트: {', '.join(summary.key_points)}")


if __name__ == "__main__":
    asyncio.run(test_summarizer())
