# -*- coding: utf-8 -*-
"""
요약 다이얼로그

일일/주간 요약을 표시하는 다이얼로그입니다.
"""
import logging
from datetime import datetime
from pathlib import Path
from typing import List
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QSizePolicy, QFileDialog, QMessageBox, QMenu
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ..styles import Colors, Fonts, FontSizes, FontWeights, Spacing, BorderRadius
from ..helpers import WrapHelper

logger = logging.getLogger(__name__)


class SummaryDialog(QDialog):
    """요약 다이얼로그"""
    
    def __init__(self, title: str, text: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(600, 500)
        self._raw_text = (text or "").strip()
        self._init_ui(title, self._raw_text or "표시할 요약이 없습니다.")
    
    def _init_ui(self, title: str, text: str):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 헤더
        self._create_header(layout, title)
        
        # 스크롤 영역
        scroll, content_labels = self._create_content_area(layout, text)
        
        # 하단 버튼
        self._create_footer(layout)
        
        # 텍스트 래핑 헬퍼 설정
        wrap_helper = WrapHelper(content_labels, Spacing.MD, self)
        scroll.viewport().installEventFilter(wrap_helper)
        self.installEventFilter(wrap_helper)
        self._wrap_helper = wrap_helper  # keep reference
    
    def _create_header(self, layout: QVBoxLayout, title: str):
        """헤더 생성"""
        header = QWidget()
        header.setStyleSheet(f"""
            QWidget {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {Colors.PRIMARY}, stop:1 {Colors.PRIMARY_DARK});
                padding: {Spacing.MD}px;
            }}
        """)
        header_layout = QVBoxLayout(header)
        
        title_label = QLabel(title)
        title_label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_XXL, QFont.Weight.Bold))
        title_label.setStyleSheet("color: white;")
        header_layout.addWidget(title_label)
        
        layout.addWidget(header)
    
    def _create_content_area(self, layout: QVBoxLayout, text: str) -> tuple:
        """컨텐츠 영역 생성"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #F9FAFB;
            }
            QScrollArea > QWidget > QWidget {
                background-color: #F9FAFB;
            }
        """)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # 내용 컨테이너
        content_widget = QWidget()
        content_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(Spacing.MD, Spacing.MD, Spacing.MD, Spacing.MD)
        content_layout.setSpacing(Spacing.SM)
        
        # 텍스트 파싱 및 섹션별 표시
        content_labels = self._parse_and_display_text(content_layout, text)
        
        content_layout.addStretch()
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)
        
        return scroll, content_labels
    
    def _parse_and_display_text(self, content_layout: QVBoxLayout, text: str) -> List[QLabel]:
        """텍스트를 파싱하여 섹션별로 표시"""
        content_labels: List[QLabel] = []
        lines = (text.strip() or "표시할 요약이 없습니다.").split('\n')
        
        section_widget = None
        section_layout = None
        
        for line in lines:
            line = line.strip()
            if not line or line == '=' * 40:
                continue
            
            # 섹션 제목 감지
            if self._is_section_title(line):
                # 이전 섹션 추가
                if section_widget:
                    content_layout.addWidget(section_widget)
                
                # 새 섹션 시작
                section_widget, section_layout = self._create_section()
                
                # 섹션 제목 추가
                section_title = QLabel(line)
                section_title.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_BASE, QFont.Weight.Bold))
                section_title.setStyleSheet(f"color: {Colors.PRIMARY}; padding-bottom: 4px;")
                section_title.setWordWrap(True)
                section_title.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
                section_layout.addWidget(section_title)
            else:
                # 섹션 내용
                if not section_widget:
                    section_widget, section_layout = self._create_section()
                
                content_label = self._create_content_label(line)
                section_layout.addWidget(content_label)
                content_labels.append(content_label)
        
        # 마지막 섹션 추가
        if section_widget:
            content_layout.addWidget(section_widget)
        
        return content_labels
    
    def _is_section_title(self, line: str) -> bool:
        """섹션 제목인지 확인"""
        return (line.endswith(':') or 
                '요약' in line or 
                'TOP' in line or 
                '발신자' in line or 
                '액션' in line)
    
    def _create_section(self) -> tuple:
        """섹션 위젯 생성"""
        section_widget = QWidget()
        section_widget.setStyleSheet(f"""
            QWidget {{
                background-color: white;
                border-radius: {BorderRadius.BASE}px;
                border: 1px solid {Colors.BORDER_LIGHT};
            }}
        """)
        section_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        
        section_layout = QVBoxLayout(section_widget)
        section_layout.setContentsMargins(Spacing.MD, Spacing.SM, Spacing.MD, Spacing.SM)
        section_layout.setSpacing(Spacing.XS)
        
        return section_widget, section_layout
    
    def _create_content_label(self, text: str) -> QLabel:
        """컨텐츠 레이블 생성"""
        label = QLabel(text)
        label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM))
        label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; padding: 2px 0;")
        label.setWordWrap(True)
        label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        return label
    
    def _create_footer(self, layout: QVBoxLayout):
        """하단 버튼 생성"""
        button_container = QWidget()
        button_container.setStyleSheet(f"background-color: {Colors.BG_SECONDARY}; padding: {Spacing.SM}px;")
        button_layout = QHBoxLayout(button_container)
        button_layout.addStretch()

        download_button = self._create_download_button()
        button_layout.addWidget(download_button)
        
        close_button = QPushButton("닫기")
        close_button.setMinimumWidth(100)
        close_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.PRIMARY};
                color: white;
                border: none;
                border-radius: {BorderRadius.BASE}px;
                padding: {Spacing.SM}px {Spacing.MD}px;
                font-size: {FontSizes.BASE};
                font-weight: {FontWeights.SEMIBOLD};
            }}
            QPushButton:hover {{
                background-color: {Colors.PRIMARY_DARK};
            }}
        """)
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)
        
        layout.addWidget(button_container)

    def _create_download_button(self) -> QPushButton:
        """다운로드 버튼 생성"""
        button = QPushButton("다운로드")
        button.setMinimumWidth(110)
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: white;
                color: {Colors.PRIMARY_DARK};
                border: 1px solid {Colors.PRIMARY};
                border-radius: {BorderRadius.BASE}px;
                padding: {Spacing.SM}px {Spacing.MD}px;
                font-size: {FontSizes.BASE};
                font-weight: {FontWeights.MEDIUM};
            }}
            QPushButton::menu-indicator {{
                image: none;
            }}
            QPushButton:hover {{
                background-color: {Colors.BG_PRIMARY};
            }}
        """)
        menu = QMenu(button)
        menu.addAction("Markdown (.md) 저장", lambda: self._download_summary("md"))
        menu.addAction("텍스트 (.txt) 저장", lambda: self._download_summary("txt"))
        button.setMenu(menu)
        return button

    def _download_summary(self, fmt: str) -> None:
        """요약을 지정된 포맷으로 저장"""
        if not self._raw_text:
            QMessageBox.warning(self, "다운로드 실패", "저장할 요약 데이터가 없습니다.")
            return
        
        suffix = ".md" if fmt == "md" else ".txt"
        filters = {
            "md": "Markdown 파일 (*.md)",
            "txt": "텍스트 파일 (*.txt)"
        }
        suggested = self._build_default_filename(suffix)
        path, _ = QFileDialog.getSaveFileName(
            self,
            "요약 다운로드",
            str(Path.home() / suggested),
            f"{filters[fmt]};;모든 파일 (*.*)"
        )
        if not path:
            return
        
        path_obj = Path(path)
        if path_obj.suffix.lower() != suffix:
            path_obj = path_obj.with_suffix(suffix)
        
        try:
            content = self._build_export_content(fmt)
            path_obj.write_text(content, encoding="utf-8")
        except OSError as exc:
            logger.exception("요약 저장 실패: %s", exc)
            QMessageBox.critical(self, "다운로드 실패", "파일을 저장하는 중 문제가 발생했습니다.")
            return
        
        QMessageBox.information(self, "다운로드 완료", f"요약을 '{path_obj.name}' 파일로 저장했습니다.")

    def _build_default_filename(self, suffix: str) -> str:
        """제목과 포맷에 맞는 기본 파일명 생성"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        title = self.windowTitle().replace(" ", "_")
        return f"{title}_{timestamp}{suffix}"

    def _build_export_content(self, fmt: str) -> str:
        """포맷별 저장 콘텐츠 생성"""
        lines = [line.strip() for line in (self._raw_text or "").splitlines() if line.strip()]
        if not lines:
            return "표시할 요약이 없습니다.\n"
        
        if fmt == "md":
            md_lines: List[str] = []
            for idx, line in enumerate(lines):
                if set(line) == {"="}:
                    continue
                if idx == 0:
                    md_lines.append(f"# {line}")
                    continue
                if self._is_section_title(line):
                    title = line.rstrip(":")
                    if md_lines and md_lines[-1] != "":
                        md_lines.append("")
                    md_lines.append(f"## {title}")
                else:
                    if line.startswith(("-", "*", "·")):
                        md_lines.append(line)
                    else:
                        md_lines.append(f"- {line}")
            return "\n".join(md_lines).strip() + "\n"
        
        return "\n".join(lines) + "\n"
