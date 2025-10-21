# -*- coding: utf-8 -*-
"""
UI 스타일 및 색상 팔레트

Smart Assistant 전체 UI에서 사용하는 일관된 색상 팔레트와 스타일을 정의합니다.
"""

# ============================================================================
# 색상 팔레트 (Tailwind CSS 기반)
# ============================================================================

class Colors:
    """색상 팔레트 정의"""
    
    # Primary Colors (브랜드 색상)
    PRIMARY = "#8B5CF6"  # Purple-500
    PRIMARY_DARK = "#7C3AED"  # Purple-600
    PRIMARY_LIGHT = "#A78BFA"  # Purple-400
    PRIMARY_BG = "#F5F3FF"  # Purple-50
    
    # Secondary Colors
    SECONDARY = "#3B82F6"  # Blue-500
    SECONDARY_DARK = "#2563EB"  # Blue-600
    SECONDARY_LIGHT = "#60A5FA"  # Blue-400
    SECONDARY_BG = "#EFF6FF"  # Blue-50
    
    # Success Colors
    SUCCESS = "#10B981"  # Green-500
    SUCCESS_DARK = "#059669"  # Green-600
    SUCCESS_LIGHT = "#34D399"  # Green-400
    SUCCESS_BG = "#ECFDF5"  # Green-50
    
    # Warning Colors
    WARNING = "#F59E0B"  # Amber-500
    WARNING_DARK = "#D97706"  # Amber-600
    WARNING_LIGHT = "#FBBF24"  # Amber-400
    WARNING_BG = "#FFFBEB"  # Amber-50
    
    # Danger Colors
    DANGER = "#EF4444"  # Red-500
    DANGER_DARK = "#DC2626"  # Red-600
    DANGER_LIGHT = "#F87171"  # Red-400
    DANGER_BG = "#FEF2F2"  # Red-50
    
    # Neutral Colors (Gray Scale)
    GRAY_50 = "#F9FAFB"
    GRAY_100 = "#F3F4F6"
    GRAY_200 = "#E5E7EB"
    GRAY_300 = "#D1D5DB"
    GRAY_400 = "#9CA3AF"
    GRAY_500 = "#6B7280"
    GRAY_600 = "#4B5563"
    GRAY_700 = "#374151"
    GRAY_800 = "#1F2937"
    GRAY_900 = "#111827"
    
    # Text Colors
    TEXT_PRIMARY = "#111827"  # Gray-900
    TEXT_SECONDARY = "#4B5563"  # Gray-600
    TEXT_TERTIARY = "#6B7280"  # Gray-500
    TEXT_DISABLED = "#9CA3AF"  # Gray-400
    
    # Background Colors
    BG_PRIMARY = "#FFFFFF"
    BG_SECONDARY = "#F9FAFB"  # Gray-50
    BG_TERTIARY = "#F3F4F6"  # Gray-100
    
    # Border Colors
    BORDER_LIGHT = "#E5E7EB"  # Gray-200
    BORDER_MEDIUM = "#D1D5DB"  # Gray-300
    BORDER_DARK = "#9CA3AF"  # Gray-400
    
    # Priority Colors
    PRIORITY_HIGH_BG = "#FEE2E2"  # Red-100
    PRIORITY_HIGH_TEXT = "#991B1B"  # Red-800
    PRIORITY_MEDIUM_BG = "#FEF3C7"  # Yellow-100
    PRIORITY_MEDIUM_TEXT = "#92400E"  # Yellow-800
    PRIORITY_LOW_BG = "#E5E7EB"  # Gray-200
    PRIORITY_LOW_TEXT = "#374151"  # Gray-700


# ============================================================================
# 폰트 스타일
# ============================================================================

class FontSizes:
    """폰트 크기 정의"""
    XS = "11px"
    SM = "12px"
    BASE = "14px"
    LG = "16px"
    XL = "18px"
    XXL = "20px"
    XXXL = "24px"


class FontWeights:
    """폰트 굵기 정의"""
    NORMAL = "400"
    MEDIUM = "500"
    SEMIBOLD = "600"
    BOLD = "700"
    EXTRABOLD = "800"


class Fonts:
    """Qt 위젯 및 CSS에서 사용할 폰트 설정"""
    # 주요 폰트 패밀리 (설치되지 않은 경우 시스템 기본 폰트로 대체됨)
    FAMILY = "Pretendard"
    FALLBACK_FAMILY = "Noto Sans KR"
    
    # QFont 생성 등에 사용할 정수 사이즈 (px 기준)
    SIZE_XS = 11
    SIZE_SM = 12
    SIZE_BASE = 14
    SIZE_MD = 15
    SIZE_LG = 16
    SIZE_XL = 18
    SIZE_XXL = 20
    SIZE_XXXL = 24
    
    @staticmethod
    def to_points(size: str) -> int:
        """FontSizes 값(px 문자열)을 정수 포인트로 변환"""
        if isinstance(size, str) and size.endswith("px"):
            try:
                return int(size[:-2])
            except ValueError:
                pass
        return int(size)


# ============================================================================
# 간격 및 여백
# ============================================================================

class Spacing:
    """간격 및 여백 정의"""
    XS = 4
    SM = 8
    BASE = 12
    MD = 16
    LG = 20
    XL = 24
    XXL = 32


class BorderRadius:
    """테두리 반경 정의"""
    SM = "4px"
    BASE = "6px"
    MD = "8px"
    LG = "12px"
    FULL = "9999px"


# ============================================================================
# 공통 스타일 문자열
# ============================================================================

class Styles:
    """재사용 가능한 스타일 문자열"""
    
    @staticmethod
    def button_primary() -> str:
        """Primary 버튼 스타일"""
        return f"""
            QPushButton {{
                background-color: {Colors.PRIMARY};
                color: white;
                border: none;
                padding: 10px 16px;
                border-radius: 6px;
                font-weight: {FontWeights.SEMIBOLD};
                font-size: {FontSizes.BASE};
            }}
            QPushButton:hover {{
                background-color: {Colors.PRIMARY_DARK};
            }}
            QPushButton:pressed {{
                background-color: {Colors.PRIMARY_DARK};
            }}
            QPushButton:disabled {{
                background-color: {Colors.GRAY_300};
                color: {Colors.GRAY_500};
            }}
        """
    
    @staticmethod
    def button_secondary() -> str:
        """Secondary 버튼 스타일"""
        return f"""
            QPushButton {{
                background-color: {Colors.SECONDARY};
                color: white;
                border: none;
                padding: 10px 16px;
                border-radius: 6px;
                font-weight: {FontWeights.SEMIBOLD};
                font-size: {FontSizes.BASE};
            }}
            QPushButton:hover {{
                background-color: {Colors.SECONDARY_DARK};
            }}
            QPushButton:pressed {{
                background-color: {Colors.SECONDARY_DARK};
            }}
            QPushButton:disabled {{
                background-color: {Colors.GRAY_300};
                color: {Colors.GRAY_500};
            }}
        """
    
    @staticmethod
    def button_success() -> str:
        """Success 버튼 스타일"""
        return f"""
            QPushButton {{
                background-color: {Colors.SUCCESS};
                color: white;
                border: none;
                padding: 10px 16px;
                border-radius: 6px;
                font-weight: {FontWeights.SEMIBOLD};
                font-size: {FontSizes.BASE};
            }}
            QPushButton:hover {{
                background-color: {Colors.SUCCESS_DARK};
            }}
            QPushButton:pressed {{
                background-color: {Colors.SUCCESS_DARK};
            }}
            QPushButton:disabled {{
                background-color: {Colors.GRAY_300};
                color: {Colors.GRAY_500};
            }}
        """
    
    @staticmethod
    def button_warning() -> str:
        """Warning 버튼 스타일"""
        return f"""
            QPushButton {{
                background-color: {Colors.WARNING};
                color: white;
                border: none;
                padding: 10px 16px;
                border-radius: 6px;
                font-weight: {FontWeights.SEMIBOLD};
                font-size: {FontSizes.BASE};
            }}
            QPushButton:hover {{
                background-color: {Colors.WARNING_DARK};
            }}
            QPushButton:pressed {{
                background-color: {Colors.WARNING_DARK};
            }}
            QPushButton:disabled {{
                background-color: {Colors.GRAY_300};
                color: {Colors.GRAY_500};
            }}
        """
    
    @staticmethod
    def button_danger() -> str:
        """Danger 버튼 스타일"""
        return f"""
            QPushButton {{
                background-color: {Colors.DANGER};
                color: white;
                border: none;
                padding: 10px 16px;
                border-radius: 6px;
                font-weight: {FontWeights.SEMIBOLD};
                font-size: {FontSizes.BASE};
            }}
            QPushButton:hover {{
                background-color: {Colors.DANGER_DARK};
            }}
            QPushButton:pressed {{
                background-color: {Colors.DANGER_DARK};
            }}
            QPushButton:disabled {{
                background-color: {Colors.GRAY_300};
                color: {Colors.GRAY_500};
            }}
        """
    
    @staticmethod
    def card() -> str:
        """카드 스타일"""
        return f"""
            QFrame {{
                background-color: {Colors.BG_PRIMARY};
                border: 1px solid {Colors.BORDER_LIGHT};
                border-radius: 8px;
                padding: 16px;
            }}
            QFrame:hover {{
                border-color: {Colors.BORDER_MEDIUM};
                background-color: {Colors.GRAY_50};
            }}
        """
    
    @staticmethod
    def group_box() -> str:
        """그룹 박스 스타일"""
        return f"""
            QGroupBox {{
                background-color: {Colors.BG_PRIMARY};
                border: 1px solid {Colors.BORDER_LIGHT};
                border-radius: 8px;
                padding: 16px;
                margin-top: 12px;
                font-weight: {FontWeights.SEMIBOLD};
                font-size: {FontSizes.BASE};
                color: {Colors.TEXT_PRIMARY};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                background-color: {Colors.BG_PRIMARY};
            }}
        """
    
    @staticmethod
    def badge(bg_color: str, text_color: str) -> str:
        """배지 스타일"""
        return f"""
            QLabel {{
                background-color: {bg_color};
                color: {text_color};
                padding: 4px 12px;
                border-radius: 12px;
                font-size: {FontSizes.XS};
                font-weight: {FontWeights.SEMIBOLD};
            }}
        """
    
    @staticmethod
    def heading_1() -> str:
        """H1 제목 스타일"""
        return f"""
            QLabel {{
                font-size: {FontSizes.XXXL};
                font-weight: {FontWeights.BOLD};
                color: {Colors.TEXT_PRIMARY};
                margin: 8px 0;
            }}
        """
    
    @staticmethod
    def heading_2() -> str:
        """H2 제목 스타일"""
        return f"""
            QLabel {{
                font-size: {FontSizes.XXL};
                font-weight: {FontWeights.BOLD};
                color: {Colors.TEXT_PRIMARY};
                margin: 6px 0;
            }}
        """
    
    @staticmethod
    def heading_3() -> str:
        """H3 제목 스타일"""
        return f"""
            QLabel {{
                font-size: {FontSizes.XL};
                font-weight: {FontWeights.SEMIBOLD};
                color: {Colors.TEXT_PRIMARY};
                margin: 4px 0;
            }}
        """
    
    @staticmethod
    def body_text() -> str:
        """본문 텍스트 스타일"""
        return f"""
            QLabel {{
                font-size: {FontSizes.BASE};
                font-weight: {FontWeights.NORMAL};
                color: {Colors.TEXT_SECONDARY};
                line-height: 1.5;
            }}
        """
    
    @staticmethod
    def small_text() -> str:
        """작은 텍스트 스타일"""
        return f"""
            QLabel {{
                font-size: {FontSizes.SM};
                font-weight: {FontWeights.NORMAL};
                color: {Colors.TEXT_TERTIARY};
            }}
        """


# ============================================================================
# 우선순위별 스타일 헬퍼
# ============================================================================

def get_priority_colors(priority: str) -> tuple[str, str]:
    """우선순위에 따른 배경색과 텍스트 색상 반환
    
    Args:
        priority: 우선순위 ("high", "medium", "low")
        
    Returns:
        (배경색, 텍스트색) 튜플
    """
    priority_lower = priority.lower() if priority else "low"
    
    if priority_lower == "high":
        return (Colors.PRIORITY_HIGH_BG, Colors.PRIORITY_HIGH_TEXT)
    elif priority_lower == "medium":
        return (Colors.PRIORITY_MEDIUM_BG, Colors.PRIORITY_MEDIUM_TEXT)
    else:
        return (Colors.PRIORITY_LOW_BG, Colors.PRIORITY_LOW_TEXT)


def get_priority_badge_style(priority: str) -> str:
    """우선순위 배지 스타일 반환
    
    Args:
        priority: 우선순위 ("high", "medium", "low")
        
    Returns:
        CSS 스타일 문자열
    """
    bg_color, text_color = get_priority_colors(priority)
    return Styles.badge(bg_color, text_color)


# ============================================================================
# 아이콘 및 이모지 헬퍼
# ============================================================================

class Icons:
    """아이콘 및 이모지 정의"""
    
    # 우선순위 아이콘
    PRIORITY_HIGH = "🔴"
    PRIORITY_MEDIUM = "🟡"
    PRIORITY_LOW = "⚪"
    
    # 메시지 타입 아이콘
    EMAIL = "📧"
    MESSENGER = "💬"
    MESSAGE = "📨"
    
    # 상태 아이콘
    DONE = "✅"
    PENDING = "⏳"
    SNOOZED = "😴"
    IN_PROGRESS = "🔄"
    
    # 액션 아이콘
    SEND = "📤"
    REPLY = "↩️"
    FORWARD = "➡️"
    DELETE = "🗑️"
    EDIT = "✏️"
    SAVE = "💾"
    
    # 정보 아이콘
    INFO = "ℹ️"
    WARNING = "⚠️"
    ERROR = "❌"
    SUCCESS = "✔️"
    
    # 시간 관련 아이콘
    CALENDAR = "📅"
    CLOCK = "🕐"
    DEADLINE = "⏰"
    
    # 기타 아이콘
    STAR = "⭐"
    FIRE = "🔥"
    CHART = "📊"
    SEARCH = "🔍"
    SETTINGS = "⚙️"
    USER = "👤"
    TEAM = "👥"
    FOLDER = "📁"
    FILE = "📄"
    LINK = "🔗"
    TAG = "🏷️"


def get_priority_icon(priority: str) -> str:
    """우선순위에 따른 아이콘 반환
    
    Args:
        priority: 우선순위 ("high", "medium", "low")
        
    Returns:
        아이콘 문자열
    """
    priority_lower = priority.lower() if priority else "low"
    
    if priority_lower == "high":
        return Icons.PRIORITY_HIGH
    elif priority_lower == "medium":
        return Icons.PRIORITY_MEDIUM
    else:
        return Icons.PRIORITY_LOW


def get_message_type_icon(msg_type: str) -> str:
    """메시지 타입에 따른 아이콘 반환
    
    Args:
        msg_type: 메시지 타입 ("email", "messenger", "chat" 등)
        
    Returns:
        아이콘 문자열
    """
    msg_type_lower = msg_type.lower() if msg_type else ""
    
    if "email" in msg_type_lower or "mail" in msg_type_lower:
        return Icons.EMAIL
    elif "messenger" in msg_type_lower or "chat" in msg_type_lower or "message" in msg_type_lower:
        return Icons.MESSENGER
    else:
        return Icons.MESSAGE


def get_status_icon(status: str) -> str:
    """상태에 따른 아이콘 반환
    
    Args:
        status: 상태 ("done", "pending", "snoozed", "in_progress" 등)
        
    Returns:
        아이콘 문자열
    """
    status_lower = status.lower() if status else "pending"
    
    if status_lower == "done":
        return Icons.DONE
    elif status_lower == "snoozed":
        return Icons.SNOOZED
    elif status_lower in ["in_progress", "working"]:
        return Icons.IN_PROGRESS
    else:
        return Icons.PENDING


def create_badge_html(text: str, bg_color: str, text_color: str, icon: str = "") -> str:
    """HTML 형식의 배지 생성
    
    Args:
        text: 배지 텍스트
        bg_color: 배경색
        text_color: 텍스트 색상
        icon: 선택적 아이콘
        
    Returns:
        HTML 문자열
    """
    icon_part = f"{icon} " if icon else ""
    return f'<span style="background-color: {bg_color}; color: {text_color}; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 600;">{icon_part}{text}</span>'


def create_priority_badge_html(priority: str) -> str:
    """우선순위 배지 HTML 생성
    
    Args:
        priority: 우선순위 ("high", "medium", "low")
        
    Returns:
        HTML 문자열
    """
    bg_color, text_color = get_priority_colors(priority)
    icon = get_priority_icon(priority)
    priority_text = {"high": "High", "medium": "Medium", "low": "Low"}.get(priority.lower(), priority)
    
    return create_badge_html(priority_text, bg_color, text_color, icon)
