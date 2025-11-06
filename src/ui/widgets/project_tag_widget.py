# -*- coding: utf-8 -*-
"""
프로젝트 태그 위젯

TODO 항목에 프로젝트 태그를 표시하는 UI 컴포넌트입니다.
"""
import logging
from typing import Dict, List, Optional, Set

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, 
    QFrame, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPalette

from src.services.project_tag_service import ProjectTagService, ProjectTag

logger = logging.getLogger(__name__)

# 싱글톤 인스턴스
_project_service_instance = None

def get_project_service():
    """프로젝트 서비스 싱글톤 인스턴스 반환"""
    global _project_service_instance
    if _project_service_instance is None:
        # 프로젝트 태그 캐시 DB 경로 설정
        import os
        vdos_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 
                               'virtualoffice', 'src', 'virtualoffice')
        cache_db_path = os.path.join(vdos_dir, 'project_tags_cache.db')
        
        _project_service_instance = ProjectTagService(cache_db_path=cache_db_path)
    return _project_service_instance


class ProjectTagLabel(QLabel):
    """개별 프로젝트 태그 라벨"""
    
    def __init__(self, project_tag: ProjectTag, parent=None):
        super().__init__(parent)
        self.project_tag = project_tag
        self._setup_ui()
    
    def _setup_ui(self):
        """UI 설정"""
        self.setText(self.project_tag.code)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 폰트 설정
        font = QFont()
        font.setPointSize(9)
        font.setBold(True)
        self.setFont(font)
        
        # 스타일 설정
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {self.project_tag.color};
                color: white;
                border-radius: 10px;
                padding: 2px 8px;
                margin: 1px;
                font-weight: bold;
                font-size: 9px;
            }}
        """)
        
        # 크기 정책
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(20)
        
        # 툴팁 설정
        if self.project_tag.description:
            self.setToolTip(f"{self.project_tag.name}: {self.project_tag.description}")
        else:
            self.setToolTip(self.project_tag.name)


class ProjectTagBar(QWidget):
    """프로젝트 태그 바 - 상단에 표시되는 필터 바"""
    
    tag_clicked = pyqtSignal(str)  # 태그 클릭 시 프로젝트 코드 전달
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.project_service = get_project_service()
        self.active_projects: Set[str] = set()
        self.selected_filter: Optional[str] = None
        self._setup_ui()
    
    def _setup_ui(self):
        """UI 설정"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(4)
        
        # 제목 라벨
        title_label = QLabel("🏷️ 프로젝트 필터")
        title_label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                font-size: 11px;
                color: #374151;
                margin-right: 8px;
            }
        """)
        layout.addWidget(title_label)
        
        # 전체 버튼
        self.all_button = QPushButton("전체")
        self.all_button.setCheckable(True)
        self.all_button.setChecked(True)
        self.all_button.clicked.connect(lambda: self._on_filter_clicked(None))
        self.all_button.setStyleSheet(self._get_filter_button_style(True))
        layout.addWidget(self.all_button)
        
        # 프로젝트 태그 버튼들
        self.tag_buttons: Dict[str, QPushButton] = {}
        for project_tag in self.project_service.get_available_projects().values():
            button = QPushButton(project_tag.code)
            button.setCheckable(True)
            button.clicked.connect(lambda checked, code=project_tag.code: self._on_filter_clicked(code))
            button.setStyleSheet(self._get_project_button_style(project_tag, False))
            button.setVisible(True)  # 항상 표시
            button.setToolTip(f"{project_tag.name}: {project_tag.description}")
            layout.addWidget(button)
            self.tag_buttons[project_tag.code] = button
        
        # 스페이서
        layout.addStretch()
        
        # 전체 스타일
        self.setStyleSheet("""
            QWidget {
                background-color: #F9FAFB;
                border-bottom: 1px solid #E5E7EB;
            }
        """)
    
    def _get_filter_button_style(self, is_active: bool) -> str:
        """필터 버튼 스타일"""
        if is_active:
            return """
                QPushButton {
                    background-color: #3B82F6;
                    color: white;
                    border: none;
                    border-radius: 12px;
                    padding: 4px 12px;
                    font-weight: bold;
                    font-size: 10px;
                }
                QPushButton:hover {
                    background-color: #2563EB;
                }
            """
        else:
            return """
                QPushButton {
                    background-color: #E5E7EB;
                    color: #6B7280;
                    border: none;
                    border-radius: 12px;
                    padding: 4px 12px;
                    font-weight: bold;
                    font-size: 10px;
                }
                QPushButton:hover {
                    background-color: #D1D5DB;
                }
            """
    
    def _get_project_button_style(self, project_tag: ProjectTag, is_active: bool) -> str:
        """프로젝트 버튼 스타일"""
        if is_active:
            return f"""
                QPushButton {{
                    background-color: {project_tag.color};
                    color: white;
                    border: none;
                    border-radius: 12px;
                    padding: 4px 12px;
                    font-weight: bold;
                    font-size: 10px;
                }}
                QPushButton:hover {{
                    opacity: 0.8;
                }}
            """
        else:
            return f"""
                QPushButton {{
                    background-color: rgba({self._hex_to_rgb(project_tag.color)}, 0.2);
                    color: {project_tag.color};
                    border: 1px solid {project_tag.color};
                    border-radius: 12px;
                    padding: 4px 12px;
                    font-weight: bold;
                    font-size: 10px;
                }}
                QPushButton:hover {{
                    background-color: rgba({self._hex_to_rgb(project_tag.color)}, 0.3);
                }}
            """
    
    def _hex_to_rgb(self, hex_color: str) -> str:
        """HEX 색상을 RGB로 변환"""
        hex_color = hex_color.lstrip('#')
        return f"{int(hex_color[0:2], 16)}, {int(hex_color[2:4], 16)}, {int(hex_color[4:6], 16)}"
    
    def _on_filter_clicked(self, project_code: Optional[str]):
        """필터 버튼 클릭 처리"""
        # 모든 버튼 비활성화
        self.all_button.setChecked(project_code is None)
        self.all_button.setStyleSheet(self._get_filter_button_style(project_code is None))
        
        for code, button in self.tag_buttons.items():
            is_active = (code == project_code)
            button.setChecked(is_active)
            project_tag = self.project_service.get_project_tag(code)
            if project_tag:
                button.setStyleSheet(self._get_project_button_style(project_tag, is_active))
        
        self.selected_filter = project_code
        self.tag_clicked.emit(project_code or "")
    
    def update_active_projects(self, projects: Set[str]):
        """활성 프로젝트 목록 업데이트"""
        self.active_projects = projects
        
        # 버튼 표시/숨김 처리
        for code, button in self.tag_buttons.items():
            button.setVisible(code in projects)
    
    def get_selected_filter(self) -> Optional[str]:
        """현재 선택된 필터 반환"""
        return self.selected_filter


class ProjectTagContainer(QWidget):
    """TODO 항목에 표시되는 프로젝트 태그 컨테이너"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.project_service = get_project_service()
        self._setup_ui()
    
    def _setup_ui(self):
        """UI 설정"""
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(4)
        
        # 크기 정책
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(24)
    
    def set_project(self, project_code: Optional[str]):
        """프로젝트 태그 설정"""
        # 기존 태그 제거
        self.clear_tags()
        
        if project_code:
            project_tag = self.project_service.get_project_tag(project_code)
            if project_tag:
                tag_label = ProjectTagLabel(project_tag)
                self.layout.addWidget(tag_label)
        
        # 스페이서 추가
        self.layout.addStretch()
    
    def clear_tags(self):
        """모든 태그 제거"""
        while self.layout.count():
            child = self.layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()


def create_project_tag_label(project_code: str) -> Optional[ProjectTagLabel]:
    """프로젝트 태그 라벨 생성 헬퍼 함수"""
    try:
        service = get_project_service()
        project_tag = service.get_project_tag(project_code)
        if project_tag:
            return ProjectTagLabel(project_tag)
        else:
            # 프로젝트 태그가 없으면 기본 태그 생성
            logger.warning(f"[프로젝트 태그] {project_code} 프로젝트 태그를 찾을 수 없음, 기본 태그 생성")
            from src.services.project_tag_service import ProjectTag
            default_tag = ProjectTag(project_code, project_code, "#6B7280", f"{project_code} 프로젝트")
            return ProjectTagLabel(default_tag)
    except Exception as e:
        logger.error(f"[프로젝트 태그] {project_code} 태그 라벨 생성 오류: {e}")
        return None