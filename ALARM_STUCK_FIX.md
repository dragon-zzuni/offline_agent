# 알람 상태 멈춤 문제 해결

## 문제 상황
- Top-3 TODO 카드가 주황색 테두리(unread 상태)로 표시됨
- 시뮬레이션 틱이 비활성화되어도 알람 상태가 계속 유지됨
- 사용자가 카드를 확인해도 unread 상태가 해제되지 않음

## 원인 분석
1. **End2EndCard에 상태 업데이트 메서드 부재**
   - `BasicTodoItem`에는 `set_unread()` 메서드가 있지만
   - `End2EndCard`에는 상태를 변경하는 메서드가 없었음
   - 생성 시 설정된 unread 스타일이 계속 유지됨

2. **사용자 상호작용 시 상태 변경 없음**
   - 텍스트 편집, 버튼 클릭 등의 상호작용에도
   - unread 상태가 자동으로 해제되지 않음

## 해결 방법

### 1. End2EndCard에 상태 관리 기능 추가
```python
class End2EndCard(QWidget):
    def __init__(self, todo: dict, parent=None, unread: bool = False):
        self._unread = unread
        self._unread_style = "..."  # 주황색 스타일
        self._read_style = "..."    # 기본 스타일
        
    def set_unread(self, unread: bool):
        """읽음/안읽음 상태 설정"""
        if self._unread != unread:
            self._unread = unread
            self._apply_style()
    
    def _apply_style(self):
        """현재 상태에 맞는 스타일 적용"""
        if self._unread:
            self.title_label.setText("🟢 " + title)  # 초록 점
            self.setStyleSheet(self._unread_style)
        else:
            self.title_label.setText("🔴 " + title)  # 빨간 점
            self.setStyleSheet(self._read_style)
```

### 2. 사용자 상호작용 시 자동 unread 해제
```python
# 텍스트 편집 시
self.subject.textChanged.connect(self._on_text_changed)
self.body.textChanged.connect(self._on_text_changed)

def _on_text_changed(self):
    if self._unread:
        self.set_unread(False)

# 버튼 클릭 시
def _on_button_clicked(self, signal: pyqtSignal):
    if self._unread:
        self.set_unread(False)
    signal.emit(self._payload())
```

### 3. Top-3 다이얼로그 열릴 때 자동 읽음 처리
```python
def show_top3_dialog(self):
    # 카드 생성
    cards = []
    for todo in self._top3_cache:
        card = End2EndCard(todo, parent=dlg, unread=unread)
        cards.append((card, todo_id))
    
    # 다이얼로그 표시 후 1초 뒤 unread 해제
    def on_dialog_shown():
        for card, todo_id in cards:
            if todo_id:
                self._viewed_ids.add(todo_id)
            QTimer.singleShot(1000, lambda c=card: c.set_unread(False))
    
    QTimer.singleShot(100, on_dialog_shown)
```

## 수정된 파일
- `offline_agent/src/ui/widgets/end2end_card.py`
  - `set_unread()` 메서드 추가
  - `_apply_style()` 메서드 추가
  - 텍스트 변경 시 unread 자동 해제
  - 버튼 클릭 시 unread 자동 해제

- `offline_agent/src/ui/todo_panel.py`
  - Top-3 다이얼로그 열릴 때 자동 읽음 처리
  - 1초 후 unread 상태 자동 해제

## 테스트 방법
1. 앱 재시작
2. VirtualOffice 연결 및 페르소나 선택
3. 새 메시지 도착 시 Top-3 카드 확인
4. 다이얼로그 열면 1초 후 주황색 테두리가 회색으로 변경되는지 확인
5. 텍스트 편집 또는 버튼 클릭 시 즉시 unread 해제되는지 확인

## 기대 효과
- ✅ 알람 상태가 자동으로 해제됨
- ✅ 사용자 상호작용 시 즉시 읽음 처리
- ✅ 다이얼로그 열면 자동으로 읽음 처리
- ✅ 불필요한 시각적 알림 제거
