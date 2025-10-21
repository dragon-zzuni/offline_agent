# -*- coding: utf-8 -*-
"""
MessageSummaryPanel - 메시지 요약 패널

메시지 탭에서 요약 단위를 선택하고 그룹화된 요약을 표시하는 컴포넌트입니다.
"""

from typing import List, Dict, Optional
from datetime import datetime, timedelta

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QRadioButton, QButtonGroup, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QCursor
import logging

logger = logging.getLogger(__name__)

from .styles import (
    Colors, FontSizes, FontWeights, Styles, Spacing, BorderRadius,
    get_priority_colors, Icons, get_priority_icon, get_message_type_icon
)


class MessageSummaryPanel(QWidget):
    """메시지 요약 패널
    
    일/주/월 단위로 메시지를 그룹화하여 요약을 표시합니다.
    
    Signals:
        summary_unit_changed: 요약 단위가 변경되었을 때 발생 (str: "daily", "weekly", "monthly")
        summary_card_clicked: 요약 카드가 클릭되었을 때 발생 (dict: 요약 그룹 데이터)
    """
    
    summary_unit_changed = pyqtSignal(str)
    summary_card_clicked = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        """
        Args:
            parent: 부모 위젯
        """
        super().__init__(parent)
        self._current_unit = "daily"
        self._init_ui()
    
    def _init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.SM)
        
        # 상단: 요약 단위 선택
        unit_selector = self._create_unit_selector()
        layout.addWidget(unit_selector)
        
        # 하단: 스크롤 가능한 요약 리스트 영역
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # 요약 컨테이너
        self.summary_container = QWidget()
        self.summary_layout = QVBoxLayout(self.summary_container)
        self.summary_layout.setContentsMargins(Spacing.SM, Spacing.SM, Spacing.SM, Spacing.SM)
        self.summary_layout.setSpacing(Spacing.MD)
        self.summary_layout.addStretch()
        
        self.scroll_area.setWidget(self.summary_container)
        layout.addWidget(self.scroll_area)
        
        # 초기 메시지
        self._show_empty_message()
    
    def _create_unit_selector(self) -> QWidget:
        """요약 단위 선택 UI 생성
        
        Returns:
            요약 단위 선택 위젯
        """
        container = QFrame()
        container.setFrameStyle(QFrame.Shape.StyledPanel)
        container.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_TERTIARY};
                border: 1px solid {Colors.BORDER_LIGHT};
                border-radius: {BorderRadius.MD};
                padding: {Spacing.SM}px;
            }}
        """)
        
        layout = QHBoxLayout(container)
        layout.setContentsMargins(Spacing.BASE, Spacing.SM, Spacing.BASE, Spacing.SM)
        layout.setSpacing(Spacing.MD)
        
        # 라벨
        label = QLabel("요약 단위:")
        label.setStyleSheet(f"""
            font-weight: {FontWeights.SEMIBOLD};
            color: {Colors.TEXT_PRIMARY};
            font-size: {FontSizes.BASE};
        """)
        layout.addWidget(label)
        
        # 라디오 버튼 그룹
        self.button_group = QButtonGroup(self)
        
        radio_style = f"""
            QRadioButton {{
                color: {Colors.TEXT_PRIMARY};
                font-size: {FontSizes.BASE};
                font-weight: {FontWeights.MEDIUM};
            }}
            QRadioButton::indicator {{
                width: 16px;
                height: 16px;
            }}
            QRadioButton::indicator:checked {{
                background-color: {Colors.PRIMARY};
                border: 2px solid {Colors.PRIMARY};
                border-radius: 8px;
            }}
            QRadioButton::indicator:unchecked {{
                background-color: white;
                border: 2px solid {Colors.GRAY_300};
                border-radius: 8px;
            }}
        """
        
        self.daily_radio = QRadioButton("일별 요약")
        self.daily_radio.setChecked(True)
        self.daily_radio.setStyleSheet(radio_style)
        self.button_group.addButton(self.daily_radio, 0)
        layout.addWidget(self.daily_radio)
        
        self.weekly_radio = QRadioButton("주별 요약")
        self.weekly_radio.setStyleSheet(radio_style)
        self.button_group.addButton(self.weekly_radio, 1)
        layout.addWidget(self.weekly_radio)
        
        self.monthly_radio = QRadioButton("월별 요약")
        self.monthly_radio.setStyleSheet(radio_style)
        self.button_group.addButton(self.monthly_radio, 2)
        layout.addWidget(self.monthly_radio)
        
        layout.addStretch()
        
        # 시그널 연결
        self.button_group.buttonClicked.connect(self._on_unit_changed)
        
        return container
    
    def _on_unit_changed(self):
        """요약 단위 변경 이벤트 핸들러"""
        if self.daily_radio.isChecked():
            unit = "daily"
        elif self.weekly_radio.isChecked():
            unit = "weekly"
        elif self.monthly_radio.isChecked():
            unit = "monthly"
        else:
            unit = "daily"
        
        if unit != self._current_unit:
            self._current_unit = unit
            self.summary_unit_changed.emit(unit)
    
    def show_message_count(self, messenger_count: int, email_count: int):
        """메시지 수만 표시 (요약 생성 전)
        
        Args:
            messenger_count: 메신저 메시지 수
            email_count: 이메일 수
        """
        self.clear()
        
        count_label = QLabel(
            f"📨 메신저 {messenger_count}건 수집됨\n"
            f"📧 이메일 {email_count}건 (메일 탭에서 확인)\n\n"
            f"위에서 요약 단위를 선택하면 자동으로 요약이 생성됩니다."
        )
        count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        count_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-size: {FontSizes.BASE};
                font-weight: {FontWeights.MEDIUM};
                padding: 40px;
                line-height: 1.8;
            }}
        """)
        
        self.summary_layout.insertWidget(0, count_label)
    
    def set_summary_unit(self, unit: str):
        """요약 단위 설정
        
        Args:
            unit: 요약 단위 ("daily", "weekly", "monthly")
        """
        self._current_unit = unit
        
        if unit == "daily":
            self.daily_radio.setChecked(True)
        elif unit == "weekly":
            self.weekly_radio.setChecked(True)
        elif unit == "monthly":
            self.monthly_radio.setChecked(True)
    
    def get_summary_unit(self) -> str:
        """현재 선택된 요약 단위 반환
        
        Returns:
            요약 단위 문자열
        """
        return self._current_unit
    
    def _show_empty_message(self):
        """빈 상태 메시지 표시"""
        self.clear()
        
        empty_label = QLabel("메시지를 수집하면 요약이 표시됩니다.")
        empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_TERTIARY};
                font-size: {FontSizes.BASE};
                font-weight: {FontWeights.MEDIUM};
                padding: 40px;
            }}
        """)
        
        self.summary_layout.insertWidget(0, empty_label)
    
    def clear(self):
        """표시 내용 초기화"""
        # 기존 위젯 모두 제거
        while self.summary_layout.count() > 1:  # stretch 제외
            item = self.summary_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def display_summaries(self, summaries: List):
        """그룹화된 요약 표시
        
        각 그룹을 카드 형태로 표시합니다.
        
        Args:
            summaries: 그룹화된 요약 리스트 (GroupedSummary 객체 또는 딕셔너리)
        """
        self.clear()
        
        if not summaries:
            self._show_empty_message()
            return
        
        # 각 요약을 카드로 표시
        for summary in summaries:
            # GroupedSummary 객체인 경우 딕셔너리로 변환
            if hasattr(summary, "to_dict"):
                summary_dict = summary.to_dict()
            else:
                summary_dict = summary
            
            card = self._create_summary_card(summary_dict)
            self.summary_layout.insertWidget(self.summary_layout.count() - 1, card)
    
    def _create_summary_card(self, summary: Dict) -> QWidget:
        """요약 카드 위젯 생성
        
        Args:
            summary: 요약 데이터
            
        Returns:
            카드 위젯
        """
        card = QFrame()
        card.setFrameStyle(QFrame.Shape.StyledPanel)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_PRIMARY};
                border: 1px solid {Colors.BORDER_LIGHT};
                border-radius: {BorderRadius.MD};
                padding: {Spacing.MD}px;
            }}
            QFrame:hover {{
                border-color: {Colors.BORDER_MEDIUM};
                background-color: {Colors.GRAY_50};
            }}
        """)
        
        # 클릭 가능하도록 설정
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.mousePressEvent = lambda event: self._on_card_clicked(summary)
        
        layout = QVBoxLayout(card)
        layout.setSpacing(Spacing.SM)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 헤더: 날짜/기간
        header = self._create_card_header(summary)
        layout.addWidget(header)
        
        # 구분선
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: #E5E7EB;")
        layout.addWidget(separator)
        
        # 통계 정보
        stats = self._create_card_stats(summary)
        layout.addWidget(stats)
        
        # 주요 발신자 배지 (우선순위 포함)
        top_senders = summary.get("top_senders", [])
        sender_priority_map = summary.get("sender_priority_map", {})
        if top_senders:
            sender_badges = self._create_sender_badges(top_senders, sender_priority_map)
            layout.addWidget(sender_badges)
        
        # 핵심 요약 (1-2줄)
        brief_summary = summary.get("brief_summary", "")
        if brief_summary:
            summary_label = QLabel(brief_summary)
            summary_label.setWordWrap(True)
            summary_label.setStyleSheet(f"""
                QLabel {{
                    color: {Colors.TEXT_PRIMARY};
                    font-size: {FontSizes.SM};
                    line-height: 1.6;
                    padding: 8px 0;
                    font-weight: {FontWeights.MEDIUM};
                }}
            """)
            layout.addWidget(summary_label)
        
        # 주요 포인트
        key_points = summary.get("key_points", [])
        if key_points:
            points_widget = self._create_key_points(key_points)
            layout.addWidget(points_widget)
        
        return card
    
    def _create_card_header(self, summary: Dict) -> QWidget:
        """카드 헤더 생성 (날짜/기간 표시)"""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.SM)
        
        # 날짜/기간 텍스트
        period_text = self._format_period(summary)
        period_label = QLabel(period_text)
        period_label.setStyleSheet(f"""
            QLabel {{
                font-size: {FontSizes.XL};
                font-weight: {FontWeights.BOLD};
                color: {Colors.TEXT_PRIMARY};
            }}
        """)
        layout.addWidget(period_label)
        
        layout.addStretch()
        
        # 단위 배지
        unit = summary.get("unit", "daily")
        unit_text = {"daily": "일별", "weekly": "주별", "monthly": "월별"}.get(unit, unit)
        unit_badge = QLabel(unit_text)
        unit_badge.setStyleSheet(f"""
            QLabel {{
                background-color: {Colors.SECONDARY_BG};
                color: {Colors.SECONDARY_DARK};
                padding: 4px 12px;
                border-radius: 12px;
                font-size: {FontSizes.XS};
                font-weight: {FontWeights.SEMIBOLD};
            }}
        """)
        layout.addWidget(unit_badge)
        
        return container
    
    def _format_period(self, summary: Dict) -> str:
        """기간을 포맷팅
        
        Args:
            summary: 요약 딕셔너리
        """
        start = summary.get("period_start")
        end = summary.get("period_end")
        unit = summary.get("unit", "daily")
        
        # datetime 객체로 변환
        if isinstance(start, str):
            try:
                start = datetime.fromisoformat(start.replace("Z", "+00:00"))
            except Exception:
                start = None
        
        if isinstance(end, str):
            try:
                end = datetime.fromisoformat(end.replace("Z", "+00:00"))
            except Exception:
                end = None
        
        if not start:
            return "날짜 정보 없음"
        
        if unit == "daily":
            return start.strftime("%Y년 %m월 %d일 (%a)")
        elif unit == "weekly":
            if end:
                # 주간: 시작일 ~ 종료일 (실제 마지막 날짜 표시)
                # end는 다음 주 월요일 직전이므로 하루 빼기
                actual_end = end - timedelta(days=1) if end.hour == 23 else end
                if start.year == actual_end.year:
                    return f"{start.strftime('%Y년 %m/%d')} ~ {actual_end.strftime('%m/%d')}"
                else:
                    return f"{start.strftime('%Y년 %m/%d')} ~ {actual_end.strftime('%Y년 %m/%d')}"
            return start.strftime("%Y년 %W주차")
        elif unit == "monthly":
            # 월별: 년도와 월만 표시
            return start.strftime("%Y년 %m월")
        else:
            return start.strftime("%Y-%m-%d")
    
    def _create_card_stats(self, summary: Dict) -> QWidget:
        """카드 통계 정보 생성"""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.SM)
        
        # 총 메시지 수
        total = summary.get("total_messages", 0)
        total_label = self._create_stat_item(Icons.MESSAGE, f"총 {total}건")
        layout.addWidget(total_label)
        
        # 이메일/메신저 분포
        email_count = summary.get("email_count")
        messenger_count = summary.get("messenger_count")
        if email_count is not None and messenger_count is not None:
            # 이메일과 메신저를 별도 배지로 표시
            if email_count > 0:
                email_badge = self._create_count_badge(Icons.EMAIL, email_count, Colors.SECONDARY_BG, Colors.SECONDARY_DARK)
                layout.addWidget(email_badge)
            
            if messenger_count > 0:
                messenger_badge = self._create_count_badge(Icons.MESSENGER, messenger_count, Colors.PRIMARY_BG, Colors.PRIMARY_DARK)
                layout.addWidget(messenger_badge)
        
        # 우선순위 분포 (아이콘 포함)
        priority_dist = summary.get("priority_distribution", {})
        if priority_dist:
            high = priority_dist.get("high", 0)
            medium = priority_dist.get("medium", 0)
            low = priority_dist.get("low", 0)
            
            if high > 0:
                high_badge = self._create_count_badge(
                    get_priority_icon("high"), 
                    high, 
                    Colors.PRIORITY_HIGH_BG, 
                    Colors.PRIORITY_HIGH_TEXT
                )
                layout.addWidget(high_badge)
            
            if medium > 0:
                medium_badge = self._create_count_badge(
                    get_priority_icon("medium"), 
                    medium, 
                    Colors.PRIORITY_MEDIUM_BG, 
                    Colors.PRIORITY_MEDIUM_TEXT
                )
                layout.addWidget(medium_badge)
            
            if low > 0:
                low_badge = self._create_count_badge(
                    get_priority_icon("low"), 
                    low, 
                    Colors.PRIORITY_LOW_BG, 
                    Colors.PRIORITY_LOW_TEXT
                )
                layout.addWidget(low_badge)
        
        layout.addStretch()
        
        return container
    
    def _create_sender_badges(self, top_senders: List[tuple], priority_map: Dict[str, str]) -> QWidget:
        """발신자 배지 생성 (우선순위 해시태그 포함)"""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, Spacing.XS, 0, 0)
        layout.setSpacing(Spacing.SM)
        
        for sender, count in top_senders[:3]:
            # 발신자별 최고 우선순위
            priority = priority_map.get(sender, "").lower()
            
            # 우선순위별 색상 가져오기
            bg_color, text_color = get_priority_colors(priority)
            priority_tag = f" #{priority.capitalize()}" if priority in ["high", "medium"] else ""
            
            badge_text = f"{sender}({count}건){priority_tag}"
            
            badge = QLabel(badge_text)
            badge.setStyleSheet(f"""
                QLabel {{
                    background-color: {bg_color};
                    color: {text_color};
                    padding: 4px 10px;
                    border-radius: 12px;
                    font-size: {FontSizes.XS};
                    font-weight: {FontWeights.SEMIBOLD};
                }}
            """)
            layout.addWidget(badge)
        
        layout.addStretch()
        return container
    
    def _create_stat_item(self, icon: str, text: str) -> QLabel:
        """통계 항목 생성"""
        label = QLabel(f"{icon} {text}")
        label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-size: {FontSizes.SM};
                font-weight: {FontWeights.MEDIUM};
            }}
        """)
        return label
    
    def _create_count_badge(self, icon: str, count: int, bg_color: str, text_color: str) -> QLabel:
        """카운트 배지 생성
        
        Args:
            icon: 아이콘
            count: 개수
            bg_color: 배경색
            text_color: 텍스트 색상
            
        Returns:
            배지 라벨
        """
        badge = QLabel(f"{icon} {count}")
        badge.setStyleSheet(f"""
            QLabel {{
                background-color: {bg_color};
                color: {text_color};
                padding: 4px 10px;
                border-radius: 12px;
                font-size: {FontSizes.XS};
                font-weight: {FontWeights.SEMIBOLD};
            }}
        """)
        return badge
    
    def _create_key_points(self, points: List[str]) -> QWidget:
        """주요 포인트 위젯 생성"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, Spacing.SM, 0, 0)
        layout.setSpacing(Spacing.XS)
        
        # 제목
        title = QLabel("주요 포인트:")
        title.setStyleSheet(f"""
            QLabel {{
                font-weight: {FontWeights.SEMIBOLD};
                color: {Colors.TEXT_PRIMARY};
                font-size: {FontSizes.SM};
            }}
        """)
        layout.addWidget(title)
        
        # 포인트 리스트
        for point in points[:5]:  # 최대 5개만 표시
            point_label = QLabel(f"• {point}")
            point_label.setWordWrap(True)
            point_label.setStyleSheet(f"""
                QLabel {{
                    color: {Colors.TEXT_SECONDARY};
                    font-size: {FontSizes.SM};
                    padding-left: 8px;
                    line-height: 1.5;
                }}
            """)
            layout.addWidget(point_label)
        
        return container
    
    def _on_card_clicked(self, summary: Dict):
        """카드 클릭 이벤트 핸들러
        
        Args:
            summary: 클릭된 요약 그룹 데이터
        """
        logger.info(f"요약 카드 클릭: {summary.get('period_start', 'Unknown')}")
        self.summary_card_clicked.emit(summary)
