# -*- coding: utf-8 -*-
"""
AnalysisResultPanel - 분석 결과 패널

분석 결과를 좌우 분할 레이아웃으로 표시하는 컴포넌트입니다.
- 좌측: 요약 영역 (일일/주간 요약, 통계)
- 우측: 상세 분석 영역 (우선순위별 메시지 카드)
"""

from typing import List, Dict, Optional
from datetime import datetime
from collections import Counter

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QScrollArea, QFrame, QSplitter, QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from .styles import (
    Colors, FontSizes, FontWeights, Styles, Spacing, BorderRadius,
    get_priority_colors, Icons, get_priority_icon, get_message_type_icon
)


class AnalysisResultPanel(QWidget):
    """분석 결과 패널
    
    좌우 분할 레이아웃으로 요약과 상세 분석을 표시합니다.
    """
    
    def __init__(self, parent=None):
        """
        Args:
            parent: 부모 위젯
        """
        super().__init__(parent)
        self._analysis_results = []
        self._messages = []
        self._current_persona_ids = []
        self._init_ui()
    
    def _init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # QSplitter로 좌우 분할
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background-color: {Colors.BORDER_LIGHT};
            }}
        """)
        
        # 좌측: 요약 영역 (30%)
        left_panel = self._create_summary_panel()
        splitter.addWidget(left_panel)
        
        # 우측: 상세 분석 영역 (70%)
        right_panel = self._create_detail_panel()
        splitter.addWidget(right_panel)
        
        # 초기 비율 설정 (30:70)
        splitter.setSizes([300, 700])
        
        layout.addWidget(splitter)
    
    def _create_summary_panel(self) -> QWidget:
        """좌측 요약 패널 생성"""
        panel = QWidget()
        panel.setStyleSheet(f"""
            QWidget {{
                background-color: {Colors.BG_SECONDARY};
            }}
        """)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(Spacing.MD, Spacing.MD, Spacing.MD, Spacing.MD)
        layout.setSpacing(Spacing.MD)
        
        # 제목
        title = QLabel("📊 분석 요약")
        title.setStyleSheet(f"""
            QLabel {{
                font-size: {FontSizes.XL};
                font-weight: {FontWeights.BOLD};
                color: {Colors.TEXT_PRIMARY};
                padding-bottom: {Spacing.SM}px;
            }}
        """)
        layout.addWidget(title)
        
        # 스크롤 영역
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # 요약 컨테이너
        self.summary_container = QWidget()
        self.summary_layout = QVBoxLayout(self.summary_container)
        self.summary_layout.setContentsMargins(0, 0, 0, 0)
        self.summary_layout.setSpacing(Spacing.MD)
        self.summary_layout.addStretch()
        
        scroll_area.setWidget(self.summary_container)
        layout.addWidget(scroll_area)
        
        # 초기 메시지
        self._show_empty_summary()
        
        return panel
    
    def _create_detail_panel(self) -> QWidget:
        """우측 상세 분석 패널 생성"""
        panel = QWidget()
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(Spacing.MD, Spacing.MD, Spacing.MD, Spacing.MD)
        layout.setSpacing(Spacing.MD)
        
        # 제목
        title = QLabel("📋 상세 분석")
        title.setStyleSheet(f"""
            QLabel {{
                font-size: {FontSizes.XL};
                font-weight: {FontWeights.BOLD};
                color: {Colors.TEXT_PRIMARY};
                padding-bottom: {Spacing.SM}px;
            }}
        """)
        layout.addWidget(title)
        
        # 스크롤 영역
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        # 스크롤 영역이 내용에 맞게 크기 조정되도록 설정
        scroll_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # 상세 컨테이너
        self.detail_container = QWidget()
        # 컨테이너가 스크롤 영역에 맞게 크기 조정되도록 설정
        self.detail_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        
        self.detail_layout = QVBoxLayout(self.detail_container)
        self.detail_layout.setContentsMargins(0, 0, 0, 0)
        self.detail_layout.setSpacing(Spacing.MD)
        self.detail_layout.addStretch()
        
        scroll_area.setWidget(self.detail_container)
        layout.addWidget(scroll_area)
        
        # 초기 메시지
        self._show_empty_detail()
        
        return panel
    
    def _show_empty_summary(self):
        """빈 요약 메시지 표시"""
        self._clear_layout(self.summary_layout)
        
        empty_label = QLabel("분석 결과가 없습니다.\n메시지를 수집하면 요약이 표시됩니다.")
        empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_TERTIARY};
                font-size: {FontSizes.BASE};
                padding: {Spacing.XL}px;
            }}
        """)
        
        self.summary_layout.insertWidget(0, empty_label)
    
    def _show_empty_detail(self):
        """빈 상세 메시지 표시"""
        self._clear_layout(self.detail_layout)
        
        empty_label = QLabel("분석 결과가 없습니다.\n메시지를 수집하면 상세 분석이 표시됩니다.")
        empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_TERTIARY};
                font-size: {FontSizes.BASE};
                padding: {Spacing.XL}px;
            }}
        """)
        
        self.detail_layout.insertWidget(0, empty_label)
    
    def _clear_layout(self, layout: QVBoxLayout):
        """레이아웃 내용 초기화"""
        while layout.count() > 1:  # stretch 제외
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def update_analysis(self, analysis_results: List[Dict], messages: List[Dict], current_persona_ids: Optional[List[str]] = None):
        """분석 결과 업데이트
        
        Args:
            analysis_results: 분석 결과 리스트
            messages: 원본 메시지 리스트
            current_persona_ids: 현재 페르소나의 sender IDs (이메일, 채팅 핸들 등)
        """
        self._analysis_results = analysis_results or []
        self._messages = messages or []
        self._current_persona_ids = current_persona_ids or []
        
        if not self._analysis_results:
            self._show_empty_summary()
            self._show_empty_detail()
            return
        
        # 요약 업데이트
        self._update_summary()
        
        # 상세 분석 업데이트
        self._update_detail()
    
    def _update_summary(self):
        """요약 영역 업데이트"""
        self._clear_layout(self.summary_layout)
        
        # 전체 통계 카드
        stats_card = self._create_stats_card()
        self.summary_layout.insertWidget(0, stats_card)
        
        # 우선순위 분포 카드
        priority_card = self._create_priority_distribution_card()
        self.summary_layout.insertWidget(1, priority_card)
        
        # 주요 발신자 카드
        sender_card = self._create_top_senders_card()
        self.summary_layout.insertWidget(2, sender_card)
    
    def _update_detail(self):
        """상세 분석 영역 업데이트"""
        self._clear_layout(self.detail_layout)
        
        # 우선순위별로 그룹화
        high_priority = []
        medium_priority = []
        low_priority = []
        
        for result in self._analysis_results:
            priority = result.get("priority", {}).get("priority_level", "low").lower()
            if priority == "high":
                high_priority.append(result)
            elif priority == "medium":
                medium_priority.append(result)
            else:
                low_priority.append(result)
        
        # High 우선순위 섹션
        if high_priority:
            high_section = self._create_priority_section("High", high_priority, Colors.PRIORITY_HIGH_TEXT)
            self.detail_layout.insertWidget(self.detail_layout.count() - 1, high_section)
        
        # Medium 우선순위 섹션
        if medium_priority:
            medium_section = self._create_priority_section("Medium", medium_priority, Colors.PRIORITY_MEDIUM_TEXT)
            self.detail_layout.insertWidget(self.detail_layout.count() - 1, medium_section)
        
        # Low 우선순위 섹션
        if low_priority:
            low_section = self._create_priority_section("Low", low_priority, Colors.PRIORITY_LOW_TEXT)
            self.detail_layout.insertWidget(self.detail_layout.count() - 1, low_section)
    
    def _create_stats_card(self) -> QWidget:
        """전체 통계 카드 생성"""
        card = QFrame()
        card.setFrameStyle(QFrame.Shape.StyledPanel)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_PRIMARY};
                border: 1px solid {Colors.BORDER_LIGHT};
                border-radius: {BorderRadius.MD};
                padding: {Spacing.MD}px;
            }}
        """)
        
        layout = QVBoxLayout(card)
        layout.setSpacing(Spacing.SM)
        
        # 제목
        title = QLabel("📈 전체 통계")
        title.setStyleSheet(f"""
            QLabel {{
                font-size: {FontSizes.LG};
                font-weight: {FontWeights.BOLD};
                color: {Colors.TEXT_PRIMARY};
            }}
        """)
        layout.addWidget(title)
        
        # 통계 정보
        total_messages = len(self._messages)
        total_analysis = len(self._analysis_results)
        
        email_count = sum(1 for m in self._messages if m.get("type", "").lower() == "email")
        messenger_count = total_messages - email_count
        
        total_actions = sum(len(r.get("actions", [])) for r in self._analysis_results)
        
        stats_text = f"""
        <div style="line-height: 1.8;">
        <b>총 메시지:</b> {total_messages}건<br>
        <b>분석 완료:</b> {total_analysis}건<br>
        <b>이메일:</b> {email_count}건 | <b>메신저:</b> {messenger_count}건<br>
        <b>추출된 액션:</b> {total_actions}건
        </div>
        """
        
        stats_label = QLabel(stats_text)
        stats_label.setWordWrap(True)
        stats_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-size: {FontSizes.SM};
            }}
        """)
        layout.addWidget(stats_label)
        
        return card
    
    def _create_priority_distribution_card(self) -> QWidget:
        """우선순위 분포 카드 생성"""
        card = QFrame()
        card.setFrameStyle(QFrame.Shape.StyledPanel)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_PRIMARY};
                border: 1px solid {Colors.BORDER_LIGHT};
                border-radius: {BorderRadius.MD};
                padding: {Spacing.MD}px;
            }}
        """)
        
        layout = QVBoxLayout(card)
        layout.setSpacing(Spacing.SM)
        
        # 제목
        title = QLabel("🎯 우선순위 분포")
        title.setStyleSheet(f"""
            QLabel {{
                font-size: {FontSizes.LG};
                font-weight: {FontWeights.BOLD};
                color: {Colors.TEXT_PRIMARY};
            }}
        """)
        layout.addWidget(title)
        
        # 우선순위 카운트
        priority_counts = Counter()
        for result in self._analysis_results:
            priority = result.get("priority", {}).get("priority_level", "low").lower()
            priority_counts[priority] += 1
        
        high_count = priority_counts.get("high", 0)
        medium_count = priority_counts.get("medium", 0)
        low_count = priority_counts.get("low", 0)
        
        # 우선순위 배지
        badges_layout = QHBoxLayout()
        badges_layout.setSpacing(Spacing.SM)
        
        if high_count > 0:
            high_badge = self._create_count_badge(
                get_priority_icon("high"), 
                f"High: {high_count}", 
                Colors.PRIORITY_HIGH_BG, 
                Colors.PRIORITY_HIGH_TEXT
            )
            badges_layout.addWidget(high_badge)
        
        if medium_count > 0:
            medium_badge = self._create_count_badge(
                get_priority_icon("medium"), 
                f"Medium: {medium_count}", 
                Colors.PRIORITY_MEDIUM_BG, 
                Colors.PRIORITY_MEDIUM_TEXT
            )
            badges_layout.addWidget(medium_badge)
        
        if low_count > 0:
            low_badge = self._create_count_badge(
                get_priority_icon("low"), 
                f"Low: {low_count}", 
                Colors.PRIORITY_LOW_BG, 
                Colors.PRIORITY_LOW_TEXT
            )
            badges_layout.addWidget(low_badge)
        
        badges_layout.addStretch()
        layout.addLayout(badges_layout)
        
        return card
    
    def _create_top_senders_card(self) -> QWidget:
        """주요 발신자 카드 생성"""
        card = QFrame()
        card.setFrameStyle(QFrame.Shape.StyledPanel)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_PRIMARY};
                border: 1px solid {Colors.BORDER_LIGHT};
                border-radius: {BorderRadius.MD};
                padding: {Spacing.MD}px;
            }}
        """)
        
        layout = QVBoxLayout(card)
        layout.setSpacing(Spacing.SM)
        
        # 제목
        title = QLabel("👥 주요 발신자")
        title.setStyleSheet(f"""
            QLabel {{
                font-size: {FontSizes.LG};
                font-weight: {FontWeights.BOLD};
                color: {Colors.TEXT_PRIMARY};
            }}
        """)
        layout.addWidget(title)
        
        # 발신자 카운트 (현재 페르소나 제외)
        sender_counts = Counter()
        for msg in self._messages:
            sender = msg.get("sender", "Unknown")
            # 현재 페르소나가 발신한 메시지는 제외 (이메일, 채팅 핸들 모두 체크)
            if sender in self._current_persona_ids:
                continue
            sender_counts[sender] += 1
        
        # 상위 5명
        top_senders = sender_counts.most_common(5)
        
        for sender, count in top_senders:
            sender_label = QLabel(f"• {sender}: {count}건")
            sender_label.setStyleSheet(f"""
                QLabel {{
                    color: {Colors.TEXT_SECONDARY};
                    font-size: {FontSizes.SM};
                    padding: 2px 0;
                }}
            """)
            layout.addWidget(sender_label)
        
        return card
    
    def _create_count_badge(self, icon: str, text: str, bg_color: str, text_color: str) -> QLabel:
        """카운트 배지 생성"""
        badge = QLabel(f"{icon} {text}")
        badge.setStyleSheet(f"""
            QLabel {{
                background-color: {bg_color};
                color: {text_color};
                padding: 6px 12px;
                border-radius: 12px;
                font-size: {FontSizes.SM};
                font-weight: {FontWeights.SEMIBOLD};
            }}
        """)
        return badge
    
    def _create_priority_section(self, priority_name: str, results: List[Dict], color: str) -> QWidget:
        """우선순위 섹션 생성"""
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setSpacing(Spacing.SM)
        layout.setContentsMargins(0, 0, 0, Spacing.MD)
        
        # 섹션 헤더
        header = QLabel(f"{get_priority_icon(priority_name.lower())} {priority_name} 우선순위 ({len(results)}건)")
        header.setStyleSheet(f"""
            QLabel {{
                font-size: {FontSizes.LG};
                font-weight: {FontWeights.BOLD};
                color: {color};
                padding-bottom: {Spacing.SM}px;
            }}
        """)
        layout.addWidget(header)
        
        # 메시지 카드들
        for result in results[:10]:  # 최대 10개만 표시
            card = self._create_message_card(result)
            layout.addWidget(card)
        
        if len(results) > 10:
            more_label = QLabel(f"... 외 {len(results) - 10}건 더")
            more_label.setStyleSheet(f"""
                QLabel {{
                    color: {Colors.TEXT_TERTIARY};
                    font-size: {FontSizes.SM};
                    font-style: italic;
                    padding: {Spacing.SM}px;
                }}
            """)
            layout.addWidget(more_label)
        
        return section
    
    def _create_message_card(self, result: Dict) -> QWidget:
        """메시지 카드 생성 (상세 정보 포함)"""
        card = QFrame()
        card.setFrameStyle(QFrame.Shape.StyledPanel)
        # 카드가 내용에 맞게 크기 조정되도록 설정
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
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
        
        layout = QVBoxLayout(card)
        layout.setSpacing(Spacing.SM)
        layout.setContentsMargins(Spacing.MD, Spacing.MD, Spacing.MD, Spacing.MD)
        
        # 메시지 정보
        msg = result.get("message", {})
        sender = msg.get("sender", "Unknown")
        subject = msg.get("subject", "") or msg.get("content", "")[:50]
        msg_type = msg.get("type", "").lower()
        
        # 1. 발신자 정보
        sender_layout = QHBoxLayout()
        type_icon = get_message_type_icon(msg_type)
        sender_label = QLabel(f"{type_icon} 발신자: {sender}")
        sender_label.setStyleSheet(f"""
            QLabel {{
                font-size: {FontSizes.BASE};
                font-weight: {FontWeights.BOLD};
                color: {Colors.TEXT_PRIMARY};
            }}
        """)
        sender_layout.addWidget(sender_label)
        sender_layout.addStretch()
        layout.addLayout(sender_layout)
        
        # 2. 수신 시간 정보
        date_str = msg.get("date") or msg.get("timestamp")
        if date_str:
            try:
                dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                time_text = f"🕐 수신: {dt.strftime('%Y-%m-%d %H:%M')}"
                time_label = QLabel(time_text)
                time_label.setStyleSheet(f"""
                    QLabel {{
                        color: {Colors.TEXT_TERTIARY};
                        font-size: {FontSizes.XS};
                        font-style: italic;
                    }}
                """)
                layout.addWidget(time_label)
            except:
                pass
        
        # 3. 수신자 및 참조 정보
        recipients = msg.get("recipients") or msg.get("to", [])
        cc = msg.get("cc", [])
        
        if recipients or cc:
            recipient_text = ""
            if recipients:
                # recipients가 리스트가 아닐 수 있으므로 처리
                if isinstance(recipients, list):
                    recipient_text += f"수신: {', '.join(str(r) for r in recipients[:2])}"
                    if len(recipients) > 2:
                        recipient_text += f" 외 {len(recipients) - 2}명"
                else:
                    recipient_text += f"수신: {recipients}"
            if cc:
                if recipient_text:
                    recipient_text += " | "
                # cc가 리스트가 아닐 수 있으므로 처리
                if isinstance(cc, list):
                    recipient_text += f"참조: {', '.join(str(c) for c in cc[:2])}"
                    if len(cc) > 2:
                        recipient_text += f" 외 {len(cc) - 2}명"
                else:
                    recipient_text += f"참조: {cc}"
            
            recipient_label = QLabel(recipient_text)
            recipient_label.setWordWrap(True)  # 텍스트 줄바꿈 활성화
            recipient_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
            recipient_label.setStyleSheet(f"""
                QLabel {{
                    color: {Colors.TEXT_SECONDARY};
                    font-size: {FontSizes.XS};
                    background-color: {Colors.BG_TERTIARY};
                    padding: 4px 8px;
                    border-radius: 4px;
                }}
            """)
            layout.addWidget(recipient_label)
        
        # 4. 제목/내용
        if subject:
            subject_label = QLabel(f"내용: {subject}")
            subject_label.setWordWrap(True)  # 텍스트 줄바꿈 활성화
            subject_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
            subject_label.setStyleSheet(f"""
                QLabel {{
                    color: {Colors.TEXT_SECONDARY};
                    font-size: {FontSizes.SM};
                    padding: 4px 0;
                }}
            """)
            layout.addWidget(subject_label)
        
        # 5. 액션 태그
        actions = result.get("actions", [])
        if actions:
            action_layout = QHBoxLayout()
            action_layout.setSpacing(Spacing.XS)
            
            action_label = QLabel(f"📋 액션 {len(actions)}개:")
            action_label.setStyleSheet(f"""
                QLabel {{
                    color: {Colors.TEXT_PRIMARY};
                    font-size: {FontSizes.XS};
                    font-weight: {FontWeights.SEMIBOLD};
                }}
            """)
            action_layout.addWidget(action_label)
            
            # 액션 태그 (최대 2개)
            for action in actions[:2]:
                action_title = action.get("title", "") or action.get("description", "") or action.get("task", "")
                if action_title:
                    # 액션 제목을 짧게 자르기
                    short_title = action_title[:20] + "..." if len(action_title) > 20 else action_title
                    action_tag = QLabel(short_title)
                    action_tag.setWordWrap(True)  # 텍스트 줄바꿈 활성화
                    action_tag.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
                    action_tag.setStyleSheet(f"""
                        QLabel {{
                            background-color: {Colors.PRIMARY_BG};
                            color: {Colors.PRIMARY_DARK};
                            padding: 2px 8px;
                            border-radius: 8px;
                            font-size: {FontSizes.XS};
                            font-weight: {FontWeights.MEDIUM};
                        }}
                    """)
                    action_layout.addWidget(action_tag)
            
            action_layout.addStretch()
            layout.addLayout(action_layout)
        
        return card
