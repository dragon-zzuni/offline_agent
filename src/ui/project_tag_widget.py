#!/usr/bin/env python3
"""
프로젝트 태그 위젯

프로젝트별 색상 태그를 표시하고 클릭을 통한 필터링 기능을 제공합니다.
"""

import hashlib
from typing import Optional, List, Callable
from PyQt6.QtWidgets import QLabel, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QFrame
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QPalette, QColor, QCursor

from .styles import Colors, FontSizes, FontWeights, Spacing, BorderRadius
import logging

logger = logging.getLogger(__name__)

class ProjectTagWidget(QLabel):
    """프로젝트 태그 위젯 클래스"""
    
    # 클릭 시그널 (프로젝트 ID 전달)
    clicked = pyqtSignal(int)
    
    # 12색 팔레트 (프로젝트별 고유 색상)
    COLOR_PALETTE = [
        ("#8B5CF6", "#FFFFFF"),  # Purple
        ("#3B82F6", "#FFFFFF"),  # Blue  
        ("#10B981", "#FFFFFF"),  # Green
        ("#F59E0B", "#FFFFFF"),  # Amber
        ("#EF4444", "#FFFFFF"),  # Red
        ("#8B5A2B", "#FFFFFF"),  # Brown
        ("#EC4899", "#FFFFFF"),  # Pink
        ("#06B6D4", "#FFFFFF"),  # Cyan
        ("#84CC16", "#FFFFFF"),  # Lime
        ("#F97316", "#FFFFFF"),  # Orange
        ("#6366F1", "#FFFFFF"),  # Indigo
        ("#14B8A6", "#FFFFFF"),  # Teal
    ]
    
    def __init__(self, project_id: int, project_name: str, short_name: str = "", parent: Optional[QWidget] = None):
        """
        프로젝트 태그 위젯 초기화
        
        Args:
            project_id: 프로젝트 ID
            project_name: 프로젝트 전체 이름
            short_name: 축약명 (비어있으면 자동 생성)
            parent: 부모 위젯
        """
        super().__init__(parent)
        
        self.project_id = project_id
        self.project_name = project_name
        self.short_name = short_name or self._generate_short_name(project_name)
        self.is_active = False
        
        # 색상 생성
        self.bg_color, self.text_color = self._generate_colors(project_name)
        
        # 위젯 설정
        self._setup_widget()
        
        logger.debug(f"프로젝트 태그 위젯 생성: {project_name} ({self.short_name})")
    
    def _generate_short_name(self, project_name: str) -> str:
        """프로젝트명에서 축약명 자동 생성"""
        import re
        
        # 영문 대문자와 한글 첫 글자 추출
        words = re.findall(r'[A-Z][a-z]*|[가-힣]+', project_name)
        
        if len(words) >= 2:
            # 여러 단어인 경우 각 단어의 첫 글자
            return ''.join(word[0].upper() if word[0].isalpha() else word[0] for word in words[:3])
        elif len(words) == 1:
            # 단일 단어인 경우 처음 3글자
            return words[0][:3].upper()
        else:
            # 특수 문자만 있는 경우 프로젝트 ID 사용
            return f"P{self.project_id}"
    
    def _generate_colors(self, project_name: str) -> tuple[str, str]:
        """프로젝트명 기반 일관된 색상 생성"""
        try:
            from utils.project_color_manager import get_project_colors
            return get_project_colors(project_name)
        except ImportError:
            # 폴백: 기존 방식
            hash_value = hashlib.md5(project_name.encode('utf-8')).hexdigest()
            color_index = int(hash_value[:2], 16) % len(self.COLOR_PALETTE)
            return self.COLOR_PALETTE[color_index]
    
    def _setup_widget(self):
        """위젯 초기 설정"""
        # 텍스트 설정
        self.setText(self.short_name)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 크기 설정
        self.setFixedHeight(24)
        self.setMinimumWidth(32)
        
        # 폰트 설정
        font = QFont()
        font.setPointSize(10)
        font.setWeight(QFont.Weight.Bold)
        self.setFont(font)
        
        # 커서 설정
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        # 툴팁 설정
        self.setToolTip(f"{self.project_name} (클릭하여 필터링)")
        
        # 스타일 적용
        self._update_style()
    
    def _update_style(self):
        """스타일 업데이트"""
        if self.is_active:
            # 활성 상태 스타일
            style = f"""
                QLabel {{
                    background-color: {self.bg_color};
                    color: {self.text_color};
                    border: 2px solid {self.bg_color};
                    border-radius: 12px;
                    padding: 2px 8px;
                    font-weight: bold;
                }}
            """
        else:
            # 비활성 상태 스타일
            style = f"""
                QLabel {{
                    background-color: {self.bg_color};
                    color: {self.text_color};
                    border: 1px solid {Colors.BORDER_LIGHT};
                    border-radius: 12px;
                    padding: 2px 8px;
                    font-weight: bold;
                }}
                QLabel:hover {{
                    border: 2px solid {self.bg_color};
                }}
            """
        
        self.setStyleSheet(style)
    
    def mousePressEvent(self, event):
        """마우스 클릭 이벤트 처리"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.project_id)
        super().mousePressEvent(event)
    
    def set_active(self, active: bool):
        """활성 상태 설정"""
        if self.is_active != active:
            self.is_active = active
            self._update_style()
    
    def get_project_info(self) -> dict:
        """프로젝트 정보 반환"""
        return {
            'id': self.project_id,
            'name': self.project_name,
            'short_name': self.short_name,
            'bg_color': self.bg_color,
            'text_color': self.text_color
        }


class ProjectFilterPanel(QFrame):
    """프로젝트 필터 패널"""
    
    # 필터 변경 시그널 (선택된 프로젝트 ID 목록 전달, None이면 전체)
    filter_changed = pyqtSignal(object)  # List[int] or None
    
    def __init__(self, parent: Optional[QWidget] = None):
        """
        프로젝트 필터 패널 초기화
        
        Args:
            parent: 부모 위젯
        """
        super().__init__(parent)
        
        self.project_tags: List[ProjectTagWidget] = []
        self.selected_project_ids: List[int] = []
        self.show_all_button: Optional[QPushButton] = None
        self.show_unclassified_button: Optional[QPushButton] = None
        
        self._setup_ui()
        
        logger.debug("프로젝트 필터 패널 초기화됨")
    
    def _setup_ui(self):
        """UI 초기 설정"""
        # 메인 레이아웃
        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.SM, Spacing.SM, Spacing.SM, Spacing.SM)
        layout.setSpacing(Spacing.SM)
        
        # 제목
        title_label = QLabel("프로젝트 필터")
        title_label.setStyleSheet(f"""
            QLabel {{
                font-size: {FontSizes.BASE};
                font-weight: {FontWeights.SEMIBOLD};
                color: {Colors.TEXT_PRIMARY};
                margin-bottom: 4px;
            }}
        """)
        layout.addWidget(title_label)
        
        # 컨트롤 버튼 영역
        control_layout = QHBoxLayout()
        control_layout.setSpacing(Spacing.XS)
        
        # "전체" 버튼
        self.show_all_button = QPushButton("전체")
        self.show_all_button.setFixedHeight(24)
        self.show_all_button.clicked.connect(self._show_all_projects)
        self.show_all_button.setStyleSheet(self._get_control_button_style(True))
        control_layout.addWidget(self.show_all_button)
        
        # "미분류" 버튼
        self.show_unclassified_button = QPushButton("미분류")
        self.show_unclassified_button.setFixedHeight(24)
        self.show_unclassified_button.clicked.connect(self._show_unclassified)
        self.show_unclassified_button.setStyleSheet(self._get_control_button_style(False))
        control_layout.addWidget(self.show_unclassified_button)
        
        control_layout.addStretch()
        layout.addLayout(control_layout)
        
        # 프로젝트 태그 영역
        self.tags_layout = QHBoxLayout()
        self.tags_layout.setSpacing(Spacing.XS)
        self.tags_layout.addStretch()  # 오른쪽 정렬을 위한 스트레치
        layout.addLayout(self.tags_layout)
        
        # 전체 프레임 스타일
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_SECONDARY};
                border: 1px solid {Colors.BORDER_LIGHT};
                border-radius: {BorderRadius.MD};
                padding: {Spacing.SM}px;
            }}
        """)
    
    def _get_control_button_style(self, is_active: bool) -> str:
        """컨트롤 버튼 스타일 반환"""
        if is_active:
            return f"""
                QPushButton {{
                    background-color: {Colors.PRIMARY};
                    color: white;
                    border: none;
                    border-radius: 12px;
                    padding: 4px 12px;
                    font-size: {FontSizes.SM};
                    font-weight: {FontWeights.SEMIBOLD};
                }}
                QPushButton:hover {{
                    background-color: {Colors.PRIMARY_DARK};
                }}
            """
        else:
            return f"""
                QPushButton {{
                    background-color: {Colors.BG_PRIMARY};
                    color: {Colors.TEXT_SECONDARY};
                    border: 1px solid {Colors.BORDER_LIGHT};
                    border-radius: 12px;
                    padding: 4px 12px;
                    font-size: {FontSizes.SM};
                    font-weight: {FontWeights.MEDIUM};
                }}
                QPushButton:hover {{
                    background-color: {Colors.GRAY_50};
                    border-color: {Colors.BORDER_MEDIUM};
                }}
            """
    
    def add_project_tag(self, project_id: int, project_name: str, short_name: str = ""):
        """프로젝트 태그 추가"""
        # 중복 확인
        for tag in self.project_tags:
            if tag.project_id == project_id:
                logger.warning(f"프로젝트 ID {project_id}는 이미 존재합니다")
                return
        
        # 새 태그 생성
        tag = ProjectTagWidget(project_id, project_name, short_name)
        tag.clicked.connect(self._on_tag_clicked)
        
        # 레이아웃에 추가 (스트레치 앞에 삽입)
        self.tags_layout.insertWidget(self.tags_layout.count() - 1, tag)
        self.project_tags.append(tag)
        
        logger.debug(f"프로젝트 태그 추가됨: {project_name}")
    
    def remove_project_tag(self, project_id: int):
        """프로젝트 태그 제거"""
        for i, tag in enumerate(self.project_tags):
            if tag.project_id == project_id:
                self.tags_layout.removeWidget(tag)
                tag.deleteLater()
                del self.project_tags[i]
                
                # 선택된 프로젝트에서도 제거
                if project_id in self.selected_project_ids:
                    self.selected_project_ids.remove(project_id)
                    self._update_filter()
                
                logger.debug(f"프로젝트 태그 제거됨: ID {project_id}")
                break
    
    def clear_project_tags(self):
        """모든 프로젝트 태그 제거"""
        for tag in self.project_tags:
            self.tags_layout.removeWidget(tag)
            tag.deleteLater()
        
        self.project_tags.clear()
        self.selected_project_ids.clear()
        self._show_all_projects()
        
        logger.debug("모든 프로젝트 태그 제거됨")
    
    def _on_tag_clicked(self, project_id: int):
        """태그 클릭 이벤트 처리"""
        if project_id in self.selected_project_ids:
            # 이미 선택된 경우 선택 해제
            self.selected_project_ids.remove(project_id)
        else:
            # 선택되지 않은 경우 선택
            self.selected_project_ids.append(project_id)
        
        # 태그 상태 업데이트
        self._update_tag_states()
        
        # 컨트롤 버튼 상태 업데이트
        self._update_control_button_states()
        
        # 필터 변경 시그널 발생
        self._update_filter()
        
        logger.debug(f"프로젝트 필터 변경: {self.selected_project_ids}")
    
    def _show_all_projects(self):
        """전체 프로젝트 보기"""
        self.selected_project_ids.clear()
        self._update_tag_states()
        self._update_control_button_states()
        self.filter_changed.emit(None)  # None = 전체 보기
        
        logger.debug("전체 프로젝트 보기 활성화")
    
    def _show_unclassified(self):
        """미분류 프로젝트만 보기"""
        self.selected_project_ids.clear()
        self._update_tag_states()
        self._update_control_button_states()
        self.filter_changed.emit([])  # 빈 리스트 = 미분류만
        
        logger.debug("미분류 프로젝트 보기 활성화")
    
    def _update_tag_states(self):
        """태그 활성 상태 업데이트"""
        for tag in self.project_tags:
            tag.set_active(tag.project_id in self.selected_project_ids)
    
    def _update_control_button_states(self):
        """컨트롤 버튼 상태 업데이트"""
        # "전체" 버튼 상태
        show_all_active = len(self.selected_project_ids) == 0
        self.show_all_button.setStyleSheet(self._get_control_button_style(show_all_active))
        
        # "미분류" 버튼 상태 (현재는 항상 비활성)
        self.show_unclassified_button.setStyleSheet(self._get_control_button_style(False))
    
    def _update_filter(self):
        """필터 업데이트 및 시그널 발생"""
        if len(self.selected_project_ids) == 0:
            # 아무것도 선택되지 않은 경우 전체 보기
            self.filter_changed.emit(None)
        else:
            # 선택된 프로젝트들만 보기
            self.filter_changed.emit(self.selected_project_ids.copy())
    
    def get_selected_projects(self) -> Optional[List[int]]:
        """선택된 프로젝트 ID 목록 반환 (None이면 전체)"""
        return self.selected_project_ids.copy() if self.selected_project_ids else None
    
    def set_selected_projects(self, project_ids: Optional[List[int]]):
        """선택된 프로젝트 설정"""
        if project_ids is None:
            self.selected_project_ids.clear()
        else:
            self.selected_project_ids = [pid for pid in project_ids if any(tag.project_id == pid for tag in self.project_tags)]
        
        self._update_tag_states()
        self._update_control_button_states()
        self._update_filter()#!/usr/bin/env python3
"""프로젝트 태그 위젯 구현"""

from PyQt6.QtWidgets import QLabel, QWidget, QHBoxLayout
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QRect
from PyQt6.QtGui import QFont, QColor, QPalette, QCursor
import hashlib
from typing import Optional, Dict, List
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class ProjectInfo:
    """프로젝트 정보 데이터 클래스"""
    name: str
    display_name: str
    color: str
    keywords: List[str]
    personas: List[str]
    description: str = ""
    activity_score: float = 0.0
    confidence_threshold: float = 0.6
    
    @classmethod
    def create_unclassified(cls) -> 'ProjectInfo':
        """미분류 프로젝트 정보 생성"""
        return cls(
            name="미분류",
            display_name="미분류",
            color="#6b7280",  # 회색
            keywords=[],
            personas=[],
            description="분류되지 않은 항목",
            activity_score=0.0
        )

class ProjectTagWidget(QLabel):
    """프로젝트 태그 위젯 클래스"""
    
    # 시그널 정의
    tag_clicked = pyqtSignal(str)  # 프로젝트명 전달
    tag_hovered = pyqtSignal(str)  # 호버 시 프로젝트명 전달
    
    def __init__(self, project_info: ProjectInfo, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self.project_info = project_info
        self.is_active = False  # 필터 활성 상태
        self.animation = None
        
        self._setup_ui()
        self._setup_events()
    
    def _setup_ui(self):
        """UI 초기 설정"""
        # 텍스트 설정
        self.setText(self.project_info.display_name)
        
        # 기본 스타일 적용
        self._apply_style()
        
        # 폰트 설정
        font = QFont()
        font.setPointSize(9)
        font.setWeight(QFont.Weight.Medium)
        self.setFont(font)
        
        # 크기 정책
        self.setFixedHeight(24)
        self.setMinimumWidth(40)
        
        # 커서 설정
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        # 툴팁 설정
        self._setup_tooltip()
    
    def _setup_tooltip(self):
        """툴팁 설정"""
        tooltip_text = f"프로젝트: {self.project_info.name}"
        if self.project_info.description:
            tooltip_text += f"\n설명: {self.project_info.description}"
        if self.project_info.personas:
            tooltip_text += f"\n참여자: {', '.join(self.project_info.personas[:3])}"
            if len(self.project_info.personas) > 3:
                tooltip_text += f" 외 {len(self.project_info.personas) - 3}명"
        
        self.setToolTip(tooltip_text)
    
    def _apply_style(self):
        """스타일 적용"""
        bg_color = self.project_info.color
        text_color = self._get_contrast_color(bg_color)
        
        # 활성 상태에 따른 스타일 조정
        if self.is_active:
            # 활성 상태: 더 진한 색상
            bg_color = self._darken_color(bg_color, 0.2)
            border_style = f"2px solid {self._darken_color(bg_color, 0.3)}"
        else:
            border_style = "1px solid transparent"
        
        style = f"""
        QLabel {{
            background-color: {bg_color};
            color: {text_color};
            border: {border_style};
            border-radius: 12px;
            padding: 4px 12px;
            margin: 2px;
        }}
        QLabel:hover {{
            background-color: {self._lighten_color(bg_color, 0.1)};
        }}
        """
        
        self.setStyleSheet(style)
    
    def _get_contrast_color(self, bg_color: str) -> str:
        """배경색에 따른 최적 텍스트 색상 반환"""
        # 색상 문자열에서 RGB 값 추출
        if bg_color.startswith('#'):
            bg_color = bg_color[1:]
        
        try:
            r = int(bg_color[0:2], 16)
            g = int(bg_color[2:4], 16)
            b = int(bg_color[4:6], 16)
            
            # 밝기 계산 (0.299*R + 0.587*G + 0.114*B)
            brightness = (r * 299 + g * 587 + b * 114) / 1000
            
            # 밝기에 따라 텍스트 색상 결정
            return "#ffffff" if brightness < 128 else "#000000"
        except (ValueError, IndexError):
            return "#ffffff"  # 기본값
    
    def _lighten_color(self, color: str, factor: float) -> str:
        """색상을 밝게 만들기"""
        if color.startswith('#'):
            color = color[1:]
        
        try:
            r = int(color[0:2], 16)
            g = int(color[2:4], 16)
            b = int(color[4:6], 16)
            
            # 각 채널을 밝게 조정
            r = min(255, int(r + (255 - r) * factor))
            g = min(255, int(g + (255 - g) * factor))
            b = min(255, int(b + (255 - b) * factor))
            
            return f"#{r:02x}{g:02x}{b:02x}"
        except (ValueError, IndexError):
            return color
    
    def _darken_color(self, color: str, factor: float) -> str:
        """색상을 어둡게 만들기"""
        if color.startswith('#'):
            color = color[1:]
        
        try:
            r = int(color[0:2], 16)
            g = int(color[2:4], 16)
            b = int(color[4:6], 16)
            
            # 각 채널을 어둡게 조정
            r = max(0, int(r * (1 - factor)))
            g = max(0, int(g * (1 - factor)))
            b = max(0, int(b * (1 - factor)))
            
            return f"#{r:02x}{g:02x}{b:02x}"
        except (ValueError, IndexError):
            return color
    
    def _setup_events(self):
        """이벤트 설정"""
        # 마우스 이벤트는 mousePressEvent에서 처리
        pass
    
    def mousePressEvent(self, event):
        """마우스 클릭 이벤트"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.tag_clicked.emit(self.project_info.name)
            self._animate_click()
        super().mousePressEvent(event)
    
    def enterEvent(self, event):
        """마우스 호버 진입 이벤트"""
        self.tag_hovered.emit(self.project_info.name)
        super().enterEvent(event)
    
    def _animate_click(self):
        """클릭 애니메이션"""
        if self.animation:
            self.animation.stop()
        
        # 크기 애니메이션
        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(150)
        self.animation.setEasingCurve(QEasingCurve.Type.OutBack)
        
        # 현재 위치와 크기
        current_rect = self.geometry()
        
        # 애니메이션 시작 (약간 축소)
        start_rect = QRect(
            current_rect.x() + 2,
            current_rect.y() + 1,
            current_rect.width() - 4,
            current_rect.height() - 2
        )
        
        self.animation.setStartValue(start_rect)
        self.animation.setEndValue(current_rect)
        self.animation.start()
    
    def set_active(self, active: bool):
        """활성 상태 설정"""
        if self.is_active != active:
            self.is_active = active
            self._apply_style()
    
    def update_project_info(self, project_info: ProjectInfo):
        """프로젝트 정보 업데이트"""
        self.project_info = project_info
        self.setText(project_info.display_name)
        self._apply_style()
        self._setup_tooltip()


class ProjectTagGenerator:
    """프로젝트 태그 생성기"""
    
    # 12색 기본 팔레트
    BASE_COLORS = [
        "#2563eb",  # 파란색
        "#16a34a",  # 초록색
        "#ea580c",  # 주황색
        "#9333ea",  # 보라색
        "#ca8a04",  # 노란색
        "#dc2626",  # 빨간색
        "#7c3aed",  # 인디고
        "#059669",  # 청록색
        "#d97706",  # 호박색
        "#be123c",  # 장미색
        "#4338ca",  # 남색
        "#0891b2"   # 하늘색
    ]
    
    def __init__(self):
        self.used_colors = set()
        self.project_color_map: Dict[str, str] = {}
    
    def generate_display_name(self, project_name: str) -> str:
        """프로젝트명에서 축약명 생성"""
        if not project_name or project_name == "미분류":
            return project_name
        
        # 공백과 특수문자로 단어 분리
        import re
        words = re.findall(r'\b\w+', project_name)
        
        if not words:
            return project_name[:4]  # 최대 4글자
        
        # 각 단어의 첫 글자 추출
        initials = []
        for word in words[:3]:  # 최대 3개 단어
            if word.isdigit():
                initials.append(word)  # 숫자는 그대로
            elif len(word) >= 2:
                initials.append(word[0].upper())
        
        result = ''.join(initials)
        
        # 너무 짧으면 첫 번째 단어 사용
        if len(result) < 2 and words:
            result = words[0][:4].upper()
        
        return result[:6]  # 최대 6글자
    
    def generate_color(self, project_name: str) -> str:
        """프로젝트명 기반 일관된 색상 생성"""
        if project_name in self.project_color_map:
            return self.project_color_map[project_name]
        
        # 프로젝트명 해시값 기반 색상 선택
        hash_value = int(hashlib.md5(project_name.encode()).hexdigest(), 16)
        color_index = hash_value % len(self.BASE_COLORS)
        
        color = self.BASE_COLORS[color_index]
        
        # 색상 충돌 방지 (같은 색상이 너무 많이 사용되지 않도록)
        attempts = 0
        while color in self.used_colors and attempts < len(self.BASE_COLORS):
            color_index = (color_index + 1) % len(self.BASE_COLORS)
            color = self.BASE_COLORS[color_index]
            attempts += 1
        
        self.used_colors.add(color)
        self.project_color_map[project_name] = color
        
        return color
    
    def create_project_info(self, project_name: str, **kwargs) -> ProjectInfo:
        """프로젝트 정보 객체 생성"""
        display_name = self.generate_display_name(project_name)
        color = self.generate_color(project_name)
        
        return ProjectInfo(
            name=project_name,
            display_name=display_name,
            color=color,
            keywords=kwargs.get('keywords', []),
            personas=kwargs.get('personas', []),
            description=kwargs.get('description', ''),
            activity_score=kwargs.get('activity_score', 0.0),
            confidence_threshold=kwargs.get('confidence_threshold', 0.6)
        )
    
    def create_tag_widget(self, project_info: ProjectInfo, parent: Optional[QWidget] = None) -> ProjectTagWidget:
        """태그 위젯 생성"""
        return ProjectTagWidget(project_info, parent)
    
    def reset_colors(self):
        """색상 사용 기록 초기화"""
        self.used_colors.clear()
        self.project_color_map.clear()


class ProjectTagContainer(QWidget):
    """프로젝트 태그들을 담는 컨테이너 위젯"""
    
    tag_clicked = pyqtSignal(str)
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(4)
        
        self.tags: Dict[str, ProjectTagWidget] = {}
        self.generator = ProjectTagGenerator()
    
    def add_tag(self, project_info: ProjectInfo) -> ProjectTagWidget:
        """태그 추가"""
        if project_info.name in self.tags:
            return self.tags[project_info.name]
        
        tag_widget = self.generator.create_tag_widget(project_info, self)
        tag_widget.tag_clicked.connect(self.tag_clicked.emit)
        
        self.layout.addWidget(tag_widget)
        self.tags[project_info.name] = tag_widget
        
        return tag_widget
    
    def remove_tag(self, project_name: str):
        """태그 제거"""
        if project_name in self.tags:
            tag_widget = self.tags.pop(project_name)
            self.layout.removeWidget(tag_widget)
            tag_widget.deleteLater()
    
    def clear_tags(self):
        """모든 태그 제거"""
        for tag_widget in self.tags.values():
            self.layout.removeWidget(tag_widget)
            tag_widget.deleteLater()
        
        self.tags.clear()
        self.generator.reset_colors()
    
    def set_active_tag(self, project_name: str):
        """특정 태그를 활성 상태로 설정"""
        for name, tag_widget in self.tags.items():
            tag_widget.set_active(name == project_name)
    
    def get_tag_count(self) -> int:
        """태그 개수 반환"""
        return len(self.tags)


class ProjectFilterPanel(QWidget):
    """프로젝트 필터 패널"""
    
    filter_changed = pyqtSignal(object)  # Optional[List[str]] - None=전체, []=미분류, [names]=선택된 프로젝트들
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self.selected_projects: Optional[List[str]] = None  # None = 전체 보기
        self.project_tags: Dict[str, ProjectTagWidget] = {}
        
        self._setup_ui()
    
    def _setup_ui(self):
        """UI 설정"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # 제목
        title = QLabel("📂 프로젝트 필터")
        title.setStyleSheet("font-weight: bold; font-size: 12px; color: #374151;")
        layout.addWidget(title)
        
        # 필터 버튼 컨테이너
        self.filter_container = QWidget()
        self.filter_layout = QHBoxLayout(self.filter_container)
        self.filter_layout.setContentsMargins(0, 0, 0, 0)
        self.filter_layout.setSpacing(6)
        
        # 전체 보기 버튼
        self.all_button = self._create_filter_button("전체", "#6b7280", is_special=True)
        self.all_button.tag_clicked.connect(lambda name: self._on_filter_clicked("전체"))
        self.all_button.set_active(True)  # 기본 선택
        self.filter_layout.addWidget(self.all_button)
        
        # 미분류 버튼
        self.unclassified_button = self._create_filter_button("미분류", "#6b7280", is_special=True)
        self.unclassified_button.tag_clicked.connect(lambda name: self._on_filter_clicked("미분류"))
        self.filter_layout.addWidget(self.unclassified_button)
        
        # 구분선
        separator = QLabel("|")
        separator.setStyleSheet("color: #d1d5db; margin: 0 4px;")
        self.filter_layout.addWidget(separator)
        
        # 스트레치 추가
        self.filter_layout.addStretch()
        
        layout.addWidget(self.filter_container)
        
        # 전체 패널 스타일
        self.setStyleSheet("""
        QWidget {
            background-color: #f9fafb;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
        }
        """)
    
    def _create_filter_button(self, text: str, color: str, is_special: bool = False) -> ProjectTagWidget:
        """필터 버튼 생성 (색상 관리자 사용)"""
        if is_special:
            # 특수 버튼 (전체, 미분류)
            project_info = ProjectInfo(
                name=text,
                display_name=text,
                color=color,
                keywords=[],
                personas=[],
                description=f"{text} 항목"
            )
        else:
            # 일반 프로젝트 버튼 - 색상 관리자 사용
            try:
                from utils.project_color_manager import get_project_colors, get_project_short_name
                bg_color, text_color = get_project_colors(text)
                short_name = get_project_short_name(text)
                
                project_info = ProjectInfo(
                    name=text,
                    display_name=short_name,  # 축약명 사용
                    color=bg_color,
                    keywords=[],
                    personas=[],
                    description=text
                )
            except ImportError:
                # 폴백: 기본 생성
                generator = ProjectTagGenerator()
                project_info = generator.create_project_info(text)
        
        button = ProjectTagWidget(project_info)
        button.tag_clicked.connect(self._on_filter_clicked)
        
        return button
    
    def add_project_filter(self, project_name: str) -> ProjectTagWidget:
        """프로젝트 필터 버튼 추가"""
        if project_name in self.project_tags:
            return self.project_tags[project_name]
        
        # 프로젝트 버튼 생성
        button = self._create_filter_button(project_name, "", is_special=False)
        
        # 구분선 앞에 삽입 (마지막에서 두 번째 위치)
        insert_index = self.filter_layout.count() - 1  # 스트레치 앞
        self.filter_layout.insertWidget(insert_index, button)
        
        self.project_tags[project_name] = button
        
        return button
    
    def _on_filter_clicked(self, project_name: str):
        """필터 버튼 클릭 이벤트"""
        # 모든 버튼 비활성화
        self.all_button.set_active(False)
        self.unclassified_button.set_active(False)
        for button in self.project_tags.values():
            button.set_active(False)
        
        # 클릭된 버튼 활성화 및 필터 설정
        if project_name == "전체":
            self.all_button.set_active(True)
            self.selected_projects = None
        elif project_name == "미분류":
            self.unclassified_button.set_active(True)
            self.selected_projects = []
        else:
            if project_name in self.project_tags:
                self.project_tags[project_name].set_active(True)
            self.selected_projects = [project_name]
        
        # 필터 변경 시그널 발생
        self.filter_changed.emit(self.selected_projects)
    
    def get_selected_projects(self) -> Optional[List[str]]:
        """선택된 프로젝트 목록 반환"""
        return self.selected_projects
    
    def clear_project_filters(self):
        """모든 프로젝트 필터 제거"""
        for button in self.project_tags.values():
            self.filter_layout.removeWidget(button)
            button.deleteLater()
        
        self.project_tags.clear()
    
    def set_project_count(self, project_name: str, count: int):
        """프로젝트별 TODO 개수 표시 (선택사항)"""
        if project_name == "전체":
            self.all_button.setText(f"전체 ({count})")
        elif project_name == "미분류":
            self.unclassified_button.setText(f"미분류 ({count})")
        elif project_name in self.project_tags:
            button = self.project_tags[project_name]
            display_name = button.project_info.display_name
            button.setText(f"{display_name} ({count})")
    
    def update_active_projects(self, active_projects: set):
        """활성 프로젝트 목록으로 태그 바 업데이트
        
        Args:
            active_projects: 현재 활성화된 프로젝트명 세트
        """
        try:
            # 기존 프로젝트 태그 중 활성 프로젝트에 없는 것 제거
            projects_to_remove = []
            for project_name in self.project_tags.keys():
                if project_name not in active_projects:
                    projects_to_remove.append(project_name)
            
            for project_name in projects_to_remove:
                button = self.project_tags.pop(project_name)
                self.filter_layout.removeWidget(button)
                button.deleteLater()
            
            # 새로운 프로젝트 추가
            for project_name in active_projects:
                if project_name and project_name not in self.project_tags:
                    self.add_project_filter(project_name)
            
            logger.debug(f"[프로젝트 태그 바] 업데이트 완료: {len(active_projects)}개 프로젝트")
            
        except Exception as e:
            logger.error(f"[프로젝트 태그 바] 업데이트 오류: {e}", exc_info=True)


if __name__ == "__main__":
    """테스트 코드"""
    import sys
    from PyQt6.QtWidgets import QApplication, QVBoxLayout, QMainWindow
    
    app = QApplication(sys.argv)
    
    # 메인 윈도우
    window = QMainWindow()
    central_widget = QWidget()
    window.setCentralWidget(central_widget)
    
    layout = QVBoxLayout(central_widget)
    
    # 태그 컨테이너
    container = ProjectTagContainer()
    layout.addWidget(container)
    
    # 테스트 프로젝트들
    generator = ProjectTagGenerator()
    
    test_projects = [
        "CareConnect 2.0 리디자인",
        "모바일 앱 개발",
        "데이터베이스 최적화",
        "사용자 인터페이스 개선",
        "보안 강화 프로젝트",
        "미분류"
    ]
    
    for project_name in test_projects:
        if project_name == "미분류":
            project_info = ProjectInfo.create_unclassified()
        else:
            project_info = generator.create_project_info(
                project_name,
                keywords=[project_name.split()[0]],
                personas=["개발자1", "디자이너1"],
                description=f"{project_name} 관련 작업"
            )
        
        container.add_tag(project_info)
    
    # 태그 클릭 이벤트 연결
    def on_tag_clicked(project_name):
        print(f"태그 클릭됨: {project_name}")
        container.set_active_tag(project_name)
    
    container.tag_clicked.connect(on_tag_clicked)
    
    window.setWindowTitle("프로젝트 태그 위젯 테스트")
    window.resize(800, 200)
    window.show()
    
    sys.exit(app.exec())