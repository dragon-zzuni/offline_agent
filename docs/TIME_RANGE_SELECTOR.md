# TimeRangeSelector 컴포넌트 가이드

## 개요

`TimeRangeSelector`는 Smart Assistant v1.1에서 추가된 시간 범위 선택 컴포넌트입니다. 사용자가 오프라인 기간을 시작/종료 시간으로 지정하여 특정 기간의 메시지만 분석할 수 있도록 합니다.

## 주요 기능

### 1. 시작/종료 시간 선택
- `QDateTimeEdit` 위젯을 사용한 직관적인 날짜/시간 선택
- 캘린더 팝업 지원
- 표시 형식: `yyyy-MM-dd HH:mm`

### 2. 빠른 선택 버튼
자주 사용하는 시간 범위를 원클릭으로 설정할 수 있습니다:

| 버튼 | 설명 | 범위 |
|------|------|------|
| 최근 1시간 | 현재 시간 기준 1시간 전부터 | now - 1h ~ now |
| 최근 4시간 | 현재 시간 기준 4시간 전부터 | now - 4h ~ now |
| 오늘 | 오늘 00:00부터 현재까지 | today 00:00 ~ now |
| 어제 | 어제 00:00부터 23:59까지 | yesterday 00:00 ~ 23:59 |
| 최근 7일 | 현재 시간 기준 7일 전부터 | now - 7d ~ now |

### 3. 유효성 검증
- 종료 시간이 시작 시간보다 이전인 경우 경고 메시지 표시
- 잘못된 범위 입력 방지

### 4. 시그널
- `time_range_changed(datetime, datetime)`: 시간 범위가 변경되었을 때 발생

## 사용 방법

### 기본 사용
```python
from ui.time_range_selector import TimeRangeSelector

# 컴포넌트 생성
selector = TimeRangeSelector()

# 시그널 연결
selector.time_range_changed.connect(on_time_range_changed)

# 레이아웃에 추가
layout.addWidget(selector)
```

### 시간 범위 가져오기
```python
start, end = selector.get_time_range()
print(f"시작: {start}")
print(f"종료: {end}")
```

### 시간 범위 설정
```python
from datetime import datetime, timedelta

now = datetime.now()
start = now - timedelta(hours=4)
selector.set_time_range(start, now)
```

### 기본값으로 리셋
```python
# 최근 30일로 리셋
selector.reset_to_default()
```

## 통합 예시

### GUI에서 사용
```python
class SmartAssistantGUI(QMainWindow):
    def create_left_panel(self):
        # 시간 범위 선택기 추가
        time_range_group = QGroupBox("시간 범위 선택")
        time_range_layout = QVBoxLayout(time_range_group)
        
        self.time_range_selector = TimeRangeSelector()
        self.time_range_selector.time_range_changed.connect(
            self._on_time_range_changed
        )
        
        time_range_layout.addWidget(self.time_range_selector)
        layout.addWidget(time_range_group)
    
    def _on_time_range_changed(self, start: datetime, end: datetime):
        """시간 범위 변경 콜백"""
        # collect_options에 시간 범위 저장
        self.collect_options["time_range"] = {
            "start": start.isoformat(),
            "end": end.isoformat()
        }
        
        # 이전 결과 초기화
        self.analysis_results = []
        self.collected_messages = []
        
        # 상태 메시지 업데이트
        self.status_message.setText(
            f"시간 범위 설정됨: {start:%Y-%m-%d %H:%M} ~ {end:%Y-%m-%d %H:%M}"
        )
```

### 백엔드에서 시간 범위 필터링
```python
from datetime import datetime, timezone

async def collect_messages(
    self,
    email_limit: Optional[int] = None,
    messenger_limit: Optional[int] = None,
    overall_limit: Optional[int] = None,
    force_reload: bool = False,
    time_range: Optional[Dict[str, Any]] = None,
):
    """메시지 수집 (시간 범위 필터링 지원)
    
    Args:
        time_range: 시간 범위 필터 {"start": datetime, "end": datetime}
                   - naive datetime은 자동으로 UTC로 변환됩니다
    """
    # 데이터셋 로드
    chat_messages = list(self._chat_messages)
    email_messages = list(self._email_messages)
    
    # 시간 범위 필터링
    if time_range:
        start_time = time_range.get("start")
        end_time = time_range.get("end")
        
        if start_time or end_time:
            # naive datetime을 UTC aware로 변환
            if start_time and start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=timezone.utc)
            if end_time and end_time.tzinfo is None:
                end_time = end_time.replace(tzinfo=timezone.utc)
            
            logger.info(
                "⏰ 시간 범위 필터링 시작: %s ~ %s",
                start_time.isoformat() if start_time else "제한없음",
                end_time.isoformat() if end_time else "제한없음"
            )
            
            def _in_time_range(msg: Dict[str, Any]) -> bool:
                try:
                    msg_date = parse_iso_datetime(msg.get("date", ""))
                    if not msg_date:
                        return False
                    return is_in_time_range(msg_date, start_time, end_time)
                except Exception as e:
                    logger.debug(f"날짜 필터링 실패: {msg.get('msg_id')} - {e}")
                    return False
            
            # 필터링 전 메시지 수 기록
            original_chat_count = len(chat_messages)
            original_email_count = len(email_messages)
            
            chat_messages = [m for m in chat_messages if _in_time_range(m)]
            email_messages = [m for m in email_messages if _in_time_range(m)]
            
            logger.info(
                "⏰ 시간 범위 필터링 완료: chat %d→%d, email %d→%d",
                original_chat_count, len(chat_messages),
                original_email_count, len(email_messages)
            )
    
    return chat_messages + email_messages
```

## UI 스타일링

컴포넌트는 보라색 테마를 사용하여 시각적으로 구분됩니다:

```python
# 빠른 선택 버튼 스타일
QPushButton {
    background-color: #8B5CF6;  /* 보라색 */
    color: white;
    border: none;
    padding: 6px;
    border-radius: 4px;
    font-weight: 600;
    font-size: 11px;
}
QPushButton:hover {
    background-color: #7C3AED;  /* 진한 보라색 */
}

# 적용 버튼 스타일
QPushButton {
    background-color: #10B981;  /* 녹색 */
    color: white;
    border: none;
    padding: 8px;
    border-radius: 4px;
    font-weight: bold;
}
```

## 기본 동작

### 초기 상태
- 기본 시간 범위: 최근 30일 (now - 30d ~ now)
- 자동으로 현재 시간과 30일 전 시간이 설정됨
- 대부분의 오프라인 데이터를 포함하여 "메시지 없음" 오류를 방지

### 빠른 선택 버튼 클릭 시
1. 해당 범위로 시작/종료 시간 자동 설정
2. 사용자가 `적용` 버튼을 클릭해야 시그널 발생

### 수동 입력 시
1. 시작/종료 시간을 직접 입력
2. `적용` 버튼 클릭
3. 유효성 검증 후 시그널 발생

## 에러 처리

### 잘못된 시간 범위
```python
if end <= start:
    QMessageBox.warning(
        self,
        "유효하지 않은 시간 범위",
        "종료 시간은 시작 시간 이후여야 합니다."
    )
    return False
```

## 향후 개선 사항

- [ ] 사전 정의된 시간 범위 프리셋 저장/불러오기
- [ ] 시간대(timezone) 선택 기능
- [ ] 시간 범위 히스토리 관리
- [ ] 시간 범위 시각화 (타임라인 그래프)
- [ ] 키보드 단축키 지원
- [x] Naive datetime 자동 UTC 변환 ✅ v1.1
- [x] 필터링 전후 메시지 수 비교 로그 ✅ v1.1
- [x] 기본 범위를 30일로 확대하여 사용성 개선 ✅ v1.1.5

## 관련 파일

- `ui/time_range_selector.py`: 컴포넌트 구현
- `ui/main_window.py`: GUI 통합
- `.kiro/specs/ui-improvements/requirements.md`: 요구사항 문서
- `.kiro/specs/ui-improvements/tasks.md`: 구현 작업 목록

## 참고 자료

- [PyQt6 QDateTimeEdit 문서](https://doc.qt.io/qt-6/qdatetimeedit.html)
- [Python datetime 모듈](https://docs.python.org/3/library/datetime.html)
- Smart Assistant UI/UX 개선 스펙 (Requirement 2)
