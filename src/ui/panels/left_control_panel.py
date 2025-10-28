# -*- coding: utf-8 -*-
"""
왼쪽 제어 패널

시간 범위 선택, 제어 버튼, 날씨 정보 등을 담당합니다.
"""
import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QGroupBox, QPushButton,
    QProgressBar, QLineEdit, QHBoxLayout, QScrollArea, QFrame
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt, pyqtSignal

from ..time_range_selector import TimeRangeSelector
from ..widgets import StatusIndicator

logger = logging.getLogger(__name__)


class LeftControlPanel(QWidget):
    """왼쪽 제어 패널"""
    
    # 시그널 정의
    status_toggled = pyqtSignal()  # 상태 토글
    collection_started = pyqtSignal()  # 수집 시작
    collection_stopped = pyqtSignal()  # 수집 중지
    cleanup_requested = pyqtSignal()  # 정리 요청
    time_range_changed = pyqtSignal(object, object)  # 시간 범위 변경
    weather_update_requested = pyqtSignal(str)  # 날씨 업데이트
    daily_summary_requested = pyqtSignal()  # 일일 요약
    weekly_summary_requested = pyqtSignal()  # 주간 요약
    connect_vo_requested = pyqtSignal()  # VirtualOffice 연결
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
    
    def _init_ui(self):
        """UI 초기화"""
        # 메인 레이아웃 (스크롤 없이)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # 제목
        self._create_title(layout)
        
        # 상태 표시기
        self._create_status_indicator(layout)
        
        # 데이터 소스 정보
        self._create_datasource_info(layout)
        
        # 제어 버튼
        self._create_control_buttons(layout)
        
        # 진행률 및 상태 메시지
        self._create_progress_status(layout)
        
        # 시간 범위 선택기
        self._create_time_range_selector(layout)
        
        # 날씨 위젯
        self._create_weather_widget(layout)
        
        # 요약 버튼
        self._create_summary_buttons(layout)
    
    def _create_title(self, layout):
        """제목 생성"""
        title = QLabel("OFFLINE-AGENT")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #2c3e50; margin: 8px;")
        layout.addWidget(title)
    
    def _create_status_indicator(self, layout):
        """상태 표시기 생성"""
        status_group = QGroupBox("연결 상태")
        status_layout = QVBoxLayout(status_group)
        
        self.status_indicator = StatusIndicator()
        status_layout.addWidget(self.status_indicator)
        
        self.status_button = QPushButton("오프라인 → 온라인")
        self.status_button.clicked.connect(lambda: self.status_toggled.emit())
        self.status_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        status_layout.addWidget(self.status_button)
        
        layout.addWidget(status_group)
    
    def _create_datasource_info(self, layout):
        """데이터 소스 정보 생성"""
        dataset_group = QGroupBox("데이터 소스")
        dataset_layout = QVBoxLayout(dataset_group)
        
        info_label = QLabel("VirtualOffice 실시간 연동 전용")
        info_label.setWordWrap(True)
        info_label.setStyleSheet(
            "color: #059669; font-weight: 600; background: #D1FAE5; "
            "padding: 8px; border-radius: 4px;"
        )
        dataset_layout.addWidget(info_label)
        
        help_label = QLabel(
            "로컬 JSON 파일은 더 이상 지원하지 않습니다.\n"
            "아래 'VirtualOffice 연동' 섹션에서 실시간 연결을 설정하세요."
        )
        help_label.setWordWrap(True)
        help_label.setStyleSheet("color: #6B7280; font-size: 10px; padding: 4px;")
        dataset_layout.addWidget(help_label)
        
        layout.addWidget(dataset_group)
    
    def _create_control_buttons(self, layout):
        """제어 버튼 생성"""
        control_group = QGroupBox("제어")
        control_layout = QVBoxLayout(control_group)
        
        # VirtualOffice 연결 테스트 버튼
        self.vo_connect_btn = QPushButton("🔌 실시간 연결 테스트")
        self.vo_connect_btn.clicked.connect(lambda: self.connect_vo_requested.emit())
        self.vo_connect_btn.setStyleSheet("""
            QPushButton {
                background-color: #3B82F6;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #2563EB;
            }
            QPushButton:disabled {
                background-color: #9CA3AF;
            }
        """)
        control_layout.addWidget(self.vo_connect_btn)
        
        # 시작 버튼
        self.start_button = QPushButton("🔄 메시지 수집")
        self.start_button.clicked.connect(lambda: self.collection_started.emit())
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        control_layout.addWidget(self.start_button)
        
        # 중지 버튼
        self.stop_button = QPushButton("⏹️ 중지")
        self.stop_button.clicked.connect(lambda: self.collection_stopped.emit())
        self.stop_button.setEnabled(False)
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        control_layout.addWidget(self.stop_button)
        
        # 정리 버튼
        self.cleanup_button = QPushButton("🧹 정리")
        self.cleanup_button.clicked.connect(lambda: self.cleanup_requested.emit())
        self.cleanup_button.setStyleSheet("""
            QPushButton {
                background-color: #f39c12;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #e67e22;
            }
        """)
        control_layout.addWidget(self.cleanup_button)
        
        layout.addWidget(control_group)
    
    def _create_progress_status(self, layout):
        """진행률 및 상태 메시지 생성"""
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        self.status_message = QLabel("준비됨")
        self.status_message.setStyleSheet("color: #666; font-size: 10px; padding: 4px;")
        self.status_message.setWordWrap(True)
        layout.addWidget(self.status_message)
    
    def _create_time_range_selector(self, layout):
        """시간 범위 선택기 생성"""
        time_range_group = QGroupBox("⏰ 시간 범위 선택")
        time_range_layout = QVBoxLayout(time_range_group)
        
        self.time_range_selector = TimeRangeSelector()
        self.time_range_selector.time_range_changed.connect(
            lambda start, end: self.time_range_changed.emit(start, end)
        )
        time_range_layout.addWidget(self.time_range_selector)
        
        layout.addWidget(time_range_group)
    
    def _create_weather_widget(self, layout):
        """날씨 위젯 생성"""
        weather_group = QGroupBox("오늘/내일 날씨")
        weather_layout = QVBoxLayout(weather_group)
        
        self.weather_input = QLineEdit()
        self.weather_input.setPlaceholderText("도시 또는 지역 (예: 서울, Seoul)")
        self.weather_input.setText("서울")
        weather_layout.addWidget(self.weather_input)
        
        self.weather_button = QPushButton("날씨 업데이트")
        self.weather_button.clicked.connect(self._on_weather_update)
        self.weather_button.setStyleSheet("padding:6px 10px; font-weight:600;")
        weather_layout.addWidget(self.weather_button)
        
        self.weather_status_label = QLabel("위치를 입력하고 업데이트를 눌러주세요.")
        self.weather_status_label.setWordWrap(True)
        self.weather_status_label.setStyleSheet(
            "color:#1F2937; background:#F5F3FF; padding:6px; border-radius:6px;"
        )
        weather_layout.addWidget(self.weather_status_label)
        
        self.weather_tip_label = QLabel("날씨 팁을 준비 중입니다.")
        self.weather_tip_label.setWordWrap(True)
        self.weather_tip_label.setStyleSheet(
            "color:#4C1D95; background:#F5F3FF; padding:6px; "
            "border-radius:6px; font-size:12px;"
        )
        weather_layout.addWidget(self.weather_tip_label)
        
        layout.addWidget(weather_group)
    
    def _create_summary_buttons(self, layout):
        """요약 버튼 생성"""
        summary_group = QGroupBox("요약 빠른 보기")
        summary_layout = QHBoxLayout(summary_group)
        
        self.daily_summary_button = QPushButton("일일 요약")
        self.daily_summary_button.setStyleSheet("padding:6px 10px; font-weight:600;")
        self.daily_summary_button.clicked.connect(
            lambda: self.daily_summary_requested.emit()
        )
        summary_layout.addWidget(self.daily_summary_button)
        
        self.weekly_summary_button = QPushButton("주간 요약")
        self.weekly_summary_button.setStyleSheet("padding:6px 10px; font-weight:600;")
        self.weekly_summary_button.clicked.connect(
            lambda: self.weekly_summary_requested.emit()
        )
        summary_layout.addWidget(self.weekly_summary_button)
        
        layout.addWidget(summary_group)
    
    def _on_weather_update(self):
        """날씨 업데이트 버튼 클릭"""
        location = self.weather_input.text().strip()
        if location:
            self.weather_update_requested.emit(location)
    
    # Public 메서드들
    
    def set_progress_visible(self, visible):
        """진행률 바 표시/숨김"""
        self.progress_bar.setVisible(visible)
    
    def set_progress_value(self, value):
        """진행률 값 설정"""
        self.progress_bar.setValue(value)
    
    def set_progress_range(self, minimum, maximum):
        """진행률 범위 설정"""
        self.progress_bar.setRange(minimum, maximum)
    
    def set_status_message(self, message):
        """상태 메시지 설정"""
        self.status_message.setText(message)
    
    def set_buttons_enabled(self, start=None, stop=None, cleanup=None, vo_connect=None):
        """버튼 활성화/비활성화"""
        if start is not None:
            self.start_button.setEnabled(start)
        if stop is not None:
            self.stop_button.setEnabled(stop)
        if cleanup is not None:
            self.cleanup_button.setEnabled(cleanup)
        if vo_connect is not None:
            self.vo_connect_btn.setEnabled(vo_connect)
    
    def update_weather_status(self, status_text, tip_text=None):
        """날씨 상태 업데이트"""
        self.weather_status_label.setText(status_text)
        if tip_text:
            self.weather_tip_label.setText(tip_text)
    
    def get_time_range(self):
        """현재 선택된 시간 범위 반환"""
        return self.time_range_selector.get_time_range()
    
    def set_time_range(self, start_dt, end_dt):
        """시간 범위 설정"""
        self.time_range_selector.set_time_range(start_dt, end_dt)
