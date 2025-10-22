# -*- coding: utf-8 -*-
"""
시각적 알림 효과
새 데이터 도착 시 시각적 알림을 표시하는 모듈
"""
import logging
from PyQt6.QtWidgets import QWidget, QGraphicsOpacityEffect
from PyQt6.QtCore import QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QColor, QPalette

logger = logging.getLogger(__name__)


class VisualNotification:
    """시각적 알림 효과 관리자
    
    위젯에 시각적 알림 효과를 적용합니다.
    새 데이터 도착 시 배경색 변경 애니메이션을 표시합니다.
    
    Attributes:
        widget: 대상 위젯
        original_style: 원본 스타일시트
        notification_timer: 알림 타이머
    """
    
    def __init__(self, widget: QWidget):
        """VisualNotification 초기화
        
        Args:
            widget: 알림을 표시할 위젯
        """
        self.widget = widget
        self.original_style = widget.styleSheet()
        self.notification_timer = None
        
        logger.debug(f"VisualNotification 초기화: {widget.__class__.__name__}")
    
    def show_notification(self, duration_ms: int = 500):
        """알림 효과 표시
        
        배경색을 변경하여 알림을 표시하고,
        지정된 시간 후 원래 스타일로 복원합니다.
        
        Args:
            duration_ms: 알림 표시 시간 (밀리초, 기본값: 500ms)
        """
        # 기존 타이머가 있으면 중지
        if self.notification_timer:
            self.notification_timer.stop()
        
        # 알림 스타일 적용 (밝은 파란색 배경)
        notification_style = self.original_style + """
            QWidget {
                background-color: #DBEAFE;
                border: 2px solid #3B82F6;
            }
        """
        self.widget.setStyleSheet(notification_style)
        
        # 지정된 시간 후 원래 스타일로 복원
        self.notification_timer = QTimer()
        self.notification_timer.setSingleShot(True)
        self.notification_timer.timeout.connect(self._restore_style)
        self.notification_timer.start(duration_ms)
        
        logger.debug(f"알림 효과 표시: {duration_ms}ms")
    
    def _restore_style(self):
        """원래 스타일로 복원"""
        self.widget.setStyleSheet(self.original_style)
        logger.debug("알림 효과 종료")


class FlashNotification:
    """플래시 알림 효과
    
    위젯에 플래시 효과를 적용합니다.
    빠르게 깜빡이는 효과로 사용자의 주의를 끕니다.
    
    Attributes:
        widget: 대상 위젯
        flash_count: 깜빡임 횟수
        flash_timer: 플래시 타이머
        current_flash: 현재 깜빡임 카운트
        original_style: 원본 스타일시트
    """
    
    def __init__(self, widget: QWidget, flash_count: int = 2):
        """FlashNotification 초기화
        
        Args:
            widget: 알림을 표시할 위젯
            flash_count: 깜빡임 횟수 (기본값: 2)
        """
        self.widget = widget
        self.flash_count = flash_count
        self.flash_timer = None
        self.current_flash = 0
        self.original_style = widget.styleSheet()
        self.is_highlighted = False
        
        logger.debug(f"FlashNotification 초기화: {widget.__class__.__name__}, 횟수={flash_count}")
    
    def start_flash(self, interval_ms: int = 250):
        """플래시 효과 시작
        
        Args:
            interval_ms: 깜빡임 간격 (밀리초, 기본값: 250ms)
        """
        self.current_flash = 0
        self.is_highlighted = False
        
        # 플래시 타이머 시작
        self.flash_timer = QTimer()
        self.flash_timer.timeout.connect(self._toggle_flash)
        self.flash_timer.start(interval_ms)
        
        logger.debug(f"플래시 효과 시작: 간격={interval_ms}ms")
    
    def _toggle_flash(self):
        """플래시 토글"""
        if self.is_highlighted:
            # 원래 스타일로 복원
            self.widget.setStyleSheet(self.original_style)
            self.is_highlighted = False
            self.current_flash += 1
            
            # 지정된 횟수만큼 깜빡였으면 종료
            if self.current_flash >= self.flash_count:
                self.flash_timer.stop()
                logger.debug("플래시 효과 종료")
        else:
            # 하이라이트 스타일 적용
            highlight_style = self.original_style + """
                QWidget {
                    background-color: #FEF3C7;
                    border: 2px solid #F59E0B;
                }
            """
            self.widget.setStyleSheet(highlight_style)
            self.is_highlighted = True


class PulseAnimation:
    """펄스 애니메이션 효과
    
    위젯에 펄스(맥박) 효과를 적용합니다.
    크기가 커졌다 작아지는 애니메이션으로 주의를 끕니다.
    
    Attributes:
        widget: 대상 위젯
        animation: 크기 애니메이션
    """
    
    def __init__(self, widget: QWidget):
        """PulseAnimation 초기화
        
        Args:
            widget: 애니메이션을 적용할 위젯
        """
        self.widget = widget
        self.animation = None
        
        logger.debug(f"PulseAnimation 초기화: {widget.__class__.__name__}")
    
    def start_pulse(self, duration_ms: int = 500):
        """펄스 애니메이션 시작
        
        Args:
            duration_ms: 애니메이션 시간 (밀리초, 기본값: 500ms)
        """
        # 투명도 효과 생성
        opacity_effect = QGraphicsOpacityEffect(self.widget)
        self.widget.setGraphicsEffect(opacity_effect)
        
        # 투명도 애니메이션 (1.0 → 0.5 → 1.0)
        self.animation = QPropertyAnimation(opacity_effect, b"opacity")
        self.animation.setDuration(duration_ms)
        self.animation.setStartValue(1.0)
        self.animation.setKeyValueAt(0.5, 0.5)
        self.animation.setEndValue(1.0)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.animation.finished.connect(self._cleanup)
        self.animation.start()
        
        logger.debug(f"펄스 애니메이션 시작: {duration_ms}ms")
    
    def _cleanup(self):
        """애니메이션 정리"""
        # 그래픽 효과 제거
        self.widget.setGraphicsEffect(None)
        logger.debug("펄스 애니메이션 종료")


class NotificationManager:
    """알림 관리자
    
    여러 위젯에 대한 알림 효과를 관리합니다.
    
    Attributes:
        notifications: 위젯별 알림 객체 딕셔너리
    """
    
    def __init__(self):
        """NotificationManager 초기화"""
        self.notifications = {}
        logger.debug("NotificationManager 초기화")
    
    def register_widget(self, widget: QWidget, notification_type: str = "visual"):
        """위젯 등록
        
        Args:
            widget: 등록할 위젯
            notification_type: 알림 타입 ("visual", "flash", "pulse")
        """
        if notification_type == "visual":
            self.notifications[widget] = VisualNotification(widget)
        elif notification_type == "flash":
            self.notifications[widget] = FlashNotification(widget)
        elif notification_type == "pulse":
            self.notifications[widget] = PulseAnimation(widget)
        else:
            logger.warning(f"알 수 없는 알림 타입: {notification_type}")
            return
        
        logger.debug(f"위젯 등록: {widget.__class__.__name__}, 타입={notification_type}")
    
    def show_notification(self, widget: QWidget, **kwargs):
        """알림 표시
        
        Args:
            widget: 알림을 표시할 위젯
            **kwargs: 알림 타입별 추가 인자
        """
        if widget not in self.notifications:
            logger.warning(f"등록되지 않은 위젯: {widget.__class__.__name__}")
            return
        
        notification = self.notifications[widget]
        
        if isinstance(notification, VisualNotification):
            notification.show_notification(kwargs.get("duration_ms", 500))
        elif isinstance(notification, FlashNotification):
            notification.start_flash(kwargs.get("interval_ms", 250))
        elif isinstance(notification, PulseAnimation):
            notification.start_pulse(kwargs.get("duration_ms", 500))
        
        logger.debug(f"알림 표시: {widget.__class__.__name__}")
    
    def unregister_widget(self, widget: QWidget):
        """위젯 등록 해제
        
        Args:
            widget: 등록 해제할 위젯
        """
        if widget in self.notifications:
            del self.notifications[widget]
            logger.debug(f"위젯 등록 해제: {widget.__class__.__name__}")
