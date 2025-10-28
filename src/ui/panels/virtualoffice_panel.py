# -*- coding: utf-8 -*-
"""
VirtualOffice 연동 패널

VirtualOffice 서버 연결, 페르소나 선택, 시뮬레이션 상태 표시 등을 담당합니다.
"""
import logging
from PyQt6.QtWidgets import (
    QGroupBox, QVBoxLayout, QLabel, QComboBox, QLineEdit, 
    QPushButton, QFrame, QWidget, QProgressBar
)
from PyQt6.QtCore import pyqtSignal

logger = logging.getLogger(__name__)


class VirtualOfficePanel(QGroupBox):
    """VirtualOffice 연동 패널"""
    
    # 시그널 정의
    connect_requested = pyqtSignal()  # 연결 테스트 요청
    persona_changed = pyqtSignal(int)  # 페르소나 변경
    tick_history_requested = pyqtSignal()  # 틱 히스토리 요청
    
    def __init__(self, parent=None):
        super().__init__("🌐 VirtualOffice 연동", parent)
        self._init_ui()
    
    def _init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        
        # 정보 레이블
        info_label = QLabel("✅ VirtualOffice 실시간 연동 전용")
        info_label.setStyleSheet(
            "color: #059669; font-weight: 600; background: #D1FAE5; "
            "padding: 6px; border-radius: 4px;"
        )
        layout.addWidget(info_label)
        
        # 페르소나 선택
        self._create_persona_section(layout)
        
        # 연결 상태 표시
        self._create_connection_status(layout)
        
        # 구분선
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet("background-color: #E5E7EB; margin: 8px 0;")
        layout.addWidget(separator)
        
        # 서버 설정
        self._create_server_settings(layout)
        
        # 시뮬레이션 상태
        self._create_simulation_status(layout)
        
        # 틱 히스토리 버튼
        self._create_tick_history_button(layout)
    
    def _create_persona_section(self, layout):
        """페르소나 선택 섹션 생성"""
        persona_label = QLabel("👤 사용자 페르소나:")
        persona_label.setStyleSheet(
            "font-weight: 700; color: #1F2937; margin-top: 8px; font-size: 13px;"
        )
        layout.addWidget(persona_label)
        
        self.persona_combo = QComboBox()
        self.persona_combo.setEnabled(False)
        self.persona_combo.currentIndexChanged.connect(
            lambda idx: self.persona_changed.emit(idx)
        )
        self.persona_combo.setStyleSheet("""
            QComboBox {
                padding: 8px;
                border: 2px solid #3B82F6;
                border-radius: 6px;
                background: white;
                font-weight: 600;
                font-size: 12px;
            }
            QComboBox:disabled {
                background-color: #F3F4F6;
                color: #9CA3AF;
                border-color: #D1D5DB;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 7px solid #3B82F6;
                margin-right: 10px;
            }
            QComboBox:disabled::down-arrow {
                border-top-color: #9CA3AF;
            }
        """)
        layout.addWidget(self.persona_combo)
    
    def _create_connection_status(self, layout):
        """연결 상태 표시 생성"""
        self.connection_status_label = QLabel("❌ 연결되지 않음")
        self.connection_status_label.setStyleSheet("""
            QLabel {
                color: #DC2626;
                background-color: #FEE2E2;
                padding: 6px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: 600;
            }
        """)
        self.connection_status_label.setWordWrap(True)
        layout.addWidget(self.connection_status_label)
    
    def _create_server_settings(self, layout):
        """서버 설정 섹션 생성"""
        settings_label = QLabel("⚙️ 서버 설정 (고급):")
        settings_label.setStyleSheet(
            "font-weight: 600; color: #6B7280; margin-top: 4px; font-size: 11px;"
        )
        layout.addWidget(settings_label)
        
        # Email Server
        layout.addWidget(QLabel("Email Server:"))
        self.email_url_input = QLineEdit("http://127.0.0.1:8000")
        self.email_url_input.setPlaceholderText("예: http://127.0.0.1:8000")
        self._apply_input_style(self.email_url_input)
        layout.addWidget(self.email_url_input)
        
        # Chat Server
        layout.addWidget(QLabel("Chat Server:"))
        self.chat_url_input = QLineEdit("http://127.0.0.1:8001")
        self.chat_url_input.setPlaceholderText("예: http://127.0.0.1:8001")
        self._apply_input_style(self.chat_url_input)
        layout.addWidget(self.chat_url_input)
        
        # Sim Manager
        layout.addWidget(QLabel("Sim Manager:"))
        self.sim_url_input = QLineEdit("http://127.0.0.1:8015")
        self.sim_url_input.setPlaceholderText("예: http://127.0.0.1:8015")
        self._apply_input_style(self.sim_url_input)
        layout.addWidget(self.sim_url_input)
    
    def _create_simulation_status(self, layout):
        """시뮬레이션 상태 섹션 생성"""
        sim_label = QLabel("시뮬레이션 상태:")
        sim_label.setStyleSheet("font-weight: 600; color: #374151; margin-top: 8px;")
        layout.addWidget(sim_label)
        
        # 상태 컨테이너
        status_container = QWidget()
        status_layout = QVBoxLayout(status_container)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(4)
        
        # 실행 상태
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
        status_layout.addWidget(self.sim_running_status)
        
        # 틱 진행률 바
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
        status_layout.addWidget(self.sim_progress_bar)
        
        # 상세 정보
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
        self.sim_status_display.setWordWrap(True)
        status_layout.addWidget(self.sim_status_display)
        
        layout.addWidget(status_container)
    
    def _create_tick_history_button(self, layout):
        """틱 히스토리 버튼 생성"""
        self.tick_history_btn = QPushButton("📊 틱 히스토리 보기")
        self.tick_history_btn.clicked.connect(
            lambda: self.tick_history_requested.emit()
        )
        self.tick_history_btn.setEnabled(False)
        self.tick_history_btn.setStyleSheet("""
            QPushButton {
                background-color: #10B981;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #059669;
            }
            QPushButton:disabled {
                background-color: #9CA3AF;
            }
        """)
        layout.addWidget(self.tick_history_btn)
    
    def _apply_input_style(self, widget):
        """입력 필드 스타일 적용"""
        widget.setStyleSheet("""
            QLineEdit {
                padding: 6px;
                border: 1px solid #D1D5DB;
                border-radius: 4px;
                background: white;
            }
            QLineEdit:focus {
                border-color: #3B82F6;
            }
        """)
    
    # Public 메서드들
    
    def get_server_urls(self):
        """서버 URL 반환"""
        return {
            'email': self.email_url_input.text().strip(),
            'chat': self.chat_url_input.text().strip(),
            'sim': self.sim_url_input.text().strip()
        }
    
    def set_server_urls(self, email_url, chat_url, sim_url):
        """서버 URL 설정"""
        self.email_url_input.setText(email_url)
        self.chat_url_input.setText(chat_url)
        self.sim_url_input.setText(sim_url)
    
    def update_connection_status(self, text, style_type='disconnected'):
        """연결 상태 업데이트
        
        Args:
            text: 표시할 텍스트
            style_type: 'connected', 'disconnected', 'waiting' 중 하나
        """
        styles = {
            'connected': """
                QLabel {
                    color: #059669;
                    background-color: #D1FAE5;
                    padding: 6px;
                    border-radius: 4px;
                    font-size: 11px;
                    font-weight: 600;
                }
            """,
            'disconnected': """
                QLabel {
                    color: #DC2626;
                    background-color: #FEE2E2;
                    padding: 6px;
                    border-radius: 4px;
                    font-size: 11px;
                    font-weight: 600;
                }
            """,
            'waiting': """
                QLabel {
                    color: #2563EB;
                    background-color: #DBEAFE;
                    padding: 6px;
                    border-radius: 4px;
                    font-size: 11px;
                    font-weight: 600;
                }
            """
        }
        
        self.connection_status_label.setText(text)
        self.connection_status_label.setStyleSheet(styles.get(style_type, styles['disconnected']))
    
    def set_persona_enabled(self, enabled):
        """페르소나 콤보박스 활성화/비활성화"""
        self.persona_combo.setEnabled(enabled)
    
    def set_tick_history_enabled(self, enabled):
        """틱 히스토리 버튼 활성화/비활성화"""
        self.tick_history_btn.setEnabled(enabled)
    
    def update_sim_status(self, running_text, progress_value, progress_max, detail_text):
        """시뮬레이션 상태 업데이트"""
        self.sim_running_status.setText(running_text)
        self.sim_progress_bar.setMaximum(progress_max)
        self.sim_progress_bar.setValue(progress_value)
        self.sim_status_display.setText(detail_text)
