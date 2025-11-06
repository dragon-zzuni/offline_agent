# MessageSummarizer 사용 흐름 가이드

## 개요

`MessageSummarizer`는 이메일과 메신저 메시지를 LLM을 사용하여 요약하는 핵심 컴포넌트입니다.

## 1. Summarizer가 사용되는 위치

### 1.1 메인 분석 파이프라인 (`main.py`)

```python
# main.py의 analyze_messages() 메서드
async def analyze_messages(self) -> List[Dict]:
    """수집된 메시지를 분석하여 우선순위, 액션 등을 추출"""
    
    # 1. MessageSummarizer 초기화
    summarizer = MessageSummarizer()
    
    # 2. 배치 요약 실행 (여러 메시지를 동시에 요약)
    summaries = await summarizer.batch_summarize(self.collected_messages)
    
    # 3. 요약 결과를 메시지에 연결
    for msg, summary in zip(self.collected_messages, summaries):
        msg["summary"] = summary.to_dict()
    
    return analysis_results
```

**입력 데이터 구조:**
```python
message = {
    "msg_id": "unique_id",           # 메시지 고유 ID
    "type": "email" or "messenger",  # 메시지 타입
    "sender": "발신자 이름",
    "subject": "제목 (이메일만)",
    "content": "메시지 본문",
    "body": "메시지 본문 (대체 필드)",
    "timestamp": "2025-01-15T10:30:00Z",
    "priority": "high/medium/low"
}
```

**출력 데이터 구조:**
```python
summary = {
    "original_id": "msg_id",
    "summary": "메시지 핵심 요약 (2-3문장)",
    "key_points": ["포인트1", "포인트2", "포인트3"],
    "sentiment": "positive/negative/neutral",
    "urgency_level": "high/medium/low",
    "action_required": True/False,
    "suggested_response": "권장 응답 (선택)",
    "created_at": "2025-01-15T10:35:00Z"
}
```

### 1.2 그룹 요약 (`main_window.py`)

```python
# main_window.py의 _update_message_summaries() 메서드
async def _update_message_summaries(self, unit: str = "daily"):
    """메시지를 그룹화하여 요약 생성"""
    
    # 1. 메시지 그룹화 (일/주/월 단위)
    from nlp.message_grouping import group_messages_by_period
    grouped = group_messages_by_period(self.collected_messages, unit)
    
    # 2. MessageSummarizer로 그룹 요약
    summarizer = MessageSummarizer()
    group_summaries = await summarizer.batch_summarize_groups(grouped, unit)
    
    # 3. UI에 표시
    self.message_summary_panel.display_summaries(summaries)
```

**그룹 요약 입력:**
```python
grouped_messages = {
    "2025-01-15": [msg1, msg2, msg3],  # 일별
    "2025-W03": [msg4, msg5],          # 주별
    "2025-01": [msg6, msg7, msg8]      # 월별
}
```

**그룹 요약 출력:**
```python
group_summary = {
    "group_label": "2025-01-15 (일별)",
    "summary": "대화 전체 핵심 요약 (3~6문장)",
    "key_points": ["핵심 포인트 1", "핵심 포인트 2"],
    "decisions": ["확정된 결정 사항"],
    "unresolved": ["미해결/후속 필요 이슈"],
    "risks": ["리스크/주의사항"],
    "action_items": [
        {
            "title": "해야 할 일",
            "priority": "High",
            "owner": "담당자",
            "due": "기한"
        }
    ],
    "total_messages": 10,
    "email_count": 3,
    "messenger_count": 7
}
```

### 1.3 TODO 상세 다이얼로그 (`ui/todo_panel.py`)

```python
# TodoDetailDialog의 _generate_summary() 메서드
def _generate_summary(self):
    """LLM을 사용하여 요약 생성"""
    
    # 1. 원본 메시지 내용 가져오기
    src = _source_message_dict(self.todo)
    content = src.get("content") or src.get("body") or ""
    
    # 2. LLM 호출 (직접 호출, Summarizer 클래스 사용 안 함)
    summary = self._call_llm_for_summary(content)
    
    # 3. UI에 표시
    self.summary_text.setPlainText(summary)
```

**주의:** TODO 상세 다이얼로그는 `MessageSummarizer` 클래스를 사용하지 않고 직접 LLM API를 호출합니다.

## 2. GUI에서 요약이 표시되는 위치

### 2.1 메시지 탭 (MessageSummaryPanel)

**위치:** 메인 윈도우 우측 → "메시지" 탭

**표시 내용:**
- 일별/주별/월별 요약 카드
- 각 카드에는:
  - 📅 날짜/기간
  - 📨 총 메시지 수
  - 📧 이메일 수 / 💬 메신저 수
  - 🔴🟡⚪ 우선순위 분포
  - 👤 주요 발신자 (우선순위 배지 포함)
  - 📝 핵심 요약 (1-2줄)
  - 📌 주요 포인트 (최대 3개)

**코드 위치:**
```python
# ui/message_summary_panel.py
class MessageSummaryPanel(QWidget):
    def display_summaries(self, summaries: List[Dict]):
        """그룹화된 요약 표시"""
        for summary in summaries:
            card = self._create_summary_card(summary)
            self.summary_layout.addWidget(card)
```

### 2.2 TODO 리스트 (TodoPanel)

**위치:** 메인 윈도우 우측 → "TODO" 탭

**표시 내용:**
- TODO 항목 리스트
- 각 항목에는:
  - 🔴🟡⚪ 우선순위 아이콘
  - 제목
  - 간단한 요약 (회색 박스, 최대 80자)
  - 마감일 배지
  - 근거 수 배지

**코드 위치:**
```python
# ui/todo_panel.py
class BasicTodoItem(QWidget):
    def _create_brief_summary(self, todo: dict) -> str:
        """간단한 요약 생성 (첫 문장, 최대 80자)"""
        desc = todo.get("description", "")
        if not desc:
            return ""
        
        # 첫 문장만 추출
        first_sentence = desc.split(".")[0].strip()
        
        # 최대 80자로 제한
        if len(first_sentence) > 80:
            return first_sentence[:77] + "..."
        
        return first_sentence
```

### 2.3 TODO 상세 다이얼로그 (TodoDetailDialog)

**위치:** TODO 항목 클릭 → 팝업 다이얼로그

**표시 내용:**
- 📄 원본 메시지 영역 (상단)
  - 우선순위, 요청자, 유형, 마감일
  - 발신자, 제목, 플랫폼
  - 원본 메시지 전체 내용
- 📝 요약 및 액션 영역 (하단)
  - 📋 요약 생성 버튼 → LLM 요약 (3-5개 불릿 포인트)
  - ✉️ 회신 초안 작성 버튼 → LLM 회신 초안

**코드 위치:**
```python
# ui/todo_panel.py
class TodoDetailDialog(QDialog):
    def _generate_summary(self):
        """LLM을 사용하여 요약 생성"""
        summary = self._call_llm_for_summary(content)
        self.summary_text.setPlainText(summary)
    
    def _generate_reply(self):
        """LLM을 사용하여 회신 초안 생성"""
        reply = self._call_llm_for_reply(content, sender)
        self.reply_text.setPlainText(reply)
```

## 3. 400 Bad Request 오류 해결

### 문제 원인

Azure OpenAI API는 다른 공급자와 다른 파라미터를 사용합니다:
- ❌ `max_tokens` (OpenAI, OpenRouter)
- ✅ `max_completion_tokens` (Azure OpenAI)
- ❌ `temperature` (Azure는 기본값 사용)

### 해결 방법

```python
# ui/todo_panel.py의 _call_llm() 메서드
payload: Dict[str, object] = {
    "messages": [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ],
}

# Azure는 max_completion_tokens 사용
if provider == "azure":
    payload["max_completion_tokens"] = 500
else:
    payload["temperature"] = 0.7
    payload["max_tokens"] = 500
```

### API 버전 확인

Azure OpenAI API 버전은 안정적인 버전을 사용해야 합니다:
- ✅ `2024-08-01-preview` (권장)
- ✅ `2024-02-15-preview`
- ❌ `2025-04-01-preview` (존재하지 않음)

```python
# config/settings.py 또는 .env
AZURE_OPENAI_API_VERSION=2024-08-01-preview
```

## 4. 데이터 흐름 요약

```
1. 메시지 수집 (main.py)
   ↓
2. MessageSummarizer.batch_summarize()
   ↓ (각 메시지 요약)
   ├─ LLM 호출 (Azure/OpenAI/OpenRouter)
   ├─ 요약, 핵심 포인트, 감정, 긴급도 분석
   └─ MessageSummary 객체 생성
   ↓
3. 요약 결과를 메시지에 연결
   ↓
4. GUI 표시
   ├─ MessageSummaryPanel (그룹 요약)
   ├─ TodoPanel (TODO 리스트)
   └─ TodoDetailDialog (상세 요약/회신)
```

## 5. 주요 메서드 정리

| 메서드 | 용도 | 입력 | 출력 |
|--------|------|------|------|
| `summarize_message()` | 단일 메시지 요약 | content, sender, subject | MessageSummary |
| `batch_summarize()` | 여러 메시지 동시 요약 | List[Dict] | List[MessageSummary] |
| `summarize_conversation()` | 대화 전체 요약 | List[Dict] | Dict (JSON) |
| `summarize_group()` | 그룹 메시지 통합 요약 | List[Dict], group_label | Dict |
| `batch_summarize_groups()` | 여러 그룹 동시 요약 | Dict[str, List[Dict]] | Dict[str, Dict] |

## 6. 설정 파일

### config/settings.py

```python
LLM_CONFIG = {
    "provider": "azure",  # "azure", "openai", "openrouter"
    "model": "gpt-4",
    "max_tokens": 1000,
    "temperature": 0.3,
    
    # Azure 설정
    "azure_api_key": os.getenv("AZURE_OPENAI_KEY"),
    "azure_endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
    "azure_deployment": os.getenv("AZURE_OPENAI_DEPLOYMENT"),
    "azure_api_version": "2024-08-01-preview",
    
    # OpenAI 설정
    "openai_api_key": os.getenv("OPENAI_API_KEY"),
    
    # OpenRouter 설정
    "openrouter_api_key": os.getenv("OPENROUTER_API_KEY"),
    "openrouter_base_url": "https://openrouter.ai/api/v1",
}
```

### .env

```bash
# Azure OpenAI
AZURE_OPENAI_KEY=your_azure_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_DEPLOYMENT=your-deployment-name
AZURE_OPENAI_API_VERSION=2024-08-01-preview

# OpenAI
OPENAI_API_KEY=your_openai_key

# OpenRouter
OPENROUTER_API_KEY=your_openrouter_key
```

## 7. 트러블슈팅

### 문제: "LLM API 키가 설정되지 않았습니다"

**해결:**
1. `.env` 파일에 API 키 설정 확인
2. `config/settings.py`에서 `LLM_CONFIG` 확인
3. 환경변수가 제대로 로드되는지 확인

### 문제: "400 Bad Request"

**해결:**
1. API 버전 확인 (`2024-08-01-preview` 사용)
2. `max_completion_tokens` 사용 (Azure)
3. `temperature` 제거 (Azure)

### 문제: "요약이 생성되지 않습니다"

**해결:**
1. 메시지 내용이 비어있지 않은지 확인
2. LLM API 키가 유효한지 확인
3. 네트워크 연결 확인
4. 로그 확인 (`logs/` 디렉토리)

## 8. 성능 최적화

### 동시 실행 제한

```python
# nlp/summarize.py
CONCURRENCY = 5  # 동시에 5개까지만 요약

sem = asyncio.Semaphore(CONCURRENCY)
async with sem:
    summary = await self.summarize_message(content, sender, subject)
```

### 메시지 길이 제한

```python
# 최대 2000자까지만 LLM에 전송
content_truncated = content[:2000]
```

### 캐싱 (향후 개선)

- 동일한 메시지는 재요약하지 않도록 캐싱
- SQLite에 요약 결과 저장
- `msg_id`를 키로 사용

## 9. 참고 문서

- [TODO_DETAIL_IMPROVEMENTS.md](TODO_DETAIL_IMPROVEMENTS.md) - TODO 상세 다이얼로그 개선사항
- [MESSAGE_SUMMARY_PANEL.md](MESSAGE_SUMMARY_PANEL.md) - 메시지 요약 패널 가이드
- [MESSAGE_GROUPING.md](MESSAGE_GROUPING.md) - 메시지 그룹화 가이드
