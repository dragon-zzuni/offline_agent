# 알람 효과 렉 문제 해결

## 문제 상황
- 알람 상태에서 GUI가 멈추거나 렉이 걸림
- 특히 여러 패널에 동시에 알람이 표시될 때 심각

## 원인 분석

### 1. 중복 위젯 등록
```python
# 문제 코드 (매번 등록)
self.notification_manager.register_widget(self.email_panel, "visual")
self.notification_manager.show_notification(self.email_panel, duration_ms=500)
```
- `_update_ui_for_new_data` 호출 시마다 위젯을 다시 등록
- 메모리 누수 및 성능 저하 발생

### 2. QGraphicsOpacityEffect 사용
```python
# 문제 코드 (무거운 그래픽 효과)
opacity_effect = QGraphicsOpacityEffect(self.widget)
self.widget.setGraphicsEffect(opacity_effect)
animation = QPropertyAnimation(opacity_effect, b"opacity")
```
- `QGraphicsOpacityEffect`는 GPU 렌더링을 사용하여 무거움
- 여러 위젯에 동시 적용 시 렉 발생

### 3. 중복 알람 실행
- 이미 알람이 실행 중인데 새 알람이 시작됨
- 타이머가 중첩되어 실행

## 해결 방법

### 1. 위젯 등록 최적화
```python
# 수정 후 (초기화 시 1회만 등록)
if not self._widgets_registered:
    if hasattr(self, 'message_summary_panel'):
        self.notification_manager.register_widget(self.message_summary_panel, "visual")
    if hasattr(self, 'email_panel'):
        self.notification_manager.register_widget(self.email_panel, "visual")
    self._widgets_registered = True

# 알람만 표시
self.notification_manager.show_notification(self.email_panel, duration_ms=300)
```

### 2. 경량화된 알람 효과
```python
# 수정 후 (단순 스타일 변경)
notification_style = self.original_style + """
    QWidget {
        background-color: #EFF6FF;
        border: 1px solid #BFDBFE;
    }
"""
self.widget.setStyleSheet(notification_style)
```
- `QGraphicsOpacityEffect` 제거
- 단순 CSS 스타일 변경으로 대체
- 훨씬 가볍고 빠름

### 3. 중복 알람 방지
```python
# 수정 후 (이미 실행 중이면 무시)
if self.notification_timer and self.notification_timer.isActive():
    self.notification_timer.stop()
    self._restore_style()
    return  # 이미 알람 중이면 새 알람 무시
```

### 4. 알람 시간 단축
```python
# 수정 전: 500ms
self.notification_manager.show_notification(widget, duration_ms=500)

# 수정 후: 300ms (더 빠르게)
self.notification_manager.show_notification(widget, duration_ms=300)
```

## 수정된 파일

1. **offline_agent/src/ui/main_window.py**
   - `_init_ui_components`: 위젯 등록 추적 변수 추가
   - `_update_ui_for_new_data`: 위젯 등록 최적화, 알람 시간 단축

2. **offline_agent/src/ui/visual_notification.py**
   - `VisualNotification.show_notification`: 중복 알람 방지, 스타일 경량화
   - `PulseAnimation`: QGraphicsOpacityEffect 제거, 단순 스타일 변경으로 대체
   - Import 정리: 불필요한 모듈 제거

## 성능 개선 효과

- ✅ 알람 효과 실행 시 렉 제거
- ✅ 메모리 사용량 감소
- ✅ CPU 사용률 감소
- ✅ 더 부드러운 UI 반응

## 테스트 방법

1. 앱 실행
2. VirtualOffice 연결 및 데이터 수집
3. 여러 패널에서 알람 효과 확인
4. GUI가 멈추지 않고 부드럽게 동작하는지 확인

## 추가 최적화 가능 사항

1. **알람 효과 완전 비활성화 옵션**
   - 설정에서 알람 효과 끄기 기능 추가
   
2. **알람 효과 강도 조절**
   - 사용자가 알람 시간 및 색상 조절 가능

3. **배치 알람**
   - 여러 패널에 동시 알람 대신 순차적으로 표시
