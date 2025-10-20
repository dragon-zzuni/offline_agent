# Smart Assistant

오프라인 데이터셋(`data/multi_project_8week_ko`)을 기반으로 멀티 프로젝트 팀의 이메일·메신저 대화를 분석하고, PM 시점의 TODO를 자동 생성하는 데스크톱 도우미입니다. 네트워크가 없는 환경에서도 최신 데이터를 수동으로 불러오고, 온라인으로 전환되면 한 번 자동으로 전체 분석을 수행합니다.

> **최신 버전**: v1.2.1+++++++++++++++++++ (2025-10-20)  
> **주요 개선**: 데이터 로딩 로깅 강화, UI 스타일 일관성 개선, 코드 품질 향상

## 🚀 주요 기능

### 최신 업데이트 (v1.2.1+++++++++++++++++++)
- **📊 데이터 로딩 로깅 강화**: 데이터셋 시간 범위 자동 감지 시 상세한 로그 출력 ✨ NEW
  - 데이터셋 경로 절대 경로 표시
  - 파일 존재 여부 명시적 확인
  - 채팅 방 수 및 메일박스 수 로깅
  - 각 소스별 수집된 날짜 수 표시
  - 총 수집된 날짜 수 및 최종 시간 범위 로깅
  - 예외 발생 시 스택 트레이스 포함 (`exc_info=True`)
  - 이모지 아이콘으로 로그 가독성 향상 (📂, 📅, ⚠️, ❌)

- **🎨 UI 스타일 일관성 개선**: MessageDetailDialog 헤더 색상 상수 표준화
  - `Colors.SURFACE` → `Colors.BG_SECONDARY`로 변경
  - `Colors.BORDER` → `Colors.BORDER_LIGHT`로 변경
  - 중앙 집중식 스타일 시스템(`ui/styles.py`)의 표준 색상 상수 사용
  - 다른 UI 컴포넌트와 일관된 색상 팔레트 적용

- **🔧 코드 품질 개선**: 주제 추출 및 요약 생성 로직 리팩토링
  - `Counter` 사용으로 성능 최적화
  - 헬퍼 함수 분리로 코드 재사용성 향상
  - 상세한 docstring 및 예시 코드 추가
  - 타입 힌트 정리 및 일관성 개선
  - **메시지 ID 필드 우선순위 개선**: `msg_id`를 주요 필드로 우선 확인하여 데이터 일관성 향상
- **📊 개선된 분석 결과 패널**: 좌우 분할 레이아웃으로 요약과 상세 분석을 동시에 표시 (v1.2.1++++) ✨ NEW
  - 좌측: 전체 통계, 우선순위 분포, 주요 발신자 요약
  - 우측: 우선순위별 메시지 카드 (High/Medium/Low 섹션)
  - QSplitter로 비율 조절 가능 (기본 30:70)
  - 카드 형태의 직관적인 메시지 표시
  - 수신 시간 정보 표시 (🕐 수신: YYYY-MM-DD HH:MM)
  - 호버 효과로 시각적 피드백 제공
  - 일관된 UI 스타일 시스템 적용 (Colors.BG_SECONDARY, Colors.BORDER_LIGHT)
- **📧 수신 타입 구분 표시**: TODO 리스트에서 참조(CC)/직접 수신(TO) 구분 (v1.2.1+)
  - TODO 카드에 수신 타입 배지 표시 (참조(CC), 숨은참조(BCC))
  - TODO 상세 다이얼로그에 수신 타입 정보 표시
  - 데이터베이스에 `recipient_type` 컬럼 추가 (자동 마이그레이션)
  - 헬퍼 함수로 코드 중복 제거 및 일관성 개선
- **⚖️ CC 메일 가중치 조정**: TOP3 우선순위 계산 시 참조 메일 가중치 낮춤 (v1.2.1+)
  - 참조(CC) 수신 메일: 가중치 30% 감소 (0.7 배수)
  - 숨은참조(BCC) 수신 메일: 가중치 37% 감소 (0.63 배수)
  - 직접 수신한 중요 메일이 TOP3에 우선 표시됨
- **📊 개선된 메시지 그룹화**: GroupedSummary 데이터 모델 사용으로 일관성 향상 (v1.2.1++)
  - `GroupedSummary.from_messages()` 팩토리 메서드 사용
  - 자동 통계 계산 (우선순위 분포, 주요 발신자)
  - 기간 시작/종료 자동 계산
  - 코드 중복 제거 및 유지보수성 향상
- **🎨 일관된 UI 디자인 시스템**: Tailwind CSS 기반의 색상 팔레트와 재사용 가능한 스타일 컴포넌트로 통일된 사용자 경험을 제공합니다 (v1.1.8)
- **🎯 주제 기반 메시지 요약**: 메시지 내용을 분석하여 주요 주제를 자동으로 추출하고 간결한 요약을 생성합니다 (v1.1.8+)
  - 10개 주제 카테고리 지원 (미팅, 보고서, 검토, 개발, 버그, 배포, 테스트, 디자인, 일정, 승인)
  - 한글 + 영어 키워드 동시 지원
  - 예시: "미팅, 보고서 관련 82건 (긴급 5건) 주요 발신자: Kim Jihoon (40건)"
- **🔍 강화된 LLM 디버깅**: TODO 상세 다이얼로그의 LLM 호출에 상세한 로깅 및 에러 처리 추가 (v1.1.9)
  - 타임아웃 60초로 확대
  - HTTP 오류, JSON 파싱 오류 구분
  - 상세한 로그로 문제 추적 용이
- **💾 TODO 영구 저장**: 앱 재시작 시에도 TODO가 유지됩니다 (v1.1.9+)
  - 14일 이상 된 오래된 TODO만 자동 정리
  - 사용자가 원하면 수동으로 "모두 삭제" 버튼 사용 가능
  - 탭 전환 시에도 TODO 유지
- **📚 오프라인 메시지 로딩**: `chat_communications.json` / `email_communications.json` / `team_personas.json`을 읽어 최신 대화와 인물 정보를 통합합니다.
- **👤 PM 수신 메시지 필터링**: PM이 수신한 메시지만 자동으로 필터링하여 빠른 TODO 생성 (v1.1.6)
  - 이메일: to, cc, bcc에 PM이 포함된 메시지만 수집
  - 메신저: PM이 참여한 DM 룸의 메시지만 수집
  - 불필요한 메시지 제외로 성능 대폭 향상
- **📧 스마트 이메일 필터링**: TODO 가치가 있는 이메일만 자동 필터링 (v1.1.7)
  - 키워드 기반 휴리스틱 필터링 (요청, 회의, 마감일 등)
  - 카드 형태의 직관적인 이메일 미리보기
  - 불필요한 이메일 제외로 집중력 향상
- **🤖 LLM 기반 분석 파이프라인**: 메시지 요약, 우선순위 산정, 액션 추출까지 한 번에 수행합니다.
- **📋 TODO 보드**: 추출된 업무를 우선순위/근거/드래프트와 함께 저장하고, PyQt6 UI에서 즉시 확인·편집·완료 처리할 수 있습니다.
  - **✅ 스마트 메시지 필터링**: PM에게 **수신된** 메시지만 TODO로 변환 (v1.1.6)
    - 이메일: `to`, `cc`, `bcc` 필드에서 PM 이메일 확인
    - 메신저: DM 룸의 참여자 목록에서 PM 핸들 확인
    - PM이 **보낸** 메시지는 자동으로 제외하여 업무 관리 정확도 향상
  - **📧 수신 타입 표시**: TODO 카드에 참조(CC)/숨은참조(BCC) 배지 표시 (v1.2.1)
    - 직접 수신(TO): 배지 없음 (기본)
    - 참조(CC): 노란색 배지로 표시
    - 숨은참조(BCC): 노란색 배지로 표시
    - TOP3 계산 시 CC/BCC 메일은 가중치 감소
  - **✅ 간결한 TODO 제목**: "미팅참석", "업무처리", "문서검토" 등 한 단어로 표시하여 가독성 향상
  - **💾 TODO 영구 저장**: 앱 재시작 시에도 TODO가 유지됩니다 (v1.1.9+)
    - 14일 이상 된 오래된 TODO만 자동 정리
    - 사용자가 원하면 수동으로 "모두 삭제" 버튼 사용 가능
  - **상세 다이얼로그 개선**: 상하 분할 레이아웃으로 원본 메시지와 요약을 명확히 구분 (v1.1.5)
  - **LLM 기반 요약/회신**: 버튼 클릭으로 즉시 요약 생성 및 회신 초안 작성 (v1.1.5+)
    - **Azure OpenAI, OpenAI, OpenRouter 지원**
    - **Azure OpenAI API 최적화**: `max_completion_tokens` 파라미터 사용으로 안정성 향상 (v1.1.8+)
    - 실시간 LLM API 호출로 3-5개 불릿 포인트 요약 생성
    - 정중하고 명확한 회신 초안 자동 작성
  - **간결한 요약 표시**: TODO 리스트에서 긴 설명을 80자 이내로 요약하여 표시 (v1.1.5)
  - **상세 다이얼로그**: TODO 클릭 시 원본 메시지와 요약/액션을 상하 분할 레이아웃으로 표시 (v1.1.5)
- **🔁 온라인 모드 감지**: 오프라인에서 작업하다가 온라인으로 전환되면 자동으로 한 차례 데이터를 재분석합니다. 온라인 상태에서도 필요 시 수동으로 재실행할 수 있습니다.
- **🌤️ 날씨 정보**: 기상청 API 및 Open-Meteo API를 통해 오늘/내일 날씨와 업무 팁을 제공합니다.
- **📊 메시지 그룹화 및 요약**: 메시지를 일/주/월 단위로 그룹화하고 각 그룹별 통합 요약을 생성합니다 (v1.1, v1.2.1++++++++++++ 개선).
  - **정확한 주간 날짜 표시**: 주간 요약에서 실제 마지막 날짜를 정확히 표시 ✨ NEW (v1.2.1++++++++++++)
    - 이전: 다음 주 월요일 직전 시간 표시 (예: "10/14 ~ 10/21 00:00")
    - 현재: 실제 주의 마지막 날짜 표시 (예: "10/14 ~ 10/20")
    - 자동으로 하루를 빼서 정확한 종료일 계산
  - **일별**: "2025년 10월 20일 (월)" 형식
  - **주별**: "2025년 10/14 ~ 10/20" 형식 (동일 연도) 또는 "2025년 10/14 ~ 2026년 01/03" 형식 (연도 다름)
  - **월별**: "2025년 10월" 형식
  - 예외 처리 강화로 파싱 실패 시에도 안정적 동작
- **⚡ Top-3 즉시 처리**: 우선순위와 데드라인을 기반으로 가장 중요한 3개 TODO를 자동으로 선정하여 표시합니다.
- **⏰ 시간 범위 선택**: 특정 오프라인 기간의 메시지만 선택하여 분석할 수 있습니다 (최근 1시간, 4시간, 오늘, 어제, 최근 7일, 전체 기간).
  - **스마트 경고**: 선택한 시간 범위에 메시지가 없을 경우 자동으로 경고하여 사용자가 범위를 조정할 수 있도록 안내합니다
  - **전체 기간 버튼**: 1년 전부터 현재까지 모든 메시지를 포함하는 범위를 한 번에 설정 (v1.1.5)
  - **개선된 기본값**: 최근 30일로 설정하여 대부분의 데이터를 자동으로 포함 (v1.1.5)
- **📨 메시지 요약 패널**: 일/주/월 단위로 메시지를 그룹화하여 카드 형태로 요약을 표시합니다 (v1.1, v1.2.1+++++++++++ 개선).
  - **발신자별 우선순위 표시**: 각 발신자의 최고 우선순위를 해시태그로 표시 (#High, #Medium)
  - **간결한 요약**: 1-2줄로 핵심 내용을 빠르게 파악
  - **깔끔한 날짜 표시**: 디버그 로그 제거로 안정적인 날짜 형식 표시 ✨ NEW (v1.2.1++++++++++)
  - **주요 포인트 자동 추출**: 최대 3개의 핵심 포인트를 자동 추출 (v1.1.9+)
    - 분석 결과가 있으면 요약에서 추출
    - 분석 결과가 없으면 메시지 내용에서 직접 추출
    - 제목 우선, 없으면 본문 첫 문장 사용
    - 발신자 정보 포함 (예: "Kim Jihoon: 오늘 오전 2일차 작업 진행 상황 점검...")
- **🔄 메시지 데이터 접근**: GUI에서 수집된 메시지 원본 데이터에 직접 접근 가능 (v1.1.1)
- **📝 로깅 시스템**: 애플리케이션 동작을 추적하고 디버깅을 지원하는 로깅 기능 (v1.1.2)

## 📁 프로젝트 구조
```
smart_assistant/
├── config/                 # 전역 설정 (경로, LLM, UI 등)
├── data/
│   ├── mobile_4week_ko/    # 레거시 데이터셋 (4주 데이터)
│   └── multi_project_8week_ko/  # 현재 데이터셋 (8주 데이터, 기본값)
├── docs/                   # 문서
│   ├── UI_STYLES.md        # UI 스타일 시스템 가이드 ✨ (v1.1.8)
│   ├── EMAIL_PANEL.md      # 이메일 패널 가이드
│   ├── MESSAGE_SUMMARY_PANEL.md  # 메시지 요약 패널 가이드
│   ├── TIME_RANGE_SELECTOR.md    # 시간 범위 선택기 가이드
│   ├── MESSAGE_GROUPING.md # 메시지 그룹화 가이드
│   └── DEVELOPMENT.md      # 개발 가이드
├── logs/                   # 실행 로그
├── nlp/                    # 요약, 우선순위, 액션 추출 모듈
│   ├── summarize.py        # 메시지 요약 (그룹 요약 포함)
│   ├── message_grouping.py # 메시지 그룹화 유틸리티
│   ├── grouped_summary.py  # 그룹 요약 데이터 모델 ✨ (v1.2.1++)
│   ├── priority_ranker.py  # 우선순위 분석
│   └── action_extractor.py # 액션 추출
├── tools/                  # 보조 스크립트
├── ui/                     # PyQt6 기반 GUI 컴포넌트
│   ├── main_window.py      # 메인 윈도우 (TimeRangeSelector, MessageSummaryPanel 통합)
│   ├── todo_panel.py       # TODO 관리 패널 (수신 타입 배지 표시)
│   ├── email_panel.py      # 이메일 패널 (v1.1.7)
│   ├── analysis_result_panel.py  # 분석 결과 패널 (v1.2.1++++) ✨ NEW
│   ├── time_range_selector.py  # 시간 범위 선택 컴포넌트 (v1.1+)
│   ├── message_summary_panel.py  # 메시지 요약 패널 (v1.1+, v1.2.1++ 개선)
│   ├── styles.py           # UI 스타일 시스템 (v1.1.8+)
│   ├── settings_dialog.py  # 설정 다이얼로그
│   └── offline_cleaner.py  # 오프라인 정리 도구
├── utils/                  # 유틸리티 모듈
│   ├── datetime_utils.py   # 날짜/시간 유틸리티
│   └── __init__.py         # 유틸리티 모듈 초기화
├── main.py                 # SmartAssistant 코어 엔진
├── run_gui.py              # GUI 실행 스크립트
└── requirements.txt        # 의존성 목록
```

## 🛠️ 설치

### 필수 요구사항
- Python 3.7 이상
- Windows 10/11 (한글 출력 최적화)

### 설치 방법
```bash
# 의존성 설치
pip install -r requirements.txt

# Node.js 의존성 (선택사항)
npm install
```

### 로깅 설정
애플리케이션은 Python의 표준 `logging` 모듈을 사용하여 상세한 실행 로그를 제공합니다.

**로그 레벨:**
- `DEBUG`: 상세한 디버깅 정보 (날짜 파싱, 파일 읽기, 데이터 구조 등)
- `INFO`: 일반 정보 메시지 (데이터 로딩, 분석 진행, 통계 등)
- `WARNING`: 경고 메시지 (데이터 누락, 파싱 실패 등)
- `ERROR`: 오류 메시지 (예외 발생, 시스템 오류 등)

**로그 레벨 변경:**
```bash
# 환경 변수로 설정
export LOG_LEVEL=DEBUG  # Linux/Mac
set LOG_LEVEL=DEBUG     # Windows

# 또는 코드에서 직접 설정
import logging
logging.getLogger().setLevel(logging.DEBUG)
```

**데이터 로딩 로깅 (v1.2.1+++++++++++++++++++) ✨ NEW**

데이터셋 시간 범위 자동 감지 시 상세한 로그를 출력합니다:

```python
# 로그 예시
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

**오류 발생 시:**
```
📂 데이터셋 경로: C:\Projects\smart_assistant\data\multi_project_8week_ko
채팅 파일 확인: C:\...\chat_communications.json (존재: False)
⚠️ 데이터셋에서 시간 정보를 찾을 수 없습니다
```

**예외 발생 시:**
```
❌ 데이터 시간 범위 초기화 오류: [Errno 2] No such file or directory: '...'
Traceback (most recent call last):
  File "ui/main_window.py", line 1570, in _initialize_data_time_range
    with open(chat_file, 'r', encoding='utf-8') as f:
FileNotFoundError: [Errno 2] No such file or directory: '...'
```

### 환경 변수 설정
`.env` 파일을 생성하여 다음 설정을 추가하세요:

```bash
# LLM 설정 (택일)
OPENAI_API_KEY=your_key
AZURE_OPENAI_KEY=your_key
AZURE_OPENAI_ENDPOINT=your_endpoint
AZURE_OPENAI_DEPLOYMENT=your_deployment
AZURE_OPENAI_API_VERSION=2024-08-01-preview  # Azure API 버전 (권장)
OPENROUTER_API_KEY=your_key

# 공급자 선택
LLM_PROVIDER=azure  # openai | azure | openrouter

# 날씨 API (선택사항)
KMA_API_KEY=your_kma_key  # 기상청 API 키
WEATHER_CONNECT_TIMEOUT=5  # 연결 타임아웃 (초)
WEATHER_READ_TIMEOUT=20    # 읽기 타임아웃 (초)
WEATHER_MAX_RETRIES=1      # 재시도 횟수
```

**Azure OpenAI 사용 시 주의사항:**
- API 버전은 `2024-08-01-preview` 이상을 권장합니다
- `max_completion_tokens` 파라미터를 사용하여 토큰 제한을 설정합니다
- `temperature` 파라미터는 Azure에서 기본값을 사용합니다
- TODO 상세 다이얼로그의 LLM 호출 타임아웃은 60초입니다 (v1.1.9)

데이터셋은 `data/mobile_4week_ko`에 포함되어 있으며, 추가 설정 없이 바로 사용할 수 있습니다. LLM API 키를 설정하면 고급 요약/추출 기능을, 설정하지 않으면 기본 휴리스틱 기반 파이프라인을 사용합니다.

## ⚙️ 사용 방법

### GUI 실행
```bash
# Python으로 직접 실행
python run_gui.py

# Windows 배치 파일 실행
run_gui.bat
```

### 주요 기능 사용법

#### 1. 메시지 수집 및 분석
- 좌측 패널에서 현재 데이터셋 경로와 상태를 확인합니다.
- **시간 범위 선택** (선택사항):
  - 시작/종료 시간을 직접 입력하거나 빠른 선택 버튼을 사용합니다.
  - 예: "최근 4시간" 버튼을 클릭하면 현재 시간 기준 4시간 전부터의 메시지만 분석합니다.
  - `적용` 버튼을 클릭하여 시간 범위를 확정합니다.
  - 시간 범위를 설정하면 해당 기간의 메시지만 필터링되어 분석됩니다.
- `메시지 수집 시작` 버튼을 클릭하여 분석을 실행합니다.
- 온라인 상태로 전환하면 자동으로 한 번 분석이 트리거됩니다.

#### 2. TODO 관리
- **TODO 리스트 탭**: 생성된 TODO를 우선순위별로 확인하고 편집할 수 있습니다.
- **수신 타입 표시**: 각 TODO 카드에 수신 타입이 배지로 표시됩니다 (v1.2.1)
  - 직접 수신(TO): 배지 없음 (기본)
  - 참조(CC): 노란색 "참조(CC)" 배지
  - 숨은참조(BCC): 노란색 "숨은참조(BCC)" 배지
- **Top-3 즉시 처리**: 가장 중요한 3개 TODO가 좌측 패널에 자동으로 표시됩니다.
  - CC/BCC 메일은 가중치가 낮아져 직접 수신 메일이 우선 표시됩니다
- **상태 관리**: TODO를 완료 처리하거나 스누즈할 수 있습니다.

#### 3. 날씨 정보
- 좌측 패널의 날씨 섹션에서 도시명을 입력하고 `날씨 업데이트` 버튼을 클릭합니다.
- 오늘과 내일의 날씨 정보 및 업무 팁이 표시됩니다.
- 기상청 API 키가 설정되어 있으면 한국 도시의 상세 정보를 제공합니다.

#### 4. 메시지 그룹화 및 요약 (v1.1, v1.2.1++++++++++++ 개선)
- **메시지 요약 패널**: 메시지 탭에서 요약 단위를 선택하고 그룹화된 요약을 카드 형태로 표시합니다.
- **일일 요약**: 메시지를 날짜별로 그룹화하여 각 날짜의 요약을 생성합니다.
  - 날짜 형식: "2025년 10월 20일 (월)"
- **주간 요약**: 메시지를 주별로 그룹화하여 각 주의 요약을 생성합니다 (월요일 시작).
  - 날짜 형식: "2025년 10/14 ~ 10/20" (동일 연도) 또는 "2025년 10/14 ~ 2026년 01/03" (연도 다름)
  - **정확한 종료일 표시**: 실제 주의 마지막 날짜를 정확히 표시 ✨ NEW (v1.2.1++++++++++++)
    - 이전: 다음 주 월요일 직전 시간 표시 (예: "10/14 ~ 10/21 00:00")
    - 현재: 실제 주의 마지막 날짜 표시 (예: "10/14 ~ 10/20")
- **월간 요약**: 메시지를 월별로 그룹화하여 각 월의 요약을 생성합니다.
  - 날짜 형식: "2025년 10월"
- **안정적인 날짜 처리**: 예외 처리 강화로 파싱 실패 시에도 안정적 동작
- 각 그룹별로 다음 정보를 제공합니다:
  - 총 메시지 수 (이메일/메신저 구분)
  - 우선순위 분포 (High/Medium/Low)
  - **주요 발신자 배지**: 발신자별 메시지 수와 최고 우선순위를 색상 코딩된 배지로 표시 ✨ (v1.2.1+++++++++)
    - High 우선순위: 빨간색 배지 (#High)
    - Medium 우선순위: 노란색 배지 (#Medium)
    - Low 우선순위: 회색 배지 (태그 없음)
    - **발신자별 우선순위 맵**: 각 발신자의 최고 우선순위를 자동 계산하여 표시
  - **간결한 요약**: 1-2줄로 핵심 내용을 빠르게 파악
  - **주요 포인트**: 최대 3개의 핵심 포인트를 자동 추출
- 그룹별 요약으로 대량 메시지 처리 시간을 단축합니다.
- **요약 단위 선택**: 라디오 버튼으로 일별/주별/월별 요약을 쉽게 전환할 수 있습니다.

#### 5. 스마트 이메일 필터링 (v1.1.7 신규 기능)
- **EmailPanel 컴포넌트**: TODO 가치가 있는 이메일만 자동 필터링하여 표시
- **키워드 기반 필터링**: 다음 키워드가 포함된 이메일만 표시
  - 요청/질문: "요청", "request", "부탁", "확인", "질문", "문의"
  - 회의/일정: "회의", "meeting", "미팅", "일정", "schedule"
  - 긴급/마감: "마감", "deadline", "긴급", "urgent", "asap"
  - 승인/결재: "승인", "approval", "결재", "검토", "review"
- **카드 형태 UI**: 제목, 발신자, 내용 미리보기를 한눈에 확인
- **실시간 카운트**: 필터링된 이메일 수를 실시간으로 표시
- **호버 효과**: 마우스 오버 시 시각적 피드백 제공

#### 6. 시간 범위 선택 (v1.1 신규 기능, v1.2.1+++++++++++++++++++ 개선)
- **시간 범위 선택기**를 사용하여 특정 오프라인 기간의 메시지만 분석할 수 있습니다.
- **자동 범위 감지**: 데이터셋의 실제 메시지 시간 범위를 자동으로 감지하여 설정 ✨ NEW
  - 채팅 및 이메일 파일을 스캔하여 가장 오래된/최근 메시지 시간 자동 설정
  - 상세한 로깅으로 데이터 로딩 과정 추적 가능
  - 파일 존재 여부, 방/메일박스 수, 수집된 날짜 수 등을 로그로 확인
- **기본 범위**: 데이터셋의 전체 기간 (자동 감지) 또는 최근 30일
- **빠른 선택 버튼**:
  - `최근 1시간`: 데이터의 최근 시간 기준 1시간 전부터
  - `최근 4시간`: 데이터의 최근 시간 기준 4시간 전부터
  - `오늘`: 오늘 00:00부터 현재까지의 메시지
  - `어제`: 어제 00:00부터 23:59까지의 메시지
  - `최근 7일`: 데이터의 최근 시간 기준 7일 전부터
  - `전체 기간`: 데이터셋의 모든 메시지 포함 (자동 감지된 범위)
- **사용자 정의 범위**: 시작/종료 시간을 직접 입력하여 원하는 기간을 설정할 수 있습니다.
- 시간 범위를 변경하면 이전 분석 결과가 초기화되고 새로운 범위로 재분석이 준비됩니다.

**로그 예시:**
```
📂 데이터셋 경로: C:\...\data\multi_project_8week_ko
채팅 파일 확인: C:\...\chat_communications.json (존재: True)
채팅 방 수: 5
채팅에서 수집된 날짜 수: 150
이메일 파일 확인: C:\...\email_communications.json (존재: True)
메일박스 수: 3
이메일에서 수집된 날짜 수: 80
총 수집된 날짜 수: 230
📅 데이터 시간 범위 자동 설정: 2024-10-01 09:00 ~ 2024-11-20 18:30
```

#### 7. 오프라인 정리
- `오프라인 정리` 버튼을 클릭하여 오프라인 기간 동안의 데이터를 정리할 수 있습니다.

### 코드에서 사용

#### AnalysisResultPanel 사용법 ✨ NEW (v1.2.1++++)
```python
from ui.analysis_result_panel import AnalysisResultPanel

# AnalysisResultPanel 생성
panel = AnalysisResultPanel()

# 분석 결과 업데이트
analysis_results = [
    {
        "message": {
            "msg_id": "msg_001",
            "sender": "김철수",
            "subject": "프로젝트 검토 요청",
            "type": "email"
        },
        "priority": {
            "priority_level": "high"
        },
        "summary": {
            "summary": "프로젝트 문서 검토가 필요합니다."
        },
        "actions": [
            {"title": "문서 검토", "priority": "High"}
        ]
    }
]

messages = [
    {
        "msg_id": "msg_001",
        "sender": "김철수",
        "subject": "프로젝트 검토 요청",
        "type": "email"
    }
]

# 분석 결과 표시
panel.update_analysis(analysis_results, messages)
```

**주요 기능:**
- **좌측 요약 영역**: 전체 통계, 우선순위 분포, 주요 발신자 TOP5
- **우측 상세 영역**: 우선순위별 메시지 카드 (High/Medium/Low 섹션)
- **자동 그룹화**: 우선순위별로 메시지를 자동 분류
- **카드 형태 표시**: 발신자, 제목, 요약, 액션 수를 카드로 표시
- **호버 효과**: 마우스 오버 시 시각적 피드백
- **비율 조절**: QSplitter로 좌우 비율 조절 가능 (기본 30:70)

#### EmailPanel 사용법
```python
from ui.email_panel import EmailPanel

# EmailPanel 생성
email_panel = EmailPanel()

# 이메일 목록 업데이트 (자동 필터링됨)
emails = [
    {
        "subject": "프로젝트 검토 요청",
        "sender": "김철수",
        "body": "첨부된 문서를 검토해 주세요.",
        "timestamp": "2025-10-17 14:30"
    }
]
email_panel.update_emails(emails)

# 필터링된 이메일 수 확인
print(f"필터링된 이메일: {len(email_panel.emails)}건")

# 초기화
email_panel.clear()
```

**필터링 키워드:**
- 요청: "요청", "request", "부탁", "확인", "check"
- 검토: "검토", "review", "승인", "approval", "결재"
- 회의: "회의", "meeting", "미팅", "일정", "schedule"
- 긴급: "마감", "deadline", "긴급", "urgent", "asap"
- 문의: "질문", "question", "문의", "inquiry"

#### 기본 사용법
```python
import asyncio
from main import SmartAssistant, DEFAULT_DATASET_ROOT

async def main():
    assistant = SmartAssistant()

    dataset_config = {
        "dataset_root": str(DEFAULT_DATASET_ROOT),
        "force_reload": True,
    }
    collect_options = {
        "messenger_limit": 40,
        "email_limit": 40,
        "force_reload": True,
    }

    result = await assistant.run_full_cycle(dataset_config, collect_options)

    if result.get("success"):
        todo_list = result["todo_list"]
        messages = result["messages"]  # 수집된 메시지 원본 데이터
        
        print(f"수집된 메시지: {len(messages)}개")
        print(f"생성된 TODO 수: {todo_list['summary']['total']}개")
        
        # PM 수신 메시지만 필터링되어 TODO로 변환됨
        for item in todo_list["items"][:5]:
            print(f"- [{item['priority']}] {item['title']}")
            print(f"  요청자: {item['requester']}")
    else:
        print("오류:", result.get("error"))

asyncio.run(main())
```

**주요 특징:**
- PM에게 **수신된** 메시지만 자동으로 필터링됩니다
- 이메일의 경우 `to`, `cc`, `bcc` 필드를 확인합니다
- 메신저의 경우 DM 룸의 참여자 목록을 확인합니다
- PM이 보낸 메시지는 TODO로 변환되지 않습니다

#### 시간 범위 필터링 사용법
```python
from datetime import datetime, timedelta, timezone

# 방법 1: UTC aware datetime 사용 (권장)
now = datetime.now(timezone.utc)
start = now - timedelta(hours=4)

collect_options = {
    "time_range": {
        "start": start,  # UTC aware datetime
        "end": now
    },
    "force_reload": True,
}

# 방법 2: naive datetime 사용 (자동으로 UTC로 변환됨)
now_naive = datetime.now()
start_naive = now_naive - timedelta(hours=4)

collect_options = {
    "time_range": {
        "start": start_naive,  # naive datetime → 자동으로 UTC로 변환
        "end": now_naive
    },
    "force_reload": True,
}

# 메시지 수집 (시간 범위 필터링 적용)
messages = await assistant.collect_messages(**collect_options)
print(f"필터링된 메시지 수: {len(messages)}개")
```

#### TimeRangeSelector UI 컴포넌트 사용법
```python
from ui.time_range_selector import TimeRangeSelector

# TimeRangeSelector 컴포넌트 생성
selector = TimeRangeSelector()

# 시간 범위 변경 시그널 연결
selector.time_range_changed.connect(on_time_range_changed)

# 현재 시간 범위 가져오기
start, end = selector.get_time_range()
print(f"선택된 범위: {start} ~ {end}")

# 프로그래밍 방식으로 시간 범위 설정
now = datetime.now()
start = now - timedelta(hours=4)
selector.set_time_range(start, now)

# 기본값(최근 24시간)으로 리셋
selector.reset_to_default()
```

#### 메시지 그룹화 및 요약 사용법
```python
from nlp.message_grouping import group_by_day, group_by_week, group_by_month, get_group_date_range
from nlp.grouped_summary import GroupedSummary
from nlp.summarize import MessageSummarizer
from ui.message_summary_panel import MessageSummaryPanel

# 1. 메시지 그룹화
daily_groups = group_by_day(messages)    # 일별
weekly_groups = group_by_week(messages)  # 주별 (월요일 시작)
monthly_groups = group_by_month(messages) # 월별

# 2. GroupedSummary 객체 생성 및 발신자별 우선순위 계산 (권장 방법)
summaries = []
for group_key, group_messages in daily_groups.items():
    # 기간 계산
    period_start, period_end = get_group_date_range(group_key, "daily")
    
    # 발신자별 우선순위 계산 (v1.2.1+++++++++)
    sender_priority_map = {}
    for msg in group_messages:
        sender = msg.get("sender", "Unknown")
        # 분석 결과에서 우선순위 찾기
        priority = "low"
        for result in analysis_results:
            if result.get("message", {}).get("msg_id") == msg.get("msg_id"):
                priority = result.get("priority", {}).get("priority_level", "low")
                break
        
        # 최고 우선순위 유지
        if sender not in sender_priority_map:
            sender_priority_map[sender] = priority
        else:
            priority_order = {"high": 3, "medium": 2, "low": 1}
            if priority_order.get(priority, 0) > priority_order.get(sender_priority_map[sender], 0):
                sender_priority_map[sender] = priority
    
    # GroupedSummary 객체 생성 (통계 자동 계산)
    summary = GroupedSummary.from_messages(
        messages=group_messages,
        period_start=period_start,
        period_end=period_end,
        unit="daily",
        summary_text="핵심 요약 내용...",
        key_points=["포인트 1", "포인트 2", "포인트 3"]
    )
    
    # 발신자별 우선순위 맵을 딕셔너리에 추가
    summary_dict = summary.to_dict()
    summary_dict["sender_priority_map"] = sender_priority_map
    summary_dict["brief_summary"] = "간결한 요약..."  # 선택사항
    
    summaries.append(summary_dict)

# 3. MessageSummaryPanel에 표시
panel = MessageSummaryPanel()
panel.display_summaries(summaries)  # 딕셔너리 리스트 전달

# 4. LLM 기반 그룹 요약 생성 (선택사항)
summarizer = MessageSummarizer()
llm_summaries = await summarizer.batch_summarize_groups(
    grouped_messages=daily_groups,
    unit="daily"
)
```

**주요 개선사항:**
- **v1.2.1++**: `GroupedSummary.from_messages()`로 통계 자동 계산
- **v1.2.1+++++++++**: 발신자별 우선순위 맵 추가로 더 상세한 정보 제공
  - 각 발신자의 최고 우선순위를 자동 계산
  - MessageSummaryPanel에서 색상 코딩된 배지로 표시
  - 우선순위 순서: High(3) > Medium(2) > Low(1)


## 📂 데이터셋 구성

### 현재 데이터셋 (multi_project_8week_ko)
- **기간**: 8주 데이터
- **팀 구성**: PM, 디자이너, 개발자, DevOps (4명)
- **PM 이메일**: pm.1@multiproject.dev
- **프로젝트**: 멀티 프로젝트 환경

| 파일 | 설명 |
| --- | --- |
| `chat_communications.json` | 팀 DM 로그 (sender, room_slug, sent_at 등) |
| `email_communications.json` | 팀 메일 기록 (sender, recipients, body 등) |
| `team_personas.json` | PM/디자이너/개발자/DevOps 인물 정보 |
| `final_state.json` | 시뮬레이션 상태 (tick, sim_time 등) |

### 레거시 데이터셋 (mobile_4week_ko)
- **기간**: 4주 데이터
- **팀 구성**: 모바일 앱 팀
- **상태**: 지원 종료 (v1.2.0부터)

애플리케이션은 이 JSON들만으로 동작하며, 로그인이나 외부 API 호출이 필요 없습니다.

**데이터셋 마이그레이션 가이드**: [DATASET_MIGRATION.md](docs/DATASET_MIGRATION.md)

## 📊 출력 예시
```
📦 총 58개 메시지 수집 (chat 35, email 23)
👤 PM 수신 메시지 필터링 완료: chat 35→28, email 23→18
   (PM이 보낸 메시지 12개 제외)
🎯 우선순위 분포: High 6 / Medium 14 / Low 8
🔥 상위 TODO
- [HIGH] 김민수님 오전 일정 정리 및 고객 피드백 요청
- [HIGH] 프로토타입 초안 내부 리뷰 준비
- [MEDIUM] 서버 검증 결과 요약 메일 발송
```

## 🔄 TODO 저장소
- 생성된 TODO는 `data/multi_project_8week_ko/todos_cache.db`(SQLite)에 저장됩니다.
- `ui/todo_panel.py`에서 항목 상태 변경, 스누즈, Top3 재계산 등을 지원합니다.
- Top-3 TODO는 우선순위, 데드라인, 근거 수를 기반으로 자동 계산됩니다.

## 🎨 UI 구성

### 좌측 패널 (고정 너비, 스크롤 가능) ✨ v1.2.1++++++
- **레이아웃 최적화**: 고정 너비(220px)로 더욱 컴팩트하고 효율적인 UI 제공
  - stretch factor 0으로 크기 고정
  - 우측 패널이 나머지 공간 모두 사용 (stretch factor 1)
  - 창 크기 조절 시 좌측 패널은 고정, 우측 패널만 확장/축소
  - 350px → 250px → 220px로 단계적 축소하여 우측 결과 패널 공간 최대화
- **스크롤 지원**: 많은 컨트롤이 있어도 편리하게 접근 가능
  - 수직 스크롤만 활성화 (필요시 자동 표시)
  - 수평 스크롤 비활성화로 깔끔한 레이아웃
  - 프레임 스타일 제거로 시각적 간결성 향상
- **연결 상태**: 온라인/오프라인 모드 전환
- **시간 범위 선택**: 분석할 오프라인 기간을 시작/종료 시간으로 지정
  - 빠른 선택 버튼: 최근 1시간, 4시간, 오늘, 어제, 최근 7일, 전체 기간
  - 사용자 정의 시간 범위 설정 가능
- **데이터 소스**: 현재 사용 중인 데이터셋 경로 표시
- **제어**: 메시지 수집 시작/중지, 오프라인 정리
- **날씨 정보**: 오늘/내일 날씨 및 업무 팁
- **요약 빠른 보기**: 일일/주간 요약 버튼
- **Top-3 즉시 처리**: 가장 중요한 3개 TODO 표시

### 우측 패널 (확장 가능, 탭)
- **📋 TODO 리스트**: 생성된 TODO 관리 및 편집
  - 수신 타입 배지 표시 (참조(CC), 숨은참조(BCC))
  - TOP3 자동 선정 (CC/BCC 메일은 가중치 감소)
  - 상세 다이얼로그에서 LLM 기반 요약/회신 생성
- **📨 메시지**: 수집된 메시지의 그룹화된 요약 (일/주/월 단위 선택 가능)
  - MessageSummaryPanel 컴포넌트로 카드 형태 표시
  - 발신자별 우선순위 배지 및 주요 포인트 자동 추출
- **📊 분석 결과**: 좌우 분할 레이아웃으로 요약과 상세 분석 표시 ✨ NEW (v1.2.1++++)
  - **좌측 요약 영역**: 전체 통계, 우선순위 분포, 주요 발신자
  - **우측 상세 영역**: 우선순위별 메시지 카드 (최대 10개씩 표시)
  - QSplitter로 비율 조절 가능 (기본 30:70)
  - 카드 호버 시 시각적 피드백
  - 메시지 타입 아이콘 (📧 이메일, 💬 메신저)
  - 수신 시간 정보 (🕐 수신: YYYY-MM-DD HH:MM)
  - 수신자 및 참조 정보 표시
  - 액션 수 표시 (📋 액션 N개)

## 🔧 기술 스택
- **Python 3.7+**: 메인 언어
- **PyQt6**: GUI 프레임워크
  - `QDateTimeEdit`: 시간 범위 선택 위젯
  - `QGroupBox`, `QVBoxLayout`: 레이아웃 관리
  - `pyqtSignal`: 컴포넌트 간 통신
- **SQLite**: 로컬 데이터베이스 (TODO 캐시, `recipient_type` 컬럼 포함)
- **OpenAI/Azure OpenAI/OpenRouter**: LLM 서비스
  - Azure OpenAI: `max_completion_tokens` 파라미터 사용
  - 타임아웃: 60초 (TODO 상세 다이얼로그)
- **Transformers**: 로컬 NLP 모델
- **Requests**: HTTP 클라이언트 (날씨 API, LLM API 호출)
  - Retry 로직: 최대 3회 재시도
  - 타임아웃: 연결 5초, 읽기 20초

## 🗺️ 향후 개선 아이디어
- [x] 시간 범위 선택 기능 (특정 기간의 메시지만 분석) ✅ v1.1
- [x] 메시지 그룹화 유틸리티 (일/주/월 단위) ✅ v1.1
- [x] 그룹 요약 데이터 모델 및 통계 계산 ✅ v1.1
- [x] MessageSummaryPanel UI 구현 (요약 단위 선택) ✅ v1.1
- [x] 발신자별 우선순위 배지 표시 ✅ v1.1
- [x] 간결한 요약 및 주요 포인트 추출 ✅ v1.1
- [x] 분석 결과 UI 개선 (좌우 분할 레이아웃) ✅ v1.2.1++++
- [ ] 데이터셋 교체/버전 선택 UI
- [ ] 분석 결과 리포트 PDF/Markdown 자동 생성
- [ ] QA용 자동 테스트 스크립트
- [ ] 추가 언어(EN) 대응

## 📝 로깅

애플리케이션은 Python의 표준 `logging` 모듈을 사용하여 동작을 추적합니다.

### 로그 레벨
- **DEBUG**: 상세한 디버깅 정보 (날짜 파싱, 파일 읽기, 데이터 구조 등)
- **INFO**: 일반적인 정보 메시지 (데이터 로딩, 분석 진행, 통계 등)
- **WARNING**: 경고 메시지 (데이터 누락, 파싱 실패 등)
- **ERROR**: 오류 메시지 (예외 발생, 시스템 오류 등)

### 로그 설정
```python
import logging

# 로그 레벨 설정
logging.basicConfig(
    level=logging.INFO,  # DEBUG로 변경하면 더 상세한 로그 출력
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### 모듈별 로거 사용
각 모듈은 독립적인 로거를 사용하여 로그를 출력합니다:

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

**주요 로깅 위치:**
- `ui/main_window.py`: GUI 이벤트, 사용자 액션, 데이터 로딩
- `main.py`: 메시지 수집 및 분석 파이프라인
- `nlp/` 모듈: NLP 처리 과정
- `ui/todo_panel.py`: TODO 관리 및 LLM 호출

### 데이터 로딩 로깅 (v1.2.1+++++++++++++++++++ 개선) ✨ NEW
데이터셋 시간 범위 자동 감지 시 상세한 로그를 출력합니다:

```python
# 로그 예시
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

**디버그 레벨 로그:**
- 개별 메시지의 날짜 파싱 오류
- 데이터 구조 검증
- 파일 읽기 상세 정보

### LLM 호출 로깅 (v1.1.9)
TODO 상세 다이얼로그의 LLM 호출은 상세한 로그를 출력합니다:
- **INFO**: API 호출 시작, 응답 수신, 생성 완료
- **DEBUG**: 요청 페이로드, 응답 JSON (처음 300-500자)
- **ERROR**: 타임아웃, HTTP 오류, JSON 파싱 오류

```python
# 로그 예시
[TodoDetail][LLM] provider=azure URL=https://... 요약/회신 생성 중...
[TodoDetail][LLM] 응답 수신 (status=200)
[TodoDetail][LLM] 생성 완료 (길이: 245자)
```

### 로그 확인
- 콘솔에서 실시간으로 로그 확인 가능
- 향후 `logs/` 디렉토리에 로그 파일 저장 기능 추가 예정

### 로그 레벨 변경
```bash
# 환경 변수로 설정
export LOG_LEVEL=DEBUG  # Linux/Mac
set LOG_LEVEL=DEBUG     # Windows

# 또는 코드에서 직접 설정
logging.getLogger().setLevel(logging.DEBUG)
```

### 문제 해결 시 로그 활용
데이터 로딩 문제가 발생하면 다음 로그를 확인하세요:
1. **파일 존재 여부**: `채팅 파일 확인: ... (존재: True/False)`
2. **데이터 구조**: `채팅 방 수`, `메일박스 수`
3. **날짜 수집**: `채팅에서 수집된 날짜 수`, `이메일에서 수집된 날짜 수`
4. **최종 범위**: `📅 데이터 시간 범위 자동 설정`

로그에 `⚠️` 또는 `❌` 아이콘이 표시되면 문제가 발생한 것입니다.

## ⚠️ 주의사항

### TODO 데이터 관리
- **TODO는 앱 재시작 후에도 유지됩니다** (v1.1.9+)
- 14일 이상 된 오래된 TODO는 자동으로 정리됩니다
- 모든 TODO를 삭제하려면 "모두 삭제" 버튼을 사용하세요
- TODO 데이터는 `data/multi_project_8week_ko/todos_cache.db`에 저장됩니다

## 🐛 알려진 이슈
- Windows 환경에서 한글 출력을 위해 UTF-8 인코딩이 강제 설정됩니다.
- 날씨 API 응답이 느린 경우 타임아웃이 발생할 수 있습니다 (환경변수로 조정 가능).
- 대량의 메시지 처리 시 메모리 사용량이 증가할 수 있습니다.
- 시간 범위 필터링 시 "수집할 메시지가 없습니다" 오류가 발생할 수 있습니다. → [문제 해결 가이드](TROUBLESHOOTING.md) 참조

## 📝 라이선스 & 기여
- MIT License
- 버그/개선 아이디어는 Issue 또는 PR로 환영합니다!
