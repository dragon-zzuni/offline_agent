# EmailPanel 컴포넌트 가이드

## 개요

`EmailPanel`은 Smart Assistant v1.1.7에서 추가된 이메일 필터링 패널 컴포넌트입니다. TODO 리스트에 포함되지 않은 이메일만 자동으로 필터링하여 카드 형태로 표시합니다.

**v1.2.1+++++++++++++++++++++++ 업데이트**: 이메일 클릭 시 상세 다이얼로그 표시 기능 추가 ✨

## 주요 기능

### 1. TODO 기반 필터링
TODO 리스트에 포함되지 않은 이메일만 자동으로 필터링합니다:

- **중복 방지**: TODO로 변환된 이메일은 자동으로 제외
- **메시지 ID 추적**: `source_message.msg_id` 기반으로 정확한 필터링
- **실시간 업데이트**: TODO 생성 시 자동으로 이메일 목록 갱신

### 2. 카드 형태 UI
각 이메일을 시각적으로 구분된 카드로 표시합니다:

```
┌─────────────────────────────────────┐
│ 제목: 프로젝트 검토 요청    발신: 김철수 │
│ ─────────────────────────────────── │
│ 내용 미리보기 (최대 100자)...        │
│                                     │
│ 수신: 2025-10-17 14:30              │
└─────────────────────────────────────┘
```

### 3. 이메일 상세 보기 (v1.2.1+++++++++++++++++++++++ 신규) ✨
이메일 항목 클릭 시 MessageDetailDialog로 전체 내용을 표시합니다:

- **전체 내용 확인**: 발신자, 제목, 전체 본문
- **수신자 정보**: TO, CC, BCC 목록 표시
- **키보드 단축키**: 
  - `Enter`: 메시지 선택
  - `Esc`: 다이얼로그 닫기
  - `↑/↓`: 이전/다음 이메일 탐색
- **일관된 UX**: MessageSummaryPanel과 동일한 다이얼로그 사용

### 4. 실시간 카운트
필터링된 이메일 수를 실시간으로 표시합니다.

### 5. 호버 효과
마우스 오버 시 시각적 피드백을 제공합니다.

## 사용 방법

### 기본 사용
```python
from ui.email_panel import EmailPanel

# 컴포넌트 생성
panel = EmailPanel()

# 레이아웃에 추가
layout.addWidget(panel)
```

### 이메일 업데이트
```python
emails = [
    {
        "msg_id": "email_001",
        "type": "email",
        "subject": "프로젝트 검토 요청",
        "sender": "김철수",
        "body": "첨부된 문서를 검토해 주세요.",
        "timestamp": "2025-10-17 14:30",
        "recipients": ["pm@company.com"],
        "cc": ["team@company.com"]
    },
    {
        "msg_id": "email_002",
        "type": "email",
        "subject": "안녕하세요",
        "sender": "이영희",
        "body": "잘 지내시나요?",
        "timestamp": "2025-10-17 15:00"
    }
]

# TODO 아이템 목록 (선택사항)
todo_items = [
    {
        "id": "todo_001",
        "source_message": {
            "msg_id": "email_001"  # 이 이메일은 필터링에서 제외됨
        }
    }
]

# 이메일 목록 업데이트 (TODO에 없는 이메일만 표시)
panel.update_emails(emails, todo_items)
```

### 초기화
```python
# 이메일 목록 초기화
panel.clear()
```

## 통합 예시

### GUI에서 사용
```python
class SmartAssistantGUI(QMainWindow):
    def create_email_tab(self):
        """이메일 탭 생성"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # EmailPanel 생성
        self.email_panel = EmailPanel()
        layout.addWidget(self.email_panel)
        
        return tab
    
    def handle_result(self, result: dict):
        """분석 결과 처리"""
        if not result.get("success"):
            return
        
        # 수집된 메시지에서 이메일만 추출
        messages = result.get("messages", [])
        emails = [m for m in messages if m.get("type") == "email"]
        
        # EmailPanel 업데이트
        self.email_panel.update_emails(emails)
```

## UI 스타일링

컴포넌트는 Tailwind CSS 스타일의 색상 팔레트를 사용합니다:

```python
# 이메일 카드
QWidget {
    border: 1px solid #D1D5DB;
    border-radius: 10px;
    background: #FFFFFF;
}
QWidget:hover {
    border-color: #9CA3AF;
    background: #F9FAFB;
}

# 헤더
QLabel {
    font-size: 16px;
    font-weight: 700;
    color: #1F2937;
}

# 카운트 배지
QLabel {
    color: #6B7280;
    background: #F3F4F6;
    padding: 4px 12px;
    border-radius: 12px;
}
```

## 데이터 구조

### 이메일 딕셔너리 스키마
```python
{
    "msg_id": str,         # 메시지 고유 ID (필수)
    "type": str,           # "email" (필수)
    "subject": str,        # 이메일 제목
    "sender": str,         # 발신자 이름
    "body": str,           # 이메일 본문
    "content": str,        # 이메일 본문 (대체 필드)
    "date": str,           # 수신 시간 (ISO 8601 형식)
    "timestamp": str,      # 수신 시간 (대체 필드)
    "sender_email": str,   # 발신자 이메일 (선택)
    "recipients": List[str],  # 수신자 목록 (TO)
    "cc": List[str],       # 참조 목록 (선택)
    "bcc": List[str],      # 숨은참조 목록 (선택)
}
```

### TODO 아이템 스키마
```python
{
    "id": str,             # TODO 고유 ID
    "source_message": {    # 원본 메시지 정보
        "msg_id": str,     # 메시지 ID (필터링에 사용)
        "type": str,
        "subject": str,
        # ... 기타 필드
    }
}
```

## 내부 메서드

### 공개 메서드
- `update_emails(emails: List[Dict], todo_items: List[Dict] = None)`: 이메일 목록 업데이트 및 필터링
- `clear()`: 이메일 목록 초기화

### 비공개 메서드
- `_init_ui()`: UI 초기화
- `_filter_non_todo_emails(emails: List[Dict]) -> List[Dict]`: TODO에 없는 이메일만 필터링
- `_on_email_clicked(item: QListWidgetItem)`: 이메일 클릭 이벤트 핸들러 ✨ NEW

## 필터링 로직

### TODO 기반 필터링
```python
def _filter_non_todo_emails(self, emails: List[Dict]) -> List[Dict]:
    """TODO 리스트에 없는 이메일만 필터링"""
    filtered = []
    for email in emails:
        # 이메일 타입만 필터링
        if email.get("type", "").lower() != "email":
            continue
        
        # TODO에 포함되지 않은 이메일만 추가
        msg_id = email.get("msg_id") or email.get("id")
        if msg_id and msg_id not in self.todo_message_ids:
            filtered.append(email)
    
    return filtered
```

### 이메일 클릭 처리 (v1.2.1+++++++++++++++++++++++ 신규) ✨
```python
def _on_email_clicked(self, item: QListWidgetItem):
    """이메일 클릭 이벤트 핸들러"""
    # 클릭된 아이템의 인덱스 가져오기
    row = self.email_list.row(item)
    
    # TODO에 없는 이메일 목록에서 해당 이메일 찾기
    filtered_emails = self._filter_non_todo_emails(self.emails)
    
    if row < 0 or row >= len(filtered_emails):
        logger.warning(f"유효하지 않은 이메일 인덱스: {row}")
        return
    
    email = filtered_emails[row]
    
    # MessageDetailDialog를 사용하여 이메일 상세 표시
    from ui.message_detail_dialog import MessageDetailDialog
    
    summary_group = {
        "period_label": email.get("subject", "이메일 상세"),
        "statistics_summary": f"발신: {email.get('sender', 'Unknown')}",
        "total_messages": 1,
        "email_count": 1,
        "messenger_count": 0
    }
    
    dialog = MessageDetailDialog(summary_group, [email], self)
    dialog.exec()
```

### 로깅
```python
# 정보 로그: 필터링 결과 요약
logger.info(f"📧 TODO에 없는 이메일: {len(filtered)}건 (전체 {len(emails)}건)")

# 경고 로그: 유효하지 않은 인덱스
logger.warning(f"유효하지 않은 이메일 인덱스: {row}")

# 에러 로그: 예외 발생
logger.error(f"이메일 클릭 처리 오류: {e}", exc_info=True)
```

## 향후 개선 사항

- [x] 이메일 클릭 시 상세 정보 팝업 ✅ v1.2.1+++++++++++++++++++++++
- [ ] 우선순위별 색상 코딩
- [ ] 이메일 미리보기 툴팁
- [ ] 더블 클릭 vs 싱글 클릭 동작 구분
- [ ] 이메일 검색 기능
- [ ] 발신자별 필터링
- [ ] 날짜 범위 필터링
- [ ] 읽음/안읽음 상태 표시
- [ ] 이메일 정렬 옵션 (날짜, 발신자, 제목)

## 관련 파일

- `ui/email_panel.py`: 컴포넌트 구현
- `ui/main_window.py`: GUI 통합
- `main.py`: 메시지 수집 및 분석
- `.kiro/specs/ui-improvements/requirements.md`: 요구사항 문서

## 참고 자료

- [PyQt6 QListWidget 문서](https://doc.qt.io/qt-6/qlistwidget.html)
- [PyQt6 QWidget 문서](https://doc.qt.io/qt-6/qwidget.html)
- Smart Assistant UI/UX 개선 스펙

