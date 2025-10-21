# -*- coding: utf-8 -*-
"""
메시지 상세 보기 다이얼로그
요약 카드 클릭 시 원본 메시지 목록과 상세 내용을 표시
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QListWidget, QListWidgetItem, QTextEdit, QPushButton,
    QSplitter, QWidget, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QCursor
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from .styles import (
    Colors, Fonts, FontSizes, FontWeights, Spacing, BorderRadius, Icons,
    get_message_type_icon, get_priority_icon
)

logger = logging.getLogger(__name__)


class MessageDetailDialog(QDialog):
    """메시지 상세 보기 다이얼로그"""
    
    def __init__(
        self,
        summary_group: Dict[str, Any],
        messages: List[Dict[str, Any]],
        parent=None
    ):
        """
        Args:
            summary_group: 요약 그룹 데이터
            messages: 원본 메시지 리스트
            parent: 부모 위젯
        """
        super().__init__(parent)
        self.summary_group = summary_group
        self.messages = messages
        
        self._init_ui()
        self._populate_messages()
        
        # 첫 번째 메시지 자동 선택
        if self.messages:
            self.message_list.setCurrentRow(0)
    
    def _init_ui(self):
        """UI 초기화"""
        # 다이얼로그 설정
        period_label = self.summary_group.get("period_label", "메시지 상세")
        total_count = len(self.messages)
        self.setWindowTitle(f"{period_label} (총 {total_count}건)")
        self.setMinimumSize(900, 600)
        
        # 메인 레이아웃
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 헤더
        header = self._create_header()
        main_layout.addWidget(header)
        
        # 좌우 분할 (QSplitter)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 좌측: 메시지 목록
        left_panel = self._create_message_list_panel()
        splitter.addWidget(left_panel)
        
        # 우측: 메시지 상세
        right_panel = self._create_message_detail_panel()
        splitter.addWidget(right_panel)
        
        # 분할 비율 설정 (40:60)
        splitter.setStretchFactor(0, 40)
        splitter.setStretchFactor(1, 60)
        
        main_layout.addWidget(splitter)
        
        # 하단 버튼
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(
            Spacing.MD, Spacing.SM, Spacing.MD, Spacing.MD
        )
        button_layout.addStretch()
        
        close_button = QPushButton("닫기")
        close_button.setMinimumWidth(100)
        close_button.clicked.connect(self.accept)
        close_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.PRIMARY};
                color: white;
                border: none;
                border-radius: {BorderRadius.BASE}px;
                padding: {Spacing.SM}px {Spacing.MD}px;
                font-size: {Fonts.SIZE_BASE}px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {Colors.PRIMARY_DARK};
            }}
        """)
        button_layout.addWidget(close_button)
        
        main_layout.addLayout(button_layout)
    
    def _create_header(self) -> QWidget:
        """헤더 생성"""
        header = QWidget()
        header.setStyleSheet(f"""
            QWidget {{
                background-color: {Colors.BG_SECONDARY};
                border-bottom: 1px solid {Colors.BORDER_LIGHT};
            }}
        """)
        
        layout = QVBoxLayout(header)
        layout.setContentsMargins(
            Spacing.MD, Spacing.MD, Spacing.MD, Spacing.MD
        )
        
        # 제목
        period_label = self.summary_group.get("period_label", "메시지 상세")
        title_label = QLabel(period_label)
        title_label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_LG, QFont.Weight.Bold))
        title_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")
        layout.addWidget(title_label)
        
        # 통계 정보
        stats_text = self.summary_group.get("statistics_summary", "")
        if stats_text:
            stats_label = QLabel(stats_text)
            stats_label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM))
            stats_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
            layout.addWidget(stats_label)
        
        return header
    
    def _create_message_list_panel(self) -> QWidget:
        """메시지 목록 패널 생성"""
        panel = QWidget()
        panel.setStyleSheet(f"""
            QWidget {{
                background-color: {Colors.BG_PRIMARY};
                border-right: 1px solid {Colors.BORDER_LIGHT};
            }}
        """)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 섹션 헤더
        header_label = QLabel("  메시지 목록")
        header_label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_BASE, QFont.Weight.Bold))
        header_label.setStyleSheet(f"""
            QLabel {{
                background-color: {Colors.BG_SECONDARY};
                color: {Colors.TEXT_PRIMARY};
                padding: {Spacing.SM}px;
                border-bottom: 1px solid {Colors.BORDER_LIGHT};
            }}
        """)
        layout.addWidget(header_label)
        
        # 메시지 목록 (QListWidget)
        self.message_list = QListWidget()
        self.message_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {Colors.BG_PRIMARY};
                border: none;
                outline: none;
            }}
            QListWidget::item {{
                padding: {Spacing.SM}px;
                border-bottom: 1px solid {Colors.BORDER_LIGHT};
            }}
            QListWidget::item:selected {{
                background-color: {Colors.PRIMARY_LIGHT};
                color: {Colors.TEXT_PRIMARY};
            }}
            QListWidget::item:hover {{
                background-color: {Colors.GRAY_100};
            }}
        """)
        self.message_list.currentRowChanged.connect(self._on_message_selected)
        layout.addWidget(self.message_list)
        
        return panel
    
    def _create_message_detail_panel(self) -> QWidget:
        """메시지 상세 패널 생성"""
        panel = QWidget()
        panel.setStyleSheet(f"background-color: {Colors.BG_PRIMARY};")
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 섹션 헤더 (메시지 타입에 따라 텍스트 변경)
        # 모든 메시지가 이메일인지 확인
        is_all_email = all(msg.get("type") == "email" for msg in self.messages) if self.messages else False
        header_text = "  이메일 상세" if is_all_email else "  메시지 상세"
        
        self.detail_header_label = QLabel(header_text)
        self.detail_header_label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_BASE, QFont.Weight.Bold))
        self.detail_header_label.setStyleSheet(f"""
            QLabel {{
                background-color: {Colors.BG_SECONDARY};
                color: {Colors.TEXT_PRIMARY};
                padding: {Spacing.SM}px;
                border-bottom: 1px solid {Colors.BORDER_LIGHT};
            }}
        """)
        layout.addWidget(self.detail_header_label)
        
        # 스크롤 영역
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
            }
        """)
        
        # 상세 내용 컨테이너
        self.detail_container = QWidget()
        self.detail_layout = QVBoxLayout(self.detail_container)
        self.detail_layout.setContentsMargins(
            Spacing.MD, Spacing.MD, Spacing.MD, Spacing.MD
        )
        self.detail_layout.setSpacing(Spacing.MD)
        
        # 초기 메시지 제거 - 첫 번째 메시지가 자동으로 선택되므로 불필요
        self.detail_layout.addStretch()
        
        scroll_area.setWidget(self.detail_container)
        layout.addWidget(scroll_area)
        
        return panel
    
    def _populate_messages(self):
        """메시지 목록 채우기"""
        if not self.messages:
            # 빈 메시지 그룹 처리
            item = QListWidgetItem("메시지가 없습니다")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.message_list.addItem(item)
            logger.warning("빈 메시지 그룹")
            return
        
        for idx, message in enumerate(self.messages):
            try:
                item_widget = self._create_message_list_item(message, idx)
                item = QListWidgetItem(self.message_list)
                item.setSizeHint(item_widget.sizeHint())
                self.message_list.addItem(item)
                self.message_list.setItemWidget(item, item_widget)
            except Exception as e:
                logger.error(f"메시지 목록 항목 생성 오류: {e}")
                continue
    
    def _create_message_list_item(
        self,
        message: Dict[str, Any],
        index: int
    ) -> QWidget:
        """메시지 목록 항목 위젯 생성"""
        widget = QWidget()
        widget.setMinimumHeight(80)  # 최소 높이 설정으로 레이아웃 깨짐 방지
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(Spacing.SM, Spacing.SM, Spacing.SM, Spacing.SM)
        layout.setSpacing(Spacing.XS)
        
        # 첫 번째 줄: 발신자 + 타입 아이콘
        first_line = QHBoxLayout()
        first_line.setSpacing(Spacing.XS)
        
        # 메시지 타입 아이콘
        msg_type = message.get("type", "messenger")
        type_icon = get_message_type_icon(msg_type)
        type_label = QLabel(type_icon)
        type_label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM))
        first_line.addWidget(type_label)
        
        # 발신자
        sender = message.get("sender", "Unknown")
        sender_label = QLabel(sender)
        sender_label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM, QFont.Weight.Bold))
        sender_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")
        first_line.addWidget(sender_label)
        
        first_line.addStretch()
        
        # 우선순위 아이콘 (우선순위 정보가 있는 경우만 표시)
        priority = message.get("priority")
        if not priority:
            metadata = message.get("metadata", {})
            priority = metadata.get("priority")
        
        # 우선순위가 있고 low가 아닌 경우만 표시
        if priority and priority != "low":
            priority_icon = get_priority_icon(priority)
            priority_label = QLabel(priority_icon)
            priority_label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM))
            first_line.addWidget(priority_label)
        
        layout.addLayout(first_line)
        
        # 두 번째 줄: 제목 또는 첫 줄
        subject = self._get_message_preview(message)
        subject_label = QLabel(subject)
        subject_label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM))
        subject_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
        subject_label.setWordWrap(True)
        layout.addWidget(subject_label)
        
        # 세 번째 줄: 시간
        timestamp = self._format_timestamp(message)
        time_label = QLabel(timestamp)
        time_label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_XS))
        time_label.setStyleSheet(f"color: {Colors.TEXT_TERTIARY};")
        layout.addWidget(time_label)
        
        return widget
    
    def _get_message_preview(self, message: Dict[str, Any], max_length: int = 50) -> str:
        """메시지 미리보기 텍스트 생성"""
        # 제목 우선
        subject = message.get("subject", "")
        if subject:
            if len(subject) > max_length:
                return subject[:max_length] + "..."
            return subject
        
        # 내용 첫 줄
        content = ""
        if isinstance(message.get("content"), str):
            content = message["content"]
        elif isinstance(message.get("content"), dict):
            content = message["content"].get("text", "")
        
        if content:
            first_line = content.split('\n')[0]
            if len(first_line) > max_length:
                return first_line[:max_length] + "..."
            return first_line
        
        return "(내용 없음)"
    
    def _format_timestamp(self, message: Dict[str, Any]) -> str:
        """타임스탬프 포맷팅"""
        # 다양한 시간 필드 시도
        timestamp = message.get("date") or message.get("timestamp") or message.get("sent_at")
        if not timestamp:
            return "시간 정보 없음"
        
        try:
            if isinstance(timestamp, str):
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            elif isinstance(timestamp, datetime):
                dt = timestamp
            else:
                return str(timestamp)
            
            return dt.strftime("%Y-%m-%d %H:%M")
        except Exception as e:
            logger.error(f"타임스탬프 포맷팅 오류: {e}")
            return str(timestamp)
    
    def _on_message_selected(self, current_row: int):
        """메시지 선택 이벤트 핸들러"""
        if current_row < 0 or current_row >= len(self.messages):
            return
        
        message = self.messages[current_row]
        self.display_message_detail(message)
    
    def display_message_detail(self, message: Dict[str, Any]):
        """메시지 상세 내용 표시"""
        # 기존 위젯 제거
        while self.detail_layout.count():
            item = self.detail_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        try:
            # 메타데이터 섹션
            metadata_widget = self._create_metadata_section(message)
            self.detail_layout.addWidget(metadata_widget)
            
            # 구분선
            separator = QWidget()
            separator.setFixedHeight(1)
            separator.setStyleSheet(f"background-color: {Colors.BORDER_LIGHT};")
            self.detail_layout.addWidget(separator)
            
            # 메시지 내용 섹션
            content_widget = self._create_content_section(message)
            self.detail_layout.addWidget(content_widget)
            
            # 수신자 목록 (이메일인 경우)
            if message.get("type") == "email":
                recipients_widget = self._create_recipients_section(message)
                if recipients_widget:
                    self.detail_layout.addWidget(recipients_widget)
            
            self.detail_layout.addStretch()
            
        except Exception as e:
            logger.error(f"메시지 상세 표시 오류: {e}")
            error_label = QLabel(f"메시지를 표시할 수 없습니다: {str(e)}")
            error_label.setStyleSheet(f"color: {Colors.ERROR};")
            self.detail_layout.addWidget(error_label)
            self.detail_layout.addStretch()
    
    def _create_metadata_section(self, message: Dict[str, Any]) -> QWidget:
        """메타데이터 섹션 생성"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.SM)
        
        # 제목 (이메일인 경우)
        subject = message.get("subject", "")
        if subject:
            subject_label = QLabel(subject)
            subject_label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_LG, QFont.Weight.Bold))
            subject_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")
            subject_label.setWordWrap(True)
            layout.addWidget(subject_label)
        
        # 메타데이터 그리드
        meta_layout = QHBoxLayout()
        meta_layout.setSpacing(Spacing.MD)
        
        # 발신자
        sender = message.get("sender", "Unknown")
        sender_label = QLabel(f"👤 {sender}")
        sender_label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM))
        sender_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
        meta_layout.addWidget(sender_label)
        
        # 시간
        timestamp = self._format_timestamp(message)
        time_label = QLabel(f"🕐 {timestamp}")
        time_label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM))
        time_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
        meta_layout.addWidget(time_label)
        
        # 유형
        msg_type = message.get("type", "messenger")
        type_icon = get_message_type_icon(msg_type)
        type_text = "이메일" if msg_type == "email" else "메신저"
        type_label = QLabel(f"{type_icon} {type_text}")
        type_label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM))
        type_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
        meta_layout.addWidget(type_label)
        
        # 우선순위 (정보가 있는 경우만 표시)
        priority = message.get("priority")
        if not priority:
            metadata = message.get("metadata", {})
            priority = metadata.get("priority")
        
        if priority:
            priority_icon = get_priority_icon(priority)
            priority_text = {"high": "높음", "medium": "중간", "low": "낮음"}.get(priority, priority)
            priority_label = QLabel(f"{priority_icon} {priority_text}")
            priority_label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM))
            priority_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
            meta_layout.addWidget(priority_label)
        
        meta_layout.addStretch()
        layout.addLayout(meta_layout)
        
        return widget
    
    def _create_content_section(self, message: Dict[str, Any]) -> QWidget:
        """메시지 내용 섹션 생성"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.SM)
        
        # 섹션 제목
        title_label = QLabel("메시지 내용")
        title_label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_BASE, QFont.Weight.Bold))
        title_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")
        layout.addWidget(title_label)
        
        # 내용 추출
        content = ""
        if isinstance(message.get("content"), str):
            content = message["content"]
        elif isinstance(message.get("content"), dict):
            content = message["content"].get("text", "")
        
        if not content:
            content = "(내용 없음)"
        
        # 스크롤 가능한 텍스트 영역
        content_text = QTextEdit()
        content_text.setReadOnly(True)
        content_text.setPlainText(content)
        content_text.setMinimumHeight(200)
        content_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {Colors.BG_SECONDARY};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER_LIGHT};
                border-radius: {BorderRadius.BASE}px;
                padding: {Spacing.SM}px;
                font-size: {Fonts.SIZE_SM}px;
                line-height: 1.5;
            }}
        """)
        layout.addWidget(content_text)
        
        return widget
    
    def _create_recipients_section(self, message: Dict[str, Any]) -> Optional[QWidget]:
        """수신자 목록 섹션 생성 (이메일 전용)"""
        recipients = message.get("recipients", [])
        if not recipients:
            return None
        
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.SM)
        
        # 섹션 제목
        title_label = QLabel("수신자")
        title_label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_BASE, QFont.Weight.Bold))
        title_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")
        layout.addWidget(title_label)
        
        # 수신자 목록
        if isinstance(recipients, list):
            recipients_text = ", ".join(recipients)
        else:
            recipients_text = str(recipients)
        
        recipients_label = QLabel(recipients_text)
        recipients_label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM))
        recipients_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
        recipients_label.setWordWrap(True)
        layout.addWidget(recipients_label)
        
        return widget
    
    def keyPressEvent(self, event):
        """키보드 이벤트 처리
        
        - 화살표 키: 메시지 목록 이동
        - Enter: 메시지 선택 (이미 선택된 경우 무시)
        - Esc: 다이얼로그 닫기
        """
        from PyQt6.QtCore import Qt
        
        key = event.key()
        
        # Esc 키: 다이얼로그 닫기
        if key == Qt.Key.Key_Escape:
            self.accept()
            return
        
        # 화살표 키: 메시지 목록 이동
        if key == Qt.Key.Key_Up:
            current_row = self.message_list.currentRow()
            if current_row > 0:
                self.message_list.setCurrentRow(current_row - 1)
            event.accept()
            return
        
        if key == Qt.Key.Key_Down:
            current_row = self.message_list.currentRow()
            if current_row < self.message_list.count() - 1:
                self.message_list.setCurrentRow(current_row + 1)
            event.accept()
            return
        
        # Enter 키: 메시지 선택 (이미 선택되어 있으므로 상세 내용 표시)
        if key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
            current_row = self.message_list.currentRow()
            if 0 <= current_row < len(self.messages):
                message = self.messages[current_row]
                self.display_message_detail(message)
            event.accept()
            return
        
        # 기타 키는 부모 클래스에 전달
        super().keyPressEvent(event)
