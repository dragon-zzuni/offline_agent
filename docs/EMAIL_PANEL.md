# EmailPanel 컴포넌트 가이드

## 개요

`EmailPanel`은 Smart Assistant v1.1.7에서 추가된 이메일 필터링 패널 컴포넌트입니다. TODO로 변환할 가치가 있는 이메일만 자동으로 필터링하여 카드 형태로 표시합니다.

## 주요 기능

### 1. 스마트 필터링
키워드 기반 휴리스틱으로 업무 관련 이메일만 자동 필터링합니다:

| 카테고리 | 키워드 |
|---------|--------|
| 요청 | 요청, request, 부탁, 확인, check |
| 검토 | 검토, review, 승인, approval, 결재 |
| 회의 | 회의, meeting, 미팅, 일정, schedule |
| 긴급 | 마감, deadline, 긴급, urgent, asap |
| 문의 | 질문, question, 문의, inquiry |

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

### 3. 실시간 카운트
필터링된 이메일 수를 실시간으로 표시합니다.

### 4. 호버 효과
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
        "subject": "프로젝트 검토 요청",
        "sender": "김철수",
        "body": "첨부된 문서를 검토해 주세요.",
        "timestamp": "2025-10-17 14:30"
    },
    {
        "subject": "안녕하세요",
        "sender": "이영희",
        "body": "잘 지내시나요?",
        "timestamp": "2025-10-17 15:00"
    }
]

# 이메일 목록 업데이트 (자동 필터링됨)
panel.update_emails(emails)
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
    "subject": str,        # 이메일 제목
    "sender": str,         # 발신자 이름
    "body": str,           # 이메일 본문
    "timestamp": str,      # 수신 시간 (선택)
    "sender_email": str,   # 발신자 이메일 (선택)
    "recipients": List[str],  # 수신자 목록 (선택)
}
```

## 내부 메서드

### 공개 메서드
- `update_emails(emails: List[Dict])`: 이메일 목록 업데이트 및 필터링
- `clear()`: 이메일 목록 초기화

### 비공개 메서드
- `_init_ui()`: UI 초기화
- `_filter_todo_worthy_emails(emails: List[Dict]) -> List[Dict]`: 키워드 기반 필터링

## 필터링 로직

### 키워드 매칭
```python
# 제목과 본문을 소문자로 변환하여 검색
subject = (email.get("subject") or "").lower()
body = (email.get("body") or "").lower()
content = f"{subject} {body}"

# 키워드 중 하나라도 포함되면 필터링 통과
if any(keyword in content for keyword in all_keywords):
    filtered.append(email)
```

### 로깅
```python
# 디버그 로그: 필터링 통과한 이메일
logger.debug(f"이메일 필터링 통과: {subject[:30]}")

# 정보 로그: 필터링 결과 요약
logger.info(f"📧 이메일 필터링 완료: {total}개 → {filtered}개")
```

## 향후 개선 사항

- [ ] LLM 기반 필터링 (키워드 기반 → AI 기반)
- [ ] 우선순위별 색상 코딩
- [ ] 이메일 클릭 시 상세 정보 팝업
- [ ] 필터링 규칙 커스터마이징
- [ ] 이메일 검색 기능
- [ ] 발신자별 필터링
- [ ] 날짜 범위 필터링
- [ ] 읽음/안읽음 상태 표시

## 관련 파일

- `ui/email_panel.py`: 컴포넌트 구현
- `ui/main_window.py`: GUI 통합
- `main.py`: 메시지 수집 및 분석
- `.kiro/specs/ui-improvements/requirements.md`: 요구사항 문서

## 참고 자료

- [PyQt6 QListWidget 문서](https://doc.qt.io/qt-6/qlistwidget.html)
- [PyQt6 QWidget 문서](https://doc.qt.io/qt-6/qwidget.html)
- Smart Assistant UI/UX 개선 스펙

