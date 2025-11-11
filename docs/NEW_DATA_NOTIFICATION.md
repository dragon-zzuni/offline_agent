# 새 데이터 수집 알림 기능

## 개요

VDOS tick 상태가 변경되어 새 메시지가 수집될 때, 사용자에게 시각적 팝업 알림을 표시하는 기능입니다.

---

## 기능 설명

### 1. 새 데이터 수집 알림 (1차)

**트리거**: 폴링 워커가 새 메시지를 감지했을 때

**표시 내용**:
```
📬 새 데이터 수집

새로운 메시지가 수집되었습니다!

📧 총 메시지:     15개
✅ 예상 TODO:      8개

※ TODO는 LLM 분석 후 자동으로 생성됩니다
```

**특징**:
- 비모달 팝업 (백그라운드 작업 방해 안 함)
- 3초 후 자동 닫기
- 예상 TODO 개수는 키워드 기반 추정

### 2. TODO 생성 완료 알림 (2차)

**트리거**: 백그라운드 LLM 분석 완료 후 TODO 생성 시

**표시 내용**:
```
✅ TODO 생성 완료

새로운 TODO가 생성되었습니다!

📋 생성된 TODO:   5개

※ TODO 리스트에서 확인하세요
```

**특징**:
- 비모달 팝업
- 3초 후 자동 닫기
- 실제 생성된 TODO 개수 표시

---

## 처리 흐름

```
1. VDOS Tick 변경
   ↓
2. 폴링 워커가 새 메시지 감지
   ↓
3. 📬 1차 알림: "새 데이터 수집" (예상 TODO 개수)
   ↓
4. 백그라운드 LLM 분석 시작
   ↓
5. TODO 생성 완료
   ↓
6. ✅ 2차 알림: "TODO 생성 완료" (실제 TODO 개수)
```

---

## 예상 TODO 계산 로직

### 키워드 기반 추정

```python
action_keywords = [
    "요청", "부탁", "검토", "확인", "회신", "답변", 
    "피드백", "의견", "승인", "결재", "미팅", "회의"
]

# 메시지 내용에 액션 키워드가 있으면 TODO 후보로 간주
for msg in messages:
    content = msg.get("body", "") + msg.get("subject", "")
    if any(keyword in content for keyword in action_keywords):
        estimated_todos += 1
```

### 실제 TODO 생성 조건

```python
# LLM 분석 후 action_required = true인 것만 TODO 생성
# 예상 개수와 실제 개수는 다를 수 있음

예시:
- 예상 TODO: 8개 (키워드 기반)
- 실제 TODO: 5개 (LLM 판단 후)
```

---

## 코드 구조

### 1. 새 데이터 수집 알림

**파일**: `offline_agent/src/ui/main_window.py`

```python
def on_new_data_received(self, data: dict):
    """새 데이터 수신 핸들러"""
    # ... 데이터 처리 ...
    
    # TODO 생성 개수 계산 및 팝업 표시
    new_todo_count = self._count_new_todos(unique_messages)
    self._show_new_data_notification(total_new_unique, new_todo_count)

def _count_new_todos(self, messages: list) -> int:
    """새 메시지에서 생성될 TODO 개수 추정"""
    # 키워드 기반 추정 로직
    
def _show_new_data_notification(self, total_messages: int, estimated_todos: int):
    """새 데이터 수집 알림 팝업 표시"""
    # QMessageBox 생성 및 표시
```

### 2. TODO 생성 완료 알림

**파일**: `offline_agent/src/ui/main_window_components/analysis_cache_controller.py`

```python
def _handle_background_analysis_result(self, result: Dict[str, Any]) -> None:
    """백그라운드 분석 결과 처리"""
    # ... TODO 생성 ...
    
    # 증분 모드일 때만 TODO 생성 알림 표시
    if incremental_mode and len(todos) > 0:
        self._show_todo_creation_notification(len(todos))

def _show_todo_creation_notification(self, todo_count: int):
    """TODO 생성 완료 알림 표시"""
    # QMessageBox 생성 및 표시
```

---

## 사용 시나리오

### 시나리오 1: 새 이메일 도착

```
1. VDOS에서 새 이메일 3개 생성
   ↓
2. 폴링 워커가 감지 (30초 간격)
   ↓
3. 📬 알림: "총 메시지 3개, 예상 TODO 2개"
   ↓
4. LLM 분석 (약 10초)
   ↓
5. ✅ 알림: "생성된 TODO 1개"
   (실제로는 1개만 action_required=true)
```

### 시나리오 2: 대량 메시지 수집

```
1. VDOS에서 새 메시지 50개 생성
   ↓
2. 폴링 워커가 감지
   ↓
3. 📬 알림: "총 메시지 50개, 예상 TODO 25개"
   ↓
4. LLM 분석 (약 60초, 상위 70개만)
   ↓
5. ✅ 알림: "생성된 TODO 12개"
```

### 시나리오 3: 정보성 메시지만 도착

```
1. VDOS에서 새 메시지 5개 생성 (모두 정보 공유)
   ↓
2. 폴링 워커가 감지
   ↓
3. 📬 알림: "총 메시지 5개, 예상 TODO 0개"
   (액션 키워드 없음)
   ↓
4. LLM 분석
   ↓
5. ✅ 알림 없음 (TODO 생성 안 됨)
```

---

## 스타일링

### 팝업 디자인

```css
QMessageBox {
    background-color: white;
}

QLabel {
    color: #333;
    min-width: 300px;
}

QPushButton {
    background-color: #4CAF50;  /* 녹색 */
    color: white;
    border: none;
    padding: 8px 20px;
    border-radius: 4px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #45a049;  /* 진한 녹색 */
}
```

### HTML 메시지 포맷

```html
<div style='font-size: 14px;'>
<p><b>새로운 메시지가 수집되었습니다!</b></p>
<br>
<table style='width: 100%;'>
<tr>
    <td style='padding: 5px;'>📧 총 메시지:</td>
    <td style='padding: 5px; text-align: right;'><b>15개</b></td>
</tr>
<tr>
    <td style='padding: 5px;'>✅ 예상 TODO:</td>
    <td style='padding: 5px; text-align: right;'><b>8개</b></td>
</tr>
</table>
<br>
<p style='color: #666; font-size: 12px;'>
※ TODO는 LLM 분석 후 자동으로 생성됩니다
</p>
</div>
```

---

## 설정 옵션

### 폴링 간격 조정

```python
# 기본값: 30초
polling_worker.set_polling_interval(30)

# 더 빠른 알림을 원하면 간격 단축
polling_worker.set_polling_interval(10)  # 10초
```

### 알림 자동 닫기 시간 조정

```python
# 기본값: 3초
QTimer.singleShot(3000, msg_box.close)

# 더 오래 표시하려면
QTimer.singleShot(5000, msg_box.close)  # 5초
```

### 알림 비활성화

```python
# _show_new_data_notification 메서드에서
if not self.enable_notifications:  # 설정 추가
    return
```

---

## 로그 메시지

### 새 데이터 수집 시

```
📬 새 데이터 수신: 메일 10개, 메시지 5개
📬 알림 표시: 메시지 15개, TODO 8개
```

### TODO 생성 완료 시

```
✅ 백그라운드 분석 완료: 5개 TODO 생성
✅ TODO 생성 알림 표시: 5개
```

---

## 주의사항

### 1. 비모달 팝업

```python
# show() 사용 (비모달)
msg_box.show()

# exec() 사용 금지 (모달, 백그라운드 작업 차단)
# msg_box.exec()  ❌
```

### 2. 자동 닫기

```python
# 3초 후 자동 닫기
QTimer.singleShot(3000, msg_box.close)

# 사용자가 OK 버튼을 누르면 즉시 닫힘
```

### 3. 예상 vs 실제 TODO 개수

```
예상 TODO: 키워드 기반 추정 (빠름, 부정확)
실제 TODO: LLM 분석 후 (느림, 정확)

→ 두 개수가 다를 수 있음
→ 사용자에게 명확히 안내
```

---

## 개선 방향

### 1. 알림 히스토리

```python
# 알림 히스토리 저장
notification_history = []

def _show_notification(self, ...):
    notification_history.append({
        "timestamp": datetime.now(),
        "type": "new_data",
        "message_count": total_messages,
        "todo_count": estimated_todos
    })
```

### 2. 알림 설정 UI

```python
# 설정 다이얼로그 추가
- [ ] 새 데이터 알림 활성화
- [ ] TODO 생성 알림 활성화
- 알림 표시 시간: [3]초
- 폴링 간격: [30]초
```

### 3. 사운드 알림

```python
from PyQt6.QtMultimedia import QSoundEffect

def _play_notification_sound(self):
    sound = QSoundEffect()
    sound.setSource(QUrl.fromLocalFile("notification.wav"))
    sound.play()
```

### 4. 시스템 트레이 알림

```python
from PyQt6.QtWidgets import QSystemTrayIcon

def _show_tray_notification(self, title, message):
    self.tray_icon.showMessage(
        title,
        message,
        QSystemTrayIcon.MessageIcon.Information,
        3000  # 3초
    )
```
