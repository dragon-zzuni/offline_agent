# 개발 가이드

Smart Assistant 개발을 위한 상세 가이드입니다.

## 프로젝트 구조

```
smart_assistant/
├── config/                 # 전역 설정
│   ├── settings.py        # 메인 설정 파일
│   ├── settings.db        # 설정 데이터베이스
│   └── settings_rules.json # 규칙 저장소
│
├── data/                  # 데이터 저장소
│   ├── mobile_4week_ko/   # 레거시 데이터셋 (4주)
│   └── multi_project_8week_ko/  # 현재 데이터셋 (8주, 기본값)
│       ├── chat_communications.json
│       ├── email_communications.json
│       ├── team_personas.json
│       ├── final_state.json
│       └── todos_cache.db # TODO 캐시 DB
│
├── nlp/                   # NLP 처리 모듈
│   ├── summarize.py       # 메시지 요약
│   ├── priority_ranker.py # 우선순위 분석
│   ├── action_extractor.py # 액션 추출
│   └── draft.py           # 이메일 초안 생성
│
├── ui/                    # PyQt6 GUI 컴포넌트
│   ├── main_window.py     # 메인 윈도우
│   ├── todo_panel.py      # TODO 관리 패널
│   ├── email_panel.py     # 이메일 패널
│   ├── time_range_selector.py  # 시간 범위 선택기
│   ├── message_summary_panel.py  # 메시지 요약 패널
│   ├── styles.py          # UI 스타일 시스템 ✨ NEW (v1.1.8)
│   ├── settings_dialog.py # 설정 다이얼로그
│   └── offline_cleaner.py # 오프라인 정리 도구
│
├── tools/                 # 유틸리티 스크립트
│   └── import_chat_logs.py # 로그 가져오기
│
├── main.py                # SmartAssistant 코어 엔진
├── run_gui.py             # GUI 진입점
└── requirements.txt       # Python 의존성
```

## 핵심 컴포넌트

### 1. SmartAssistant (main.py)
코어 엔진으로 전체 워크플로우를 관리합니다.

```python
from main import SmartAssistant

assistant = SmartAssistant()
await assistant.initialize(dataset_config)
messages = await assistant.collect_messages(**collect_options)
analysis_results = await assistant.analyze_messages()
todo_list = await assistant.generate_todo_list(analysis_results)
```

### 2. SmartAssistantGUI (ui/main_window.py)
PyQt6 기반 메인 GUI 윈도우입니다.

**주요 메서드:**
- `init_ui()`: UI 초기화
- `create_left_panel()`: 좌측 제어 패널 생성 (스크롤 지원) ✨ v1.2.1+++
- `create_right_panel()`: 우측 결과 패널 생성
- `start_collection()`: 메시지 수집 시작
- `handle_result()`: 분석 결과 처리

**UI 개선사항 (v1.2.1+++):**
- 좌측 패널에 `QScrollArea` 적용으로 스크롤 지원
- 화면 크기가 작아도 모든 컨트롤 접근 가능
- 프레임 스타일 제거로 깔끔한 디자인

### 3. TodoPanel (ui/todo_panel.py)
TODO 관리 패널입니다.

**주요 기능:**
- TODO 목록 표시
- 상태 변경 (완료, 스누즈)
- Top-3 선정 및 표시
- TODO 편집

### 4. TimeRangeSelector (ui/time_range_selector.py)
시간 범위 선택 컴포넌트입니다.

**주요 기능:**
- 시작/종료 시간 선택 (QDateTimeEdit)
- 빠른 선택 버튼 (최근 1시간, 4시간, 오늘, 어제, 최근 7일)
- 시간 범위 유효성 검증
- time_range_changed 시그널 발생

**사용 예시:**
```python
from ui.time_range_selector import TimeRangeSelector

selector = TimeRangeSelector()
selector.time_range_changed.connect(self._on_time_range_changed)

# 시간 범위 가져오기
start, end = selector.get_time_range()

# 시간 범위 설정
selector.set_time_range(start_datetime, end_datetime)

# 기본값으로 리셋 (최근 30일)
selector.reset_to_default()
```

**기본 동작:**
- 초기화 시 자동으로 최근 30일 범위가 설정됩니다
- 대부분의 오프라인 데이터를 포함하여 "메시지 없음" 오류를 방지합니다

### 5. MessageSummaryPanel (ui/message_summary_panel.py)
메시지 요약 패널 컴포넌트입니다.

**주요 기능:**
- 요약 단위 선택 UI (일별/주별/월별 라디오 버튼)
- 그룹화된 요약을 카드 형태로 표시
- 스크롤 가능한 요약 리스트 영역
- summary_unit_changed 시그널 발생

**사용 예시:**
```python
from ui.message_summary_panel import MessageSummaryPanel

panel = MessageSummaryPanel()
panel.summary_unit_changed.connect(self._on_summary_unit_changed)

# 요약 표시
summaries = [
    {
        "period_start": datetime(2025, 10, 15),
        "period_end": datetime(2025, 10, 15, 23, 59, 59),
        "unit": "daily",
        "total_messages": 15,
        "email_count": 8,
        "messenger_count": 7,
        "summary_text": "오늘의 주요 이슈는...",
        "key_points": ["포인트 1", "포인트 2"],
        "priority_distribution": {"high": 5, "medium": 6, "low": 4},
        "top_senders": [("김철수", 5), ("이영희", 3)]
    }
]
panel.display_summaries(summaries)

# 현재 요약 단위 가져오기
unit = panel.get_summary_unit()  # "daily", "weekly", "monthly"
```

### 6. UI 스타일 시스템 (ui/styles.py) ✨ NEW (v1.1.8)
중앙 집중식 스타일 시스템입니다.

**주요 클래스:**
- `Colors`: 색상 팔레트 (Tailwind CSS 기반)
- `FontSizes`: 폰트 크기 (XS ~ XXXL)
- `FontWeights`: 폰트 굵기 (Normal ~ Extrabold)
- `Spacing`: 간격 및 여백 (XS ~ XXL)
- `BorderRadius`: 테두리 반경 (SM ~ FULL)
- `Styles`: 재사용 가능한 스타일 메서드
- `Icons`: 아이콘 및 이모지 정의

**사용 예시:**
```python
from ui.styles import Colors, FontSizes, Styles, Icons

# 색상 사용
button.setStyleSheet(f"""
    QPushButton {{
        background-color: {Colors.PRIMARY};
        color: white;
        font-size: {FontSizes.BASE};
    }}
""")

# 재사용 가능한 스타일
button.setStyleSheet(Styles.button_primary())

# 아이콘 사용
label.setText(f"{Icons.EMAIL} 이메일")

# 우선순위 색상
from ui.styles import get_priority_colors
bg_color, text_color = get_priority_colors("high")
```

**상세 문서:**
- [UI_STYLES.md](UI_STYLES.md): 스타일 시스템 가이드

### 7. WorkerThread (ui/main_window.py)
백그라운드 작업 스레드입니다.

**시그널:**
- `progress_updated(int)`: 진행률 업데이트
- `status_updated(str)`: 상태 메시지 업데이트
- `result_ready(dict)`: 작업 완료
- `error_occurred(str)`: 오류 발생

## 데이터 흐름

```
JSON 데이터셋
    ↓
SmartAssistant.collect_messages()
    ↓
메시지 수집 (이메일 + 메신저)
    ↓
SmartAssistant.analyze_messages()
    ↓
NLP 분석 (요약, 우선순위, 액션 추출)
    ↓
SmartAssistant.generate_todo_list()
    ↓
TODO 생성
    ↓
run_full_cycle() 반환
    ├─ todo_list: TODO 리스트
    ├─ analysis_results: 분석 결과
    ├─ collected_messages: 메시지 수 (int)
    └─ messages: 메시지 원본 데이터 (List[Dict]) ← v1.1.1 추가
    ↓
SQLite 저장 (todos_cache.db)
    ↓
GUI 표시 (TodoPanel, MessageSummaryPanel)
```

## 주요 기능 구현

### 시간 범위 선택

```python
def _on_time_range_changed(self, start: datetime, end: datetime):
    """시간 범위 변경 콜백
    
    시간 범위가 변경되면 이전 분석 결과를 초기화하고
    새로운 범위로 재분석을 준비합니다.
    
    Args:
        start: 시작 시간
        end: 종료 시간
    """
    # 시간 범위를 collect_options에 저장
    self.collect_options["time_range"] = {
        "start": start.isoformat(),
        "end": end.isoformat()
    }
    
    # 이전 결과 초기화
    self.analysis_results = []
    self.collected_messages = []
    
    # 상태 메시지 업데이트
    start_str = start.strftime("%Y-%m-%d %H:%M")
    end_str = end.strftime("%Y-%m-%d %H:%M")
    self.status_message.setText(
        f"시간 범위 설정됨: {start_str} ~ {end_str}\n"
        "'메시지 수집 시작'을 눌러 분석하세요."
    )
```

### 날씨 정보 조회

```python
def fetch_weather(self, preset_location: Optional[str] = None):
    """날씨 정보 조회
    
    1. 기상청 API 시도 (KMA_API_KEY 설정 시)
    2. 실패 시 Open-Meteo API 폴백
    3. UI 업데이트
    """
    # 기상청 API 시도
    if self.kma_api_key:
        if self._fetch_weather_from_kma(location):
            return
    
    # Open-Meteo API 폴백
    # ...
```

### Top-3 TODO 선정

```python
def _score_for_top3(t: Dict) -> float:
    """Top-3 점수 계산
    
    점수 = 우선순위 가중치 × 데드라인 가중치 × 근거 가중치
    """
    w_priority = {"high": 3.0, "medium": 2.0, "low": 1.0}.get(priority, 1.0)
    w_deadline = 1.0 + (24.0 / (24.0 + hours_left))
    w_evidence = 1.0 + min(0.5, 0.1 * len(reasons))
    return w_priority * w_deadline * w_evidence
```

### 주제 기반 메시지 요약 (v1.1.8+)

```python
def _extract_topics_from_messages(self, messages: List[Dict]) -> List[str]:
    """메시지에서 주요 주제 추출
    
    메시지 내용을 분석하여 가장 많이 언급된 주제를 반환합니다.
    
    지원 주제:
    - 미팅, 보고서, 검토, 개발, 버그, 배포, 테스트, 디자인, 일정, 승인
    
    Returns:
        주제 문자열 리스트 (최대 3개)
    """
    topic_keywords = {
        "미팅": ["미팅", "회의", "meeting", "mtg"],
        "보고서": ["보고서", "리포트", "report", "문서"],
        # ... 10개 주제
    }
    
    topic_counts = Counter()
    
    # 최대 20개 메시지만 분석 (성능 최적화)
    for msg in messages[:20]:
        content = (msg.get("content") or msg.get("body") or "").lower()
        subject = (msg.get("subject") or "").lower()
        text = f"{subject} {content}"
        
        for topic, keywords in topic_keywords.items():
            if any(kw in text for kw in keywords):
                topic_counts[topic] += 1
    
    return [topic for topic, count in topic_counts.most_common(3)]

def _generate_brief_summary(self, messages, priority_dist, top_senders):
    """1-2줄 간단 요약 생성
    
    주제 기반의 의미있는 요약을 생성합니다.
    
    예시:
    - "미팅, 보고서 관련 82건 (긴급 5건) 주요 발신자: Kim Jihoon (40건)"
    """
    topics = self._extract_topics_from_messages(messages)
    
    if topics:
        topic_str = ", ".join(topics[:2])
        if high_count > 0:
            line1 = f"{topic_str} 관련 {total}건 (긴급 {high_count}건)"
        # ...
```

### 일일/주간 요약

```python
def show_daily_summary(self):
    """일일 요약 표시
    
    1. 메시지를 날짜별로 파싱
    2. 최근 날짜의 메시지 필터링
    3. 통계 계산 (발신자, 우선순위, 액션)
    4. 팝업 다이얼로그로 표시
    """
    # 날짜 파싱
    parsed = [(dt, msg) for dt, msg in messages if dt]
    target_date = parsed[-1][0].date()
    day_msgs = [msg for dt, msg in parsed if dt.date() == target_date]
    
    # 통계 계산
    # ...
```

## 환경 변수

### LLM 설정
```bash
# OpenAI
OPENAI_API_KEY=your_key
LLM_PROVIDER=openai

# Azure OpenAI
AZURE_OPENAI_KEY=your_key
AZURE_OPENAI_ENDPOINT=your_endpoint
AZURE_OPENAI_DEPLOYMENT=your_deployment
AZURE_OPENAI_API_VERSION=2024-08-01-preview  # API 버전 (권장)
LLM_PROVIDER=azure

# OpenRouter
OPENROUTER_API_KEY=your_key
LLM_PROVIDER=openrouter
```

**Azure OpenAI 사용 시 주의사항:**
- API 버전은 `2024-08-01-preview` 이상을 권장합니다
- TODO 상세 다이얼로그의 LLM 호출은 공급자별로 최적화된 파라미터를 사용합니다:
  - Azure: `max_completion_tokens` 사용, `temperature`는 deployment 설정 사용
  - OpenAI/OpenRouter: `max_tokens`, `temperature` 사용

### 날씨 API 설정
```bash
# 기상청 API (선택사항)
KMA_API_KEY=your_kma_key
KMA_API_URL=https://apihub.kma.go.kr/api/typ02/openapi/VilageFcstInfoService_2.0/getVilageFcst

# 타임아웃 설정
WEATHER_CONNECT_TIMEOUT=5
WEATHER_READ_TIMEOUT=20
WEATHER_MAX_RETRIES=1
```

## 디버깅

### 로깅 시스템

Smart Assistant는 Python의 표준 `logging` 모듈을 사용합니다.

#### 로깅 활성화
```python
import logging

# 기본 설정
logging.basicConfig(
    level=logging.DEBUG,  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # 콘솔 출력
        logging.FileHandler('logs/app.log', encoding='utf-8')  # 파일 저장
    ]
)
```

#### 모듈별 로거 사용
```python
# 각 모듈에서
import logging
logger = logging.getLogger(__name__)

# 로깅 사용
logger.debug("상세 디버깅 정보")
logger.info("일반 정보")
logger.warning("경고 메시지")
logger.error("오류 발생", exc_info=True)  # 스택 트레이스 포함
```

#### 주요 로깅 위치
- `ui/main_window.py`: GUI 이벤트, 사용자 액션, 데이터 로딩
- `main.py`: 메시지 수집 및 분석 파이프라인
- `nlp/` 모듈: NLP 처리 과정

#### 데이터 로딩 로깅 (v1.2.1+++++++++++++++++++++)
데이터셋 시간 범위 자동 감지 시 상세한 로그를 출력합니다:

```python
# ui/main_window.py의 _initialize_data_time_range() 메서드
logger.info(f"📂 데이터셋 경로: {dataset_path.absolute()}")
logger.info(f"채팅 파일 확인: {chat_file.absolute()} (존재: {chat_file.exists()})")
logger.info(f"채팅 방 수: {len(rooms)}")
logger.info(f"채팅에서 수집된 날짜 수: {len(dates)}")
logger.debug(f"채팅 날짜 파싱 오류: {sent_at} - {e}")
logger.warning("⚠️ 데이터셋에서 시간 정보를 찾을 수 없습니다")
logger.error(f"❌ 데이터 시간 범위 초기화 오류: {e}", exc_info=True)
```

**로그 출력 예시:**
```
📂 데이터셋 경로: C:\Projects\smart_assistant\data\multi_project_8week_ko
채팅 파일 확인: C:\...\chat_communications.json (존재: True)
채팅 방 수: 5
채팅에서 수집된 날짜 수: 150
이메일 파일 확인: C:\...\email_communications.json (존재: True)
메일박스 수: 3
이메일에서 수집된 날짜 수: 80
총 수집된 날짜 수: 230
📅 데이터 시간 범위 자동 설정: 2024-10-01 09:00 ~ 2024-11-20 18:30
```

**로깅 베스트 프랙티스:**
1. **이모지 아이콘 사용**: 로그 가독성 향상 (📂, 📅, ⚠️, ❌, ✅)
2. **명확한 메시지**: 무엇을 하는지, 결과가 무엇인지 명시
3. **컨텍스트 포함**: 파일 경로, 개수, 상태 등 구체적 정보
4. **예외 처리**: `exc_info=True`로 스택 트레이스 포함
5. **적절한 레벨**: DEBUG(상세), INFO(일반), WARNING(주의), ERROR(오류)

#### 로그 레벨 변경
```bash
# 환경 변수로 설정
export LOG_LEVEL=DEBUG  # Linux/Mac
set LOG_LEVEL=DEBUG     # Windows

# 또는 코드에서 직접 설정
logging.getLogger().setLevel(logging.DEBUG)
```

### LLM 호출 디버깅 (v1.1.9)

TODO 상세 다이얼로그의 LLM 호출은 상세한 로그를 출력합니다:

```python
# ui/todo_panel.py의 _call_llm() 메서드
logger.info(f"[TodoDetail][LLM] provider={provider} URL={url[:80]}... 요약/회신 생성 중...")
logger.debug(f"[TodoDetail][LLM] payload={json.dumps(payload, ensure_ascii=False)[:300]}")
logger.info(f"[TodoDetail][LLM] 응답 수신 (status={response.status_code})")
logger.debug(f"[TodoDetail][LLM] 응답 JSON: {json.dumps(resp_json, ensure_ascii=False)[:500]}")
logger.info(f"[TodoDetail][LLM] 생성 완료 (길이: {len(content)}자)")
```

**로그 출력 예시:**
```
[TodoDetail][LLM] provider=azure URL=https://krcentral.cognitiveservices.azure.com/... 요약/회신 생성 중...
[TodoDetail][LLM] 응답 수신 (status=200)
[TodoDetail][LLM] 생성 완료 (길이: 245자)
```

**에러 로그 예시:**
```
[TodoDetail][LLM] 타임아웃 (60초 초과)
[TodoDetail][LLM] HTTP 오류: 400 - {"error": {"code": "InvalidRequest", ...}}
[TodoDetail][LLM] JSON 파싱 실패: Expecting value: line 1 column 1 (char 0)
[TodoDetail][LLM] choices가 비어있음
[TodoDetail][LLM] content가 비어있음
```

### PyQt6 디버깅
```python
# 환경 변수 설정
os.environ['QT_DEBUG_PLUGINS'] = '1'
```

### SQLite 데이터베이스 확인
```bash
sqlite3 data/multi_project_8week_ko/todos_cache.db
.tables
SELECT * FROM todos;
```

### 로그 파일 위치
- 콘솔 출력: 실시간 로그 확인
- 파일 저장: `logs/app.log` (향후 구현 예정)
- 로그 로테이션: 일별/크기별 로그 파일 분할 (향후 구현 예정)

## 성능 최적화

### 메시지 수집 제한
```python
collect_options = {
    "email_limit": 50,      # 이메일 최대 50개
    "messenger_limit": 100, # 메신저 최대 100개
    "overall_limit": 150,   # 전체 최대 150개
}
```

### 캐싱 활용
```python
# force_reload=False로 캐시 사용
dataset_config = {
    "dataset_root": str(DEFAULT_DATASET_ROOT),
    "force_reload": False,  # 캐시 사용
}
```

## 테스트

### 단위 테스트 작성
```python
import pytest
from ui.main_window import _score_for_top3

def test_score_calculation():
    todo = {
        "priority": "high",
        "deadline_ts": "2024-10-18T12:00:00Z",
        "evidence": ["reason1", "reason2"]
    }
    score = _score_for_top3(todo)
    assert score > 3.0  # High priority base score
```

### GUI 테스트
```python
from PyQt6.QtTest import QTest
from PyQt6.QtCore import Qt

def test_button_click(qtbot):
    window = SmartAssistantGUI()
    qtbot.addWidget(window)
    
    # 버튼 클릭 시뮬레이션
    QTest.mouseClick(window.start_button, Qt.MouseButton.LeftButton)
    
    # 상태 확인
    assert window.worker_thread is not None
```

## 배포

### 실행 파일 생성 (PyInstaller)
```bash
pyinstaller --onefile --windowed run_gui.py
```

### 의존성 업데이트
```bash
pip freeze > requirements.txt
```

## 문제 해결

### 한글 출력 문제
Windows에서 한글이 깨지는 경우:
```python
# main_window.py에 이미 포함됨
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
```

### PyQt6 폰트 문제
```python
# 전역 폰트 설정
app = QApplication(sys.argv)
base_font = QFont("Malgun Gothic", 10)
app.setFont(base_font)
```

### 날씨 API 타임아웃
```bash
# .env 파일에서 타임아웃 증가
WEATHER_CONNECT_TIMEOUT=10
WEATHER_READ_TIMEOUT=30
```

## 참고 자료

- [PyQt6 공식 문서](https://www.riverbankcomputing.com/static/Docs/PyQt6/)
- [SQLite 문서](https://www.sqlite.org/docs.html)
- [기상청 API 가이드](https://apihub.kma.go.kr/)
- [Open-Meteo API](https://open-meteo.com/)
- [LLM API 사용 가이드](LLM_API_GUIDE.md)
- [Azure OpenAI 공식 문서](https://learn.microsoft.com/azure/ai-services/openai/)
