# -*- coding: utf-8 -*-
"""
NEW 배지 위젯
새 메일/메시지 도착 시 표시되는 배지 위젯
"""
import logging
from PyQt6.QtWidgets import QLabel, QWidget, QHBoxLayout
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QColor

logger = logging.getLogger(__name__)


class NewBadgeWidget(QLabel):
    """NEW 배지 위젯
    
    새 메일/메시지 도착 시 표시되는 배지입니다.
    3초 후 자동으로 페이드아웃 애니메이션과 함께 사라집니다.
    
    Attributes:
        _opacity: 현재 투명도 (0.0 ~ 1.0)
        fade_timer: 페이드아웃 타이머
        fade_animation: 페이드아웃 애니메이션
    """
    
    def __init__(self, parent: QWidget = None):
        """NewBadgeWidget 초기화
        
        Args:
            parent: 부모 위젯
        """
        super().__init__("NEW", parent)
        self._opacity = 1.0
        
        # 스타일 설정
        self.setStyleSheet("""
            QLabel {
                background-color: #EF4444;
                color: white;
                font-size: 10px;
                font-weight: bold;
                padding: 2px 6px;
                border-radius: 3px;
                margin-left: 4px;
            }
        """)
        
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedSize(40, 18)
        
        # 3초 후 페이드아웃 시작
        self.fade_timer = QTimer()
        self.fade_timer.setSingleShot(True)
        self.fade_timer.timeout.connect(self.start_fade_out)
        self.fade_timer.start(3000)  # 3초
        
        logger.debug("NEW 배지 생성됨")
    
    def start_fade_out(self):
        """페이드아웃 애니메이션 시작"""
        # 투명도 애니메이션 (1.0 → 0.0)
        self.fade_animation = QPropertyAnimation(self, b"opacity")
        self.fade_animation.setDuration(500)  # 0.5초
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.fade_animation.finished.connect(self.hide)
        self.fade_animation.start()
        
        logger.debug("NEW 배지 페이드아웃 시작")
    
    @pyqtProperty(float)
    def opacity(self):
        """투명도 getter"""
        return self._opacity
    
    @opacity.setter
    def opacity(self, value: float):
        """투명도 setter
        
        Args:
            value: 투명도 (0.0 ~ 1.0)
        """
        self._opacity = value
        self.setWindowOpacity(value)
        
        # 스타일시트에 투명도 적용
        alpha = int(255 * value)
        self.setStyleSheet(f"""
            QLabel {{
                background-color: rgba(239, 68, 68, {alpha});
                color: rgba(255, 255, 255, {alpha});
                font-size: 10px;
                font-weight: bold;
                padding: 2px 6px;
                border-radius: 3px;
                margin-left: 4px;
            }}
        """)


class MessageItemWidget(QWidget):
    """메시지 아이템 위젯 (NEW 배지 포함)
    
    메시지 목록에 표시되는 아이템 위젯입니다.
    새 메시지인 경우 NEW 배지를 표시합니다.
    
    Attributes:
        message_label: 메시지 내용 레이블
        badge: NEW 배지 (새 메시지인 경우)
    """
    
    def __init__(self, message_text: str, is_new: bool = False, parent: QWidget = None):
        """MessageItemWidget 초기화
        
        Args:
            message_text: 메시지 텍스트
            is_new: 새 메시지 여부
            parent: 부모 위젯
        """
        super().__init__(parent)
        
        # 레이아웃 설정
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(4)
        
        # 메시지 레이블
        self.message_label = QLabel(message_text)
        self.message_label.setWordWrap(True)
        layout.addWidget(self.message_label, 1)
        
        # NEW 배지 (새 메시지인 경우)
        self.badge = None
        if is_new:
            self.badge = NewBadgeWidget(self)
            layout.addWidget(self.badge)
        
        layout.addStretch()
    
    def set_new_badge(self, show: bool = True):
        """NEW 배지 표시/숨김
        
        Args:
            show: 표시 여부
        """
        if show and not self.badge:
            # 배지 생성
            self.badge = NewBadgeWidget(self)
            self.layout().insertWidget(1, self.badge)
        elif not show and self.badge:
            # 배지 제거
            self.badge.hide()
            self.badge.deleteLater()
            self.badge = None
