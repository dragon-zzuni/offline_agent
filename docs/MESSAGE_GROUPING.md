# 메시지 그룹화 및 요약 기능

## 개요

메시지를 일/주/월 단위로 그룹화하고 각 그룹별로 통합 요약을 생성하는 기능입니다. 이를 통해 대량의 메시지를 효율적으로 분석하고 사용자에게 구조화된 정보를 제공할 수 있습니다.

## 구현된 모듈

### 1. `nlp/message_grouping.py`

메시지를 시간 단위로 그룹화하는 유틸리티 함수들을 제공합니다.

#### 주요 함수

- **`group_by_day(messages)`**: 메시지를 일별로 그룹화
  - 반환: `Dict[str, List[Dict]]` (키: YYYY-MM-DD)
  
- **`group_by_week(messages)`**: 메시지를 주별로 그룹화 (월요일 시작)
  - 반환: `Dict[str, List[Dict]]` (키: 주 시작일 YYYY-MM-DD)
  
- **`group_by_month(messages)`**: 메시지를 월별로 그룹화
  - 반환: `Dict[str, List[Dict]]` (키: YYYY-MM)
  
- **`get_group_date_range(group_key, unit)`**: 그룹 키로부터 시작/종료 날짜 계산
  - 반환: `tuple[datetime, datetime]`

#### 사용 예시

```python
from nlp.message_grouping import group_by_day, group_by_week, group_by_month

# 일별 그룹화
daily_groups = group_by_day(messages)
# {'2025-10-15': [msg1, msg2, ...], '2025-10-16': [...], ...}

# 주별 그룹화
weekly_groups = group_by_week(messages)
# {'2025-10-14': [msg1, msg2, ...], '2025-10-21': [...], ...}

# 월별 그룹화
monthly_groups = group_by_month(messages)
# {'2025-10': [msg1, msg2, ...], '2025-11': [...], ...}
```

### 2. `nlp/grouped_summary.py`

그룹화된 메시지의 요약 정보를 담는 데이터 클래스입니다.

#### GroupedSummary 클래스

```python
@dataclass
class GroupedSummary:
    period_start: datetime          # 기간 시작
    period_end: datetime            # 기간 종료
    unit: str                       # "daily", "weekly", "monthly"
    total_messages: int             # 총 메시지 수
    email_count: int                # 이메일 수
    messenger_count: int            # 메신저 수
    summary_text: str               # 요약 텍스트
    key_points: List[str]           # 핵심 포인트
    priority_distribution: Dict[str, int]  # 우선순위 분포
    top_senders: List[tuple[str, int]]     # 주요 발신자
```

#### 주요 메서드

- **`from_messages(messages, period_start, period_end, unit, ...)`**: 메시지 리스트로부터 생성
  - 통계 정보 자동 계산
  
- **`to_dict()`**: 딕셔너리로 변환 (직렬화용)

- **`from_dict(data)`**: 딕셔너리에서 복원

- **`get_period_label()`**: 사람이 읽기 쉬운 기간 레이블 반환
  - 예: "2025년 10월 15일", "2025년 10월 14일 ~ 10월 20일"

- **`get_statistics_summary()`**: 통계 정보 문자열 반환
  - 예: "총 15건 | 이메일 8건, 메신저 7건 | 우선순위: High 5건, Medium 6건, Low 4건"

#### 사용 예시

```python
from nlp.grouped_summary import GroupedSummary
from nlp.message_grouping import get_group_date_range

# 메시지 그룹으로부터 요약 생성
period_start, period_end = get_group_date_range("2025-10-15", "daily")
summary = GroupedSummary.from_messages(
    messages=daily_messages,
    period_start=period_start,
    period_end=period_end,
    unit="daily",
    summary_text="오늘의 주요 이슈는...",
    key_points=["포인트 1", "포인트 2"]
)

# 정보 출력
print(summary.get_period_label())  # "2025년 10월 15일"
print(summary.get_statistics_summary())  # "총 15건 | ..."

# 직렬화
summary_dict = summary.to_dict()
```

### 3. `nlp/summarize.py` (확장)

MessageSummarizer 클래스에 그룹 요약 메서드를 추가했습니다.

#### 추가된 메서드

- **`summarize_group(messages, group_label)`**: 그룹 메시지 통합 요약
  - 이메일과 메신저 메시지를 모두 포함하여 처리
  - LLM을 사용한 대화 흐름 요약
  - 반환: 요약 정보 딕셔너리

- **`batch_summarize_groups(grouped_messages, unit)`**: 여러 그룹 동시 요약
  - 동시 실행 제한 (CONCURRENCY=3)
  - 반환: 그룹 키별 요약 결과 딕셔너리

#### 사용 예시

```python
from nlp.summarize import MessageSummarizer
from nlp.message_grouping import group_by_day

summarizer = MessageSummarizer()

# 일별 그룹화
daily_groups = group_by_day(messages)

# 단일 그룹 요약
summary = await summarizer.summarize_group(
    messages=daily_groups["2025-10-15"],
    group_label="2025-10-15"
)

# 여러 그룹 동시 요약
all_summaries = await summarizer.batch_summarize_groups(
    grouped_messages=daily_groups,
    unit="daily"
)
```

## 통합 워크플로우

전체 프로세스를 통합한 예시입니다:

```python
import asyncio
from nlp.message_grouping import group_by_day, get_group_date_range
from nlp.grouped_summary import GroupedSummary
from nlp.summarize import MessageSummarizer

async def analyze_messages_by_day(messages):
    # 1. 일별 그룹화
    daily_groups = group_by_day(messages)
    
    # 2. 각 그룹 요약 생성
    summarizer = MessageSummarizer()
    summaries_dict = await summarizer.batch_summarize_groups(
        grouped_messages=daily_groups,
        unit="daily"
    )
    
    # 3. GroupedSummary 객체 생성
    grouped_summaries = []
    for group_key, messages in daily_groups.items():
        period_start, period_end = get_group_date_range(group_key, "daily")
        summary_data = summaries_dict.get(group_key, {})
        
        grouped_summary = GroupedSummary.from_messages(
            messages=messages,
            period_start=period_start,
            period_end=period_end,
            unit="daily",
            summary_text=summary_data.get("summary", ""),
            key_points=summary_data.get("key_points", [])
        )
        grouped_summaries.append(grouped_summary)
    
    return grouped_summaries

# 실행
summaries = await analyze_messages_by_day(all_messages)
for summary in summaries:
    print(f"{summary.get_period_label()}: {summary.get_statistics_summary()}")
```

## 테스트

`test_grouping.py` 파일을 실행하여 모든 기능을 테스트할 수 있습니다:

```bash
python test_grouping.py
```

테스트 항목:
- 일/주/월별 그룹화 함수
- GroupedSummary 데이터 모델 생성 및 변환
- 그룹 요약 생성 (LLM 사용)

## 요구사항 충족

이 구현은 다음 요구사항을 충족합니다:

- **Requirement 3.2**: 일 단위 그룹화 및 요약
- **Requirement 3.3**: 주 단위 그룹화 및 요약
- **Requirement 3.4**: 월 단위 그룹화 및 요약
- **Requirement 3.5**: 이메일과 메신저 메시지 통합 요약
- **Requirement 3.6**: 그룹별 요약으로 처리 시간 단축

## 다음 단계

이 기능을 GUI에 통합하려면:

1. **MessageSummaryPanel 구현** (Task 5)
   - 요약 단위 선택 UI
   - 그룹화된 요약 표시

2. **AnalysisResultPanel 재설계** (Task 6)
   - 좌측에 일일/주간 요약 표시
   - 우측에 상세 분석 결과 표시

3. **시간 범위와 통합** (Task 7)
   - TimeRangeSelector와 연동
   - 선택된 시간 범위 내 메시지를 선택된 단위로 그룹화
