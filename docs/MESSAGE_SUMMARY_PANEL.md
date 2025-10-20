# MessageSummaryPanel 컴포넌트 가이드

## 개요

`MessageSummaryPanel`은 Smart Assistant v1.1에서 추가된 메시지 요약 패널 컴포넌트입니다. 메시지 탭에서 일/주/월 단위로 메시지를 그룹화하여 카드 형태로 요약을 표시합니다.

## 주요 기능

### 1. 요약 단위 선택
- 라디오 버튼을 통한 직관적인 단위 선택
- 일별 요약 (Daily)
- 주별 요약 (Weekly)
- 월별 요약 (Monthly)

### 2. 카드 형태 요약 표시
각 그룹의 요약을 시각적으로 구분된 카드로 표시합니다:

| 요소 | 설명 |
|------|------|
| 헤더 | 날짜/기간 및 단위 배지 |
| 통계 | 총 메시지 수, 이메일/메신저 분포, 우선순위 분포 |
| 발신자 배지 | 주요 발신자 3명과 우선순위 해시태그 (#High, #Medium) |
| 간결한 요약 | 1-2줄로 핵심 내용을 빠르게 파악 (주제 자동 추출 포함) |
| 주요 포인트 | 최대 3개의 핵심 포인트 리스트 |

### 3. 발신자별 우선순위 표시
- **High 우선순위**: 빨간색 배지 + #High 태그
- **Medium 우선순위**: 노란색 배지 + #Medium 태그
- **Low 우선순위**: 회색 배지 (태그 없음)
- 각 발신자의 최고 우선순위를 자동으로 계산하여 표시

### 4. 주제 기반 요약 (v1.1.8+)
- **자동 주제 추출**: 메시지 내용에서 주요 주제를 자동으로 파악
- **10개 주제 카테고리**: 미팅, 보고서, 검토, 개발, 버그, 배포, 테스트, 디자인, 일정, 승인
- **다국어 지원**: 한글과 영어 키워드를 동시에 지원
- **성능 최적화**: 최대 20개 메시지만 분석하여 빠른 응답
- **예시**:
  - 기존: "총 82건의 메시지가 수집되었습니다"
  - 개선: "미팅, 보고서 관련 82건 (긴급 5건) 주요 발신자: Kim Jihoon (40건)"

### 4. 스크롤 가능한 리스트
- 많은 그룹이 있어도 스크롤로 모두 확인 가능
- 수평 스크롤바 숨김 처리
- 부드러운 스크롤 경험

### 5. 시그널
- `summary_unit_changed(str)`: 요약 단위가 변경되었을 때 발생

## 사용 방법

### 기본 사용
```python
from ui.message_summary_panel import MessageSummaryPanel

# 컴포넌트 생성
panel = MessageSummaryPanel()

# 시그널 연결
panel.summary_unit_changed.connect(on_unit_changed)

# 레이아웃에 추가
layout.addWidget(panel)
```

### 요약 표시
```python
from datetime import datetime
from collections import Counter

summaries = [
    {
        "period_start": datetime(2025, 10, 15),
        "period_end": datetime(2025, 10, 15, 23, 59, 59),
        "unit": "daily",
        "total_messages": 15,
        "email_count": 8,
        "messenger_count": 7,
        "brief_summary": "총 15건의 메시지 중 5건이 높은 우선순위입니다. 김철수님으로부터 5건의 메시지가 있습니다.",
        "key_points": [
            "프로젝트 일정 1주일 연기",
            "긴급 버그 3건 수정 완료",
            "새로운 기능 요청 2건"
        ],
        "priority_distribution": {
            "high": 5,
            "medium": 6,
            "low": 4
        },
        "top_senders": [
            ("김철수", 5),
            ("이영희", 3),
            ("박민수", 2)
        ],
        "sender_priority_map": {
            "김철수": "high",
            "이영희": "medium",
            "박민수": "low"
        }
    }
]

panel.display_summaries(summaries)
```

### 요약 단위 변경
```python
# 프로그래밍 방식으로 단위 설정
panel.set_summary_unit("weekly")

# 현재 단위 가져오기
current_unit = panel.get_summary_unit()  # "daily", "weekly", "monthly"
```

### 내용 초기화
```python
# 모든 요약 카드 제거
panel.clear()
```

## 통합 예시

### GUI에서 사용
```python
class SmartAssistantGUI(QMainWindow):
    def create_message_tab(self):
        """메시지 탭 생성"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # MessageSummaryPanel 생성
        self.message_summary_panel = MessageSummaryPanel()
        self.message_summary_panel.summary_unit_changed.connect(
            self._on_summary_unit_changed
        )
        layout.addWidget(self.message_summary_panel)
        
        return tab
    
    def _on_summary_unit_changed(self, unit: str):
        """요약 단위 변경 콜백"""
        if not self.collected_messages:
            self.status_message.setText("메시지를 먼저 수집해주세요.")
            return
        
        # 그룹화된 요약 생성 및 표시
        self._update_message_summaries(unit)
        
        # 상태바 업데이트
        unit_text = {"daily": "일별", "weekly": "주별", "monthly": "월별"}.get(unit, unit)
        self.status_bar.showMessage(f"요약 단위 변경: {unit_text}", 3000)
    
    def _update_message_summaries(self, unit: str = "daily"):
        """메시지 요약 업데이트"""
        from nlp.message_grouping import group_by_day, group_by_week, group_by_month
        
        # 메시지 그룹화
        if unit == "daily":
            groups = group_by_day(self.collected_messages)
        elif unit == "weekly":
            groups = group_by_week(self.collected_messages)
        elif unit == "monthly":
            groups = group_by_month(self.collected_messages)
        else:
            groups = group_by_day(self.collected_messages)
        
        # 각 그룹에 대한 요약 생성
        summaries = []
        for group_key, messages in groups.items():
            # 요약 데이터 생성 로직
            summary = self._create_group_summary(group_key, messages, unit)
            summaries.append(summary)
        
        # MessageSummaryPanel에 표시
        self.message_summary_panel.display_summaries(summaries)
```

## UI 스타일링

컴포넌트는 Tailwind CSS 스타일의 색상 팔레트를 사용합니다:

```python
# 요약 단위 선택 영역
QFrame {
    background-color: #F3F4F6;  # 밝은 회색
    border: 1px solid #E5E7EB;
    border-radius: 8px;
}

# 요약 카드
QFrame {
    background-color: #FFFFFF;  # 흰색
    border: 1px solid #E5E7EB;
    border-radius: 8px;
}
QFrame:hover {
    border-color: #D1D5DB;
    background-color: #F9FAFB;  # 호버 시 약간 어두운 회색
}

# 단위 배지
QLabel {
    background-color: #DBEAFE;  # 밝은 파란색
    color: #1E40AF;             # 진한 파란색
    border-radius: 12px;
}
```

## 데이터 구조

### 요약 딕셔너리 스키마
```python
{
    "period_start": datetime,           # 기간 시작 (datetime 객체 또는 ISO 문자열)
    "period_end": datetime,             # 기간 종료 (datetime 객체 또는 ISO 문자열)
    "unit": str,                        # "daily", "weekly", "monthly"
    "total_messages": int,              # 총 메시지 수
    "email_count": int,                 # 이메일 수 (선택)
    "messenger_count": int,             # 메신저 수 (선택)
    "brief_summary": str,               # 간결한 요약 (1-2줄)
    "key_points": List[str],            # 주요 포인트 리스트 (최대 3개, 선택)
    "priority_distribution": {          # 우선순위 분포 (선택)
        "high": int,
        "medium": int,
        "low": int
    },
    "top_senders": List[Tuple[str, int]],  # 주요 발신자 리스트 (선택)
    "sender_priority_map": Dict[str, str]   # 발신자별 최고 우선순위 (선택)
}
```

## 내부 메서드

### 공개 메서드
- `display_summaries(summaries: List[Dict])`: 요약 리스트 표시
- `clear()`: 모든 요약 카드 제거
- `set_summary_unit(unit: str)`: 요약 단위 설정
- `get_summary_unit() -> str`: 현재 요약 단위 반환

### 비공개 메서드
- `_init_ui()`: UI 초기화
- `_create_unit_selector() -> QWidget`: 요약 단위 선택 UI 생성
- `_on_unit_changed()`: 요약 단위 변경 이벤트 핸들러
- `_show_empty_message()`: 빈 상태 메시지 표시
- `_create_summary_card(summary: Dict) -> QWidget`: 요약 카드 생성
- `_create_card_header(summary: Dict) -> QWidget`: 카드 헤더 생성
- `_format_period(summary: Dict) -> str`: 기간 포맷팅
- `_create_card_stats(summary: Dict) -> QWidget`: 카드 통계 생성
- `_create_sender_badges(top_senders: List[tuple], priority_map: Dict[str, str]) -> QWidget`: 발신자 배지 생성 (우선순위 포함)
- `_create_stat_item(icon: str, text: str) -> QLabel`: 통계 항목 생성
- `_create_key_points(points: List[str]) -> QWidget`: 주요 포인트 위젯 생성

## 향후 개선 사항

- [x] 발신자별 우선순위 배지 표시 ✅ v1.1
- [x] 간결한 요약 (1-2줄) ✅ v1.1
- [x] 주요 포인트 자동 추출 (최대 3개) ✅ v1.1
- [ ] 카드 클릭 시 상세 정보 팝업
- [ ] 요약 내용 복사 기능
- [ ] 요약 내보내기 (PDF, Markdown)
- [ ] 커스텀 날짜 범위 필터링
- [ ] 발신자별 필터링
- [ ] 우선순위별 필터링
- [ ] 검색 기능

## 관련 파일

- `ui/message_summary_panel.py`: 컴포넌트 구현
- `ui/main_window.py`: GUI 통합
- `nlp/message_grouping.py`: 메시지 그룹화 유틸리티
- `nlp/grouped_summary.py`: 그룹 요약 데이터 모델
- `.kiro/specs/ui-improvements/requirements.md`: 요구사항 문서
- `.kiro/specs/ui-improvements/tasks.md`: 구현 작업 목록

## 참고 자료

- [PyQt6 QWidget 문서](https://doc.qt.io/qt-6/qwidget.html)
- [PyQt6 QRadioButton 문서](https://doc.qt.io/qt-6/qradiobutton.html)
- [PyQt6 QScrollArea 문서](https://doc.qt.io/qt-6/qscrollarea.html)
- Smart Assistant UI/UX 개선 스펙 (Requirement 3)
- MESSAGE_GROUPING.md: 메시지 그룹화 기능 가이드
