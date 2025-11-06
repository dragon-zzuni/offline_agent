# 시뮬레이션 상태 패널 개선

## 개요

Task 14에서 구현된 시뮬레이션 상태 패널 개선 사항을 설명합니다.

## 구현 내용

### 14.1 상세 상태 정보 표시

**목표**: 현재 틱, 시뮬레이션 시간, 실행 상태를 더 명확하게 표시하고 아이콘 및 색상을 사용하여 시각적 가독성을 향상시킵니다.

#### 구현 사항

1. **실행 상태 표시 레이블** (`sim_running_status`)
   - 실행 중: 🟢 실행 중 (녹색 배경)
   - 정지됨: 🔴 정지됨 (빨강 배경)
   - 연결 대기: ⚪ 연결 대기 중 (회색 배경)

2. **상세 정보 표시** (`sim_status_display`)
   - 🕐 Tick: 현재 틱 번호 (천 단위 구분자 포함)
   - 📅 시간: 시뮬레이션 시간 (ISO 8601 형식)
   - ✅/⏸️ 자동 틱: 활성화/비활성화 상태

3. **색상 구분**
   - 실행 중: 녹색 계열 (#D1FAE5, #10B981)
   - 정지됨: 회색 계열 (#F9FAFB, #E5E7EB)
   - 오류: 빨강 계열 (#FEE2E2, #EF4444)

#### 코드 예시

```python
# 실행 상태 표시
self.sim_running_status = QLabel("⚪ 연결 대기 중")
self.sim_running_status.setStyleSheet("""
    QLabel {
        color: #6B7280;
        background-color: #F3F4F6;
        padding: 6px 10px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 12px;
    }
""")

# 상세 정보 표시
self.sim_status_display = QLabel("연결 후 표시됩니다")
self.sim_status_display.setStyleSheet("""
    QLabel {
        color: #374151;
        background-color: #F9FAFB;
        padding: 8px;
        border-radius: 4px;
        border: 1px solid #E5E7EB;
        font-size: 11px;
        font-family: 'Consolas', 'Monaco', monospace;
    }
""")
```

### 14.2 진행률 바 추가

**목표**: 시뮬레이션 전체 진행률을 시각적으로 표시합니다.

#### 구현 사항

1. **진행률 바** (`sim_progress_bar`)
   - 현재 틱 수를 값으로 표시
   - 천 단위 구분자 포함 (예: "Tick: 1,500")
   - 동적 최대값 조정 (현재 틱의 1.2배)

2. **색상 구분**
   - 실행 중: 녹색 그라데이션 (#10B981 → #059669)
   - 정지됨: 회색 그라데이션 (#9CA3AF → #6B7280)

3. **동적 최대값 조정**
   - 현재 틱이 최대값을 초과하면 자동으로 최대값을 증가
   - 최대값 = 현재 틱 × 1.2

#### 코드 예시

```python
# 진행률 바 생성
from PyQt6.QtWidgets import QProgressBar

self.sim_progress_bar = QProgressBar()
self.sim_progress_bar.setTextVisible(True)
self.sim_progress_bar.setFormat("Tick: %v")
self.sim_progress_bar.setMinimum(0)
self.sim_progress_bar.setMaximum(10000)
self.sim_progress_bar.setValue(0)
self.sim_progress_bar.setStyleSheet("""
    QProgressBar {
        border: 1px solid #D1D5DB;
        border-radius: 4px;
        background-color: #F3F4F6;
        text-align: center;
        height: 20px;
        font-size: 11px;
        font-weight: 600;
    }
    QProgressBar::chunk {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #3B82F6, stop:1 #2563EB);
        border-radius: 3px;
    }
""")

# 상태 업데이트 시 진행률 바 업데이트
def on_sim_status_updated(self, status: dict):
    current_tick = status['current_tick']
    
    # 동적 최대값 조정
    if current_tick > self.sim_progress_bar.maximum():
        self.sim_progress_bar.setMaximum(int(current_tick * 1.2))
    
    # 값 및 포맷 업데이트
    self.sim_progress_bar.setValue(current_tick)
    self.sim_progress_bar.setFormat(f"Tick: {current_tick:,}")
```

## 상태 업데이트 로직

### on_sim_status_updated() 메서드

시뮬레이션 상태가 업데이트될 때 호출되는 핸들러입니다.

```python
def on_sim_status_updated(self, status: dict):
    """시뮬레이션 상태 업데이트 핸들러
    
    Args:
        status: {
            "current_tick": int,
            "sim_time": str,
            "is_running": bool,
            "auto_tick": bool
        }
    """
    current_tick = status['current_tick']
    
    # 1. 실행 상태 표시 업데이트
    if status['is_running']:
        self.sim_running_status.setText("🟢 실행 중")
        # 녹색 스타일 적용
    else:
        self.sim_running_status.setText("🔴 정지됨")
        # 빨강 스타일 적용
    
    # 2. 진행률 바 업데이트
    if current_tick > self.sim_progress_bar.maximum():
        self.sim_progress_bar.setMaximum(int(current_tick * 1.2))
    self.sim_progress_bar.setValue(current_tick)
    self.sim_progress_bar.setFormat(f"Tick: {current_tick:,}")
    
    # 3. 상세 정보 업데이트
    auto_tick_icon = "✅" if status['auto_tick'] else "⏸️"
    status_text = (
        f"🕐 Tick: {current_tick:,}\n"
        f"📅 시간: {status['sim_time']}\n"
        f"{auto_tick_icon} 자동 틱: {'활성화' if status['auto_tick'] else '비활성화'}"
    )
    self.sim_status_display.setText(status_text)
    
    # 4. 폴링 간격 조정
    if self.polling_worker:
        if status['is_running']:
            self.polling_worker.set_polling_interval(5)
        else:
            self.polling_worker.set_polling_interval(10)
```

## UI 레이아웃

```
┌─────────────────────────────────────┐
│ 🌐 VirtualOffice 연동               │
├─────────────────────────────────────┤
│ [데이터 소스 선택]                  │
│ [서버 URL 설정]                     │
│ [연결 버튼]                         │
│                                     │
│ 시뮬레이션 상태:                    │
│ ┌─────────────────────────────────┐ │
│ │ 🟢 실행 중                      │ │ ← 실행 상태 표시
│ ├─────────────────────────────────┤ │
│ │ [████████████░░░░░░] Tick: 1,500│ │ ← 진행률 바
│ ├─────────────────────────────────┤ │
│ │ 🕐 Tick: 1,500                  │ │
│ │ 📅 시간: 2025-11-26T10:30:00Z   │ │ ← 상세 정보
│ │ ✅ 자동 틱: 활성화              │ │
│ └─────────────────────────────────┘ │
│                                     │
│ [📊 틱 히스토리 보기]               │
└─────────────────────────────────────┘
```

## 시각적 검증

구현된 기능을 시각적으로 검증하려면 다음 스크립트를 실행하세요:

```bash
python offline_agent/test_sim_status_visual.py
```

### 검증 체크리스트

- [ ] 실행 상태 아이콘이 변경되는가? (🟢/🔴)
- [ ] 실행 상태에 따라 색상이 변경되는가?
- [ ] 진행률 바가 틱 값을 표시하는가?
- [ ] 진행률 바 색상이 상태에 따라 변경되는가?
- [ ] 상세 정보에 아이콘이 표시되는가?
- [ ] 천 단위 구분자가 표시되는가? (1,000)
- [ ] 큰 틱 값에서 진행률 바가 자동 조정되는가?

## 관련 요구사항

- **Requirement 3.2**: 현재 틱 번호를 UI에 표시
- **Requirement 3.3**: 시뮬레이션 시간을 UI에 표시
- **Requirement 3.4**: 시뮬레이션 실행 상태를 UI에 표시

## 참고 자료

- [PyQt6 QProgressBar 문서](https://doc.qt.io/qt-6/qprogressbar.html)
- [PyQt6 QLabel 문서](https://doc.qt.io/qt-6/qlabel.html)
- [CSS 색상 팔레트](https://tailwindcss.com/docs/customizing-colors)
