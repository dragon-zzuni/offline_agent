# UI 스타일 시스템 가이드

## 개요

`ui/styles.py`는 Smart Assistant 전체 UI에서 사용하는 일관된 디자인 시스템을 제공합니다. Tailwind CSS 기반의 색상 팔레트와 재사용 가능한 스타일 컴포넌트를 정의하여 UI 일관성을 보장합니다.

## 주요 구성 요소

### 1. 색상 팔레트 (Colors)

#### 브랜드 색상
```python
from ui.styles import Colors

# Primary (보라색 - 브랜드 색상)
Colors.PRIMARY          # #8B5CF6
Colors.PRIMARY_DARK     # #7C3AED
Colors.PRIMARY_LIGHT    # #A78BFA
Colors.PRIMARY_BG       # #F5F3FF

# Secondary (파란색)
Colors.SECONDARY        # #3B82F6
Colors.SECONDARY_DARK   # #2563EB
Colors.SECONDARY_LIGHT  # #60A5FA
Colors.SECONDARY_BG     # #EFF6FF
```

#### 상태 색상
```python
# Success (녹색)
Colors.SUCCESS          # #10B981
Colors.SUCCESS_DARK     # #059669
Colors.SUCCESS_BG       # #ECFDF5

# Warning (주황색)
Colors.WARNING          # #F59E0B
Colors.WARNING_DARK     # #D97706
Colors.WARNING_BG       # #FFFBEB

# Danger (빨간색)
Colors.DANGER           # #EF4444
Colors.DANGER_DARK      # #DC2626
Colors.DANGER_BG        # #FEF2F2
```

#### 중립 색상 (Gray Scale)
```python
Colors.GRAY_50          # #F9FAFB (가장 밝음)
Colors.GRAY_100         # #F3F4F6
Colors.GRAY_200         # #E5E7EB
Colors.GRAY_300         # #D1D5DB
Colors.GRAY_400         # #9CA3AF
Colors.GRAY_500         # #6B7280
Colors.GRAY_600         # #4B5563
Colors.GRAY_700         # #374151
Colors.GRAY_800         # #1F2937
Colors.GRAY_900         # #111827 (가장 어두움)
```

#### 텍스트 색상
```python
Colors.TEXT_PRIMARY     # #111827 (본문)
Colors.TEXT_SECONDARY   # #4B5563 (보조)
Colors.TEXT_TERTIARY    # #6B7280 (부가)
Colors.TEXT_DISABLED    # #9CA3AF (비활성)
```

#### 우선순위 색상
```python
# High Priority (빨간색)
Colors.PRIORITY_HIGH_BG     # #FEE2E2
Colors.PRIORITY_HIGH_TEXT   # #991B1B

# Medium Priority (노란색)
Colors.PRIORITY_MEDIUM_BG   # #FEF3C7
Colors.PRIORITY_MEDIUM_TEXT # #92400E

# Low Priority (회색)
Colors.PRIORITY_LOW_BG      # #E5E7EB
Colors.PRIORITY_LOW_TEXT    # #374151
```

### 2. 폰트 스타일

#### 폰트 크기 (FontSizes)
```python
from ui.styles import FontSizes

FontSizes.XS      # 11px
FontSizes.SM      # 12px
FontSizes.BASE    # 14px (기본)
FontSizes.LG      # 16px
FontSizes.XL      # 18px
FontSizes.XXL     # 20px
FontSizes.XXXL    # 24px
```

#### 폰트 굵기 (FontWeights)
```python
from ui.styles import FontWeights

FontWeights.NORMAL      # 400
FontWeights.MEDIUM      # 500
FontWeights.SEMIBOLD    # 600
FontWeights.BOLD        # 700
FontWeights.EXTRABOLD   # 800
```

### 3. 간격 및 여백 (Spacing)

```python
from ui.styles import Spacing

Spacing.XS      # 4px
Spacing.SM      # 8px
Spacing.BASE    # 12px
Spacing.MD      # 16px
Spacing.LG      # 20px
Spacing.XL      # 24px
Spacing.XXL     # 32px
```

### 4. 테두리 반경 (BorderRadius)

```python
from ui.styles import BorderRadius

BorderRadius.SM     # 4px
BorderRadius.BASE   # 6px
BorderRadius.MD     # 8px
BorderRadius.LG     # 12px
BorderRadius.FULL   # 9999px (완전한 원)
```

## 재사용 가능한 스타일

### 버튼 스타일

```python
from ui.styles import Styles

# Primary 버튼 (보라색)
button.setStyleSheet(Styles.button_primary())

# Secondary 버튼 (파란색)
button.setStyleSheet(Styles.button_secondary())

# Success 버튼 (녹색)
button.setStyleSheet(Styles.button_success())

# Warning 버튼 (주황색)
button.setStyleSheet(Styles.button_warning())

# Danger 버튼 (빨간색)
button.setStyleSheet(Styles.button_danger())
```

### 카드 및 컨테이너

```python
# 카드 스타일
frame.setStyleSheet(Styles.card())

# 그룹 박스 스타일
group_box.setStyleSheet(Styles.group_box())
```

### 배지 스타일

```python
# 커스텀 배지
badge.setStyleSheet(Styles.badge("#FEE2E2", "#991B1B"))

# 우선순위 배지
from ui.styles import get_priority_badge_style
badge.setStyleSheet(get_priority_badge_style("high"))
```

### 제목 및 텍스트

```python
# H1 제목
heading.setStyleSheet(Styles.heading_1())

# H2 제목
heading.setStyleSheet(Styles.heading_2())

# H3 제목
heading.setStyleSheet(Styles.heading_3())

# 본문 텍스트
text.setStyleSheet(Styles.body_text())

# 작은 텍스트
small_text.setStyleSheet(Styles.small_text())
```

## 헬퍼 함수

### 우선순위 관련

```python
from ui.styles import get_priority_colors, get_priority_icon

# 우선순위 색상 가져오기
bg_color, text_color = get_priority_colors("high")

# 우선순위 아이콘 가져오기
icon = get_priority_icon("high")  # 🔴
```

### 아이콘

```python
from ui.styles import Icons, get_message_type_icon, get_status_icon

# 정적 아이콘
Icons.EMAIL         # 📧
Icons.MESSENGER     # 💬
Icons.DONE          # ✅
Icons.PENDING       # ⏳
Icons.CALENDAR      # 📅

# 동적 아이콘
email_icon = get_message_type_icon("email")      # 📧
chat_icon = get_message_type_icon("messenger")   # 💬
done_icon = get_status_icon("done")              # ✅
```

### HTML 배지 생성

```python
from ui.styles import create_badge_html, create_priority_badge_html

# 커스텀 HTML 배지
badge_html = create_badge_html("New", "#FEE2E2", "#991B1B", "🔥")

# 우선순위 HTML 배지
priority_html = create_priority_badge_html("high")
```

## 사용 예시

### 예시 1: 우선순위 배지가 있는 카드

```python
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel
from ui.styles import Colors, FontSizes, FontWeights, Spacing, get_priority_colors

card = QFrame()
card.setStyleSheet(f"""
    QFrame {{
        background-color: {Colors.BG_PRIMARY};
        border: 1px solid {Colors.BORDER_LIGHT};
        border-radius: 8px;
        padding: {Spacing.MD}px;
    }}
""")

layout = QVBoxLayout(card)

# 제목
title = QLabel("중요한 작업")
title.setStyleSheet(f"""
    font-size: {FontSizes.XL};
    font-weight: {FontWeights.BOLD};
    color: {Colors.TEXT_PRIMARY};
""")
layout.addWidget(title)

# 우선순위 배지
bg_color, text_color = get_priority_colors("high")
badge = QLabel("High")
badge.setStyleSheet(f"""
    background-color: {bg_color};
    color: {text_color};
    padding: 4px 12px;
    border-radius: 12px;
    font-size: {FontSizes.XS};
    font-weight: {FontWeights.SEMIBOLD};
""")
layout.addWidget(badge)
```

### 예시 2: 스타일 시스템을 사용한 버튼

```python
from PyQt6.QtWidgets import QPushButton
from ui.styles import Styles

# Primary 버튼
save_button = QPushButton("저장")
save_button.setStyleSheet(Styles.button_primary())

# Success 버튼
submit_button = QPushButton("제출")
submit_button.setStyleSheet(Styles.button_success())

# Danger 버튼
delete_button = QPushButton("삭제")
delete_button.setStyleSheet(Styles.button_danger())
```

### 예시 3: 메시지 요약 패널 스타일링

```python
from ui.styles import Colors, FontSizes, FontWeights, Spacing, Icons

# 요약 카드
summary_card = QFrame()
summary_card.setStyleSheet(f"""
    QFrame {{
        background-color: {Colors.BG_PRIMARY};
        border: 1px solid {Colors.BORDER_LIGHT};
        border-radius: 8px;
        padding: {Spacing.MD}px;
    }}
    QFrame:hover {{
        border-color: {Colors.BORDER_MEDIUM};
        background-color: {Colors.GRAY_50};
    }}
""")

# 아이콘과 텍스트
icon_label = QLabel(f"{Icons.EMAIL} 이메일")
icon_label.setStyleSheet(f"""
    font-size: {FontSizes.SM};
    color: {Colors.TEXT_SECONDARY};
    font-weight: {FontWeights.MEDIUM};
""")
```

## 디자인 원칙

### 1. 일관성
- 모든 UI 컴포넌트는 동일한 색상 팔레트를 사용합니다
- 간격과 여백은 Spacing 상수를 사용하여 일관성을 유지합니다
- 폰트 크기와 굵기는 정의된 상수를 사용합니다

### 2. 접근성
- 텍스트와 배경 간 충분한 대비를 유지합니다 (WCAG 2.1 AA 준수)
- 색상만으로 정보를 전달하지 않고 아이콘과 텍스트를 함께 사용합니다
- 비활성 상태는 명확하게 구분됩니다

### 3. 계층 구조
- Primary: 주요 액션 (저장, 제출 등)
- Secondary: 보조 액션 (취소, 닫기 등)
- Success: 긍정적 결과 (완료, 성공 등)
- Warning: 주의 필요 (경고, 확인 필요 등)
- Danger: 위험한 액션 (삭제, 제거 등)

### 4. 반응성
- 호버 상태에서 시각적 피드백 제공
- 클릭/누름 상태 표시
- 비활성 상태 명확히 구분

## 마이그레이션 가이드

기존 하드코딩된 스타일을 스타일 시스템으로 마이그레이션하는 방법:

### Before (하드코딩)
```python
button.setStyleSheet("""
    QPushButton {
        background-color: #8B5CF6;
        color: white;
        padding: 10px 16px;
        border-radius: 6px;
    }
""")
```

### After (스타일 시스템)
```python
from ui.styles import Styles

button.setStyleSheet(Styles.button_primary())
```

### 색상 상수 표준화 예시

#### Before (비표준 상수)
```python
from ui.styles import Colors

header.setStyleSheet(f"""
    QWidget {{
        background-color: {Colors.SURFACE};
        border-bottom: 1px solid {Colors.BORDER};
    }}
""")
```

#### After (표준 상수)
```python
from ui.styles import Colors

header.setStyleSheet(f"""
    QWidget {{
        background-color: {Colors.BG_SECONDARY};
        border-bottom: 1px solid {Colors.BORDER_LIGHT};
    }}
""")
```

**개선 사항:**
- `Colors.SURFACE` → `Colors.BG_SECONDARY`: 명확한 의미 전달
- `Colors.BORDER` → `Colors.BORDER_LIGHT`: 테두리 강도 명시
- 모든 UI 컴포넌트가 동일한 색상 팔레트 사용

## 향후 개선 사항

- [ ] 다크 모드 지원
- [ ] 테마 전환 기능
- [ ] 커스텀 테마 생성 도구
- [ ] 애니메이션 및 전환 효과
- [ ] 반응형 디자인 지원

## 관련 파일

- `ui/styles.py`: 스타일 시스템 구현
- `ui/message_summary_panel.py`: 스타일 시스템 사용 예시
- `ui/time_range_selector.py`: 스타일 시스템 사용 예시

## 참고 자료

- [Tailwind CSS 색상 팔레트](https://tailwindcss.com/docs/customizing-colors)
- [PyQt6 스타일시트 문서](https://doc.qt.io/qt-6/stylesheet.html)
- [Material Design 색상 시스템](https://material.io/design/color)
