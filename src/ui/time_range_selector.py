# -*- coding: utf-8 -*-
"""
TimeRangeSelector 컴포넌트

시간 범위를 선택할 수 있는 UI 컴포넌트입니다.
사용자가 오프라인 기간을 시작/종료 시간으로 지정하고,
빠른 선택 버튼으로 자주 사용하는 범위를 쉽게 설정할 수 있습니다.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QDateTimeEdit, QMessageBox, QGroupBox
)
from PyQt6.QtCore import pyqtSignal, Qt, QDateTime

from .styles import Colors, FontSizes, FontWeights, Styles, Spacing, BorderRadius

logger = logging.getLogger(__name__)


class TimeRangeSelector(QWidget):
    """시간 범위 선택 위젯
    
    시작 시간과 종료 시간을 선택할 수 있는 UI 컴포넌트입니다.
    빠른 선택 버튼을 통해 자주 사용하는 시간 범위를 쉽게 설정할 수 있습니다.
    
    Signals:
        time_range_changed: 시간 범위가 변경되었을 때 발생 (start: datetime, end: datetime)
    """
    
    time_range_changed = pyqtSignal(datetime, datetime)
    
    def __init__(self, parent: Optional[QWidget] = None):
        """
        Args:
            parent: 부모 위젯
        """
        super().__init__(parent)

        # 시뮬레이션 시간 컨텍스트
        self._simulation_time: Optional[datetime] = None
        self._is_simulation_mode: bool = False

        self._init_ui()
        self._setup_default_range()
    
    def _init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.SM, Spacing.SM, Spacing.SM, Spacing.SM)
        layout.setSpacing(Spacing.SM)
        
        # 시작 시간 선택
        start_layout = QHBoxLayout()
        start_label = QLabel("시작:")
        start_label.setFixedWidth(50)
        start_label.setStyleSheet(f"font-size: {FontSizes.SM}; font-weight: {FontWeights.SEMIBOLD};")
        self.start_datetime = QDateTimeEdit()
        self.start_datetime.setCalendarPopup(True)
        self.start_datetime.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.start_datetime.setStyleSheet(f"font-size: {FontSizes.SM}; padding: 4px;")
        start_layout.addWidget(start_label)
        start_layout.addWidget(self.start_datetime)
        layout.addLayout(start_layout)
        
        # 종료 시간 선택
        end_layout = QHBoxLayout()
        end_label = QLabel("종료:")
        end_label.setFixedWidth(50)
        end_label.setStyleSheet(f"font-size: {FontSizes.SM}; font-weight: {FontWeights.SEMIBOLD};")
        self.end_datetime = QDateTimeEdit()
        self.end_datetime.setCalendarPopup(True)
        self.end_datetime.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.end_datetime.setStyleSheet(f"font-size: {FontSizes.SM}; padding: 4px;")
        end_layout.addWidget(end_label)
        end_layout.addWidget(self.end_datetime)
        layout.addLayout(end_layout)
        
        # 빠른 선택 버튼 그룹
        quick_group = QGroupBox("빠른 선택")
        quick_layout = QVBoxLayout(quick_group)
        quick_layout.setSpacing(Spacing.XS)
        quick_layout.setContentsMargins(Spacing.SM, Spacing.SM, Spacing.SM, Spacing.SM)
        
        # 첫 번째 줄: 최근 1시간, 4시간
        row1 = QHBoxLayout()
        row1.setSpacing(Spacing.XS)
        
        quick_button_style = f"""
            QPushButton {{
                background-color: {Colors.PRIMARY};
                color: white;
                border: none;
                padding: 6px;
                border-radius: 4px;
                font-weight: {FontWeights.SEMIBOLD};
                font-size: {FontSizes.XS};
            }}
            QPushButton:hover {{
                background-color: {Colors.PRIMARY_DARK};
            }}
            QPushButton:pressed {{
                background-color: {Colors.PRIMARY_DARK};
            }}
        """
        
        self.btn_1hour = QPushButton("최근 1시간")
        self.btn_1hour.clicked.connect(lambda: self._set_quick_range(hours=1))
        self.btn_1hour.setStyleSheet(quick_button_style)
        row1.addWidget(self.btn_1hour)
        
        self.btn_4hours = QPushButton("최근 4시간")
        self.btn_4hours.clicked.connect(lambda: self._set_quick_range(hours=4))
        self.btn_4hours.setStyleSheet(quick_button_style)
        row1.addWidget(self.btn_4hours)
        
        quick_layout.addLayout(row1)
        
        # 두 번째 줄: 오늘, 어제
        row2 = QHBoxLayout()
        row2.setSpacing(Spacing.XS)
        
        self.btn_today = QPushButton("오늘")
        self.btn_today.clicked.connect(self._set_today)
        self.btn_today.setStyleSheet(quick_button_style)
        row2.addWidget(self.btn_today)
        
        self.btn_yesterday = QPushButton("어제")
        self.btn_yesterday.clicked.connect(self._set_yesterday)
        self.btn_yesterday.setStyleSheet(quick_button_style)
        row2.addWidget(self.btn_yesterday)
        
        quick_layout.addLayout(row2)
        
        # 세 번째 줄: 최근 7일, 전체 기간
        row3 = QHBoxLayout()
        row3.setSpacing(Spacing.XS)
        
        self.btn_7days = QPushButton("최근 7일")
        self.btn_7days.clicked.connect(lambda: self._set_quick_range(days=7))
        self.btn_7days.setStyleSheet(quick_button_style)
        row3.addWidget(self.btn_7days)
        
        self.btn_all_time = QPushButton("전체 기간")
        self.btn_all_time.clicked.connect(self._set_all_time_range)
        self.btn_all_time.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.WARNING};
                color: white;
                border: none;
                padding: 6px;
                border-radius: 4px;
                font-weight: {FontWeights.SEMIBOLD};
                font-size: {FontSizes.XS};
            }}
            QPushButton:hover {{
                background-color: {Colors.WARNING_DARK};
            }}
            QPushButton:pressed {{
                background-color: {Colors.WARNING_DARK};
            }}
        """)
        row3.addWidget(self.btn_all_time)
        
        quick_layout.addLayout(row3)
        
        layout.addWidget(quick_group)
        
        # 적용 버튼
        self.apply_button = QPushButton("적용")
        self.apply_button.clicked.connect(self._apply_range)
        self.apply_button.setStyleSheet(Styles.button_success())
        layout.addWidget(self.apply_button)

    def set_simulation_context(self, sim_time: Optional[datetime] = None, is_simulation_mode: bool = False):
        """시뮬레이션 시간 컨텍스트 설정

        Args:
            sim_time: 시뮬레이션 현재 시간 (UTC aware datetime). None이면 실시간 모드
            is_simulation_mode: True면 시뮬레이션/리플레이 모드, False면 실시간 모드

        Examples:
            >>> # 리플레이 모드 (Day 30, 10:00)
            >>> selector.set_simulation_context(sim_time=datetime(...), is_simulation_mode=True)

            >>> # 실시간 모드로 복귀
            >>> selector.set_simulation_context(sim_time=None, is_simulation_mode=False)
        """
        self._simulation_time = sim_time
        self._is_simulation_mode = is_simulation_mode

        if is_simulation_mode and sim_time:
            logger.info(f"🎬 시뮬레이션 모드 활성화: {sim_time.isoformat()}")
        else:
            logger.info("⏱️ 실시간 모드 활성화")

    def _get_current_sim_time(self) -> datetime:
        """현재 시간 반환 (시뮬레이션 모드면 sim_time, 아니면 datetime.now())

        Returns:
            현재 시간 (datetime)
        """
        if self._is_simulation_mode and self._simulation_time:
            return self._simulation_time
        return datetime.now()

    def _setup_default_range(self):
        """기본 시간 범위 설정 (전체 기간 - 최근 30일)"""
        now = self._get_current_sim_time()
        # 기본값을 최근 30일로 설정하여 대부분의 데이터를 포함
        start = now - timedelta(days=30)

        self.start_datetime.setDateTime(QDateTime(start))
        self.end_datetime.setDateTime(QDateTime(now))
    
    def _set_all_time_range(self):
        """전체 기간 설정
        
        데이터셋의 실제 메시지 범위를 사용합니다.
        데이터 범위가 설정되지 않은 경우 부모 윈도우에서 데이터를 가져와 범위를 계산합니다.
        """
        # 1. 이미 설정된 데이터 범위가 있으면 사용
        if hasattr(self, '_data_start') and hasattr(self, '_data_end'):
            self.start_datetime.setDateTime(QDateTime(self._data_start))
            self.end_datetime.setDateTime(QDateTime(self._data_end))
            logger.info(f"📅 설정된 데이터 범위 사용: {self._data_start} ~ {self._data_end}")
        else:
            # 2. 부모 윈도우에서 실제 데이터를 가져와서 범위 계산
            data_range = self._get_actual_data_range()
            if data_range:
                start_time, end_time = data_range
                self.start_datetime.setDateTime(QDateTime(start_time))
                self.end_datetime.setDateTime(QDateTime(end_time))
                # 계산된 범위를 저장
                self._data_start = start_time
                self._data_end = end_time
                logger.info(f"📅 실제 데이터에서 범위 계산: {start_time} ~ {end_time}")
            else:
                # 3. 데이터를 찾을 수 없으면 최근 1년 사용
                now = self._get_current_sim_time()
                start = now - timedelta(days=365)
                self.start_datetime.setDateTime(QDateTime(start))
                self.end_datetime.setDateTime(QDateTime(now))
                logger.warning("📅 데이터를 찾을 수 없어 최근 1년으로 설정")
        
        # 시간 범위만 설정하고 자동 적용하지 않음 (다른 버튼들과 동일한 동작)
    
    def _get_actual_data_range(self) -> Optional[Tuple[datetime, datetime]]:
        """부모 윈도우에서 실제 데이터 범위 가져오기
        
        VirtualOffice에서 전체 데이터를 조회하여 실제 시간 범위를 계산합니다.
        
        Returns:
            (start_time, end_time) 튜플 또는 None
        """
        try:
            # 부모 윈도우 찾기
            parent = self.parent()
            while parent and not hasattr(parent, 'vo_client'):
                parent = parent.parent()
            
            if not parent:
                logger.warning("부모 윈도우를 찾을 수 없음")
                return None
            
            # VirtualOffice 클라이언트가 있으면 전체 데이터 조회
            if hasattr(parent, 'vo_client') and parent.vo_client and hasattr(parent, 'selected_persona') and parent.selected_persona:
                logger.info("🔍 VirtualOffice에서 전체 데이터 범위 조회 중...")
                
                try:
                    # 전체 이메일 조회 (since_id=None으로 전체 조회)
                    emails = parent.vo_client.get_emails(
                        mailbox=parent.selected_persona.email_address,
                        since_id=None  # 전체 조회
                    )
                    
                    # 전체 메시지 조회 (since_id=None으로 전체 조회)
                    messages = parent.vo_client.get_messages(
                        handle=parent.selected_persona.handle,
                        since_id=None  # 전체 조회
                    )
                    
                    all_messages = emails + messages
                    logger.info(f"📊 전체 데이터 조회 완료: 이메일 {len(emails)}개, 메시지 {len(messages)}개")
                    
                    if all_messages:
                        message_times = self._extract_times_from_messages(all_messages)
                        if message_times:
                            min_time = min(message_times)
                            max_time = max(message_times)
                            logger.info(f"📅 전체 데이터 범위: {min_time} ~ {max_time}")
                            return min_time, max_time
                    
                except Exception as vo_error:
                    logger.error(f"VirtualOffice 데이터 조회 오류: {vo_error}")
            
            # VirtualOffice 조회 실패 시 현재 수집된 메시지에서 범위 계산
            logger.info("현재 수집된 메시지에서 데이터 범위 계산")
            messages = getattr(parent, 'collected_messages', [])
            if not messages and hasattr(parent, 'assistant') and hasattr(parent.assistant, 'collected_messages'):
                messages = parent.assistant.collected_messages
            
            if messages:
                message_times = self._extract_times_from_messages(messages)
                if message_times:
                    return min(message_times), max(message_times)
            
            logger.warning("데이터를 찾을 수 없음")
            return None
            
        except Exception as e:
            logger.error(f"실제 데이터 범위 계산 오류: {e}")
            return None
    
    def _extract_times_from_messages(self, messages: list) -> list:
        """메시지 리스트에서 시간 정보 추출
        
        Args:
            messages: 메시지 리스트
            
        Returns:
            datetime 객체 리스트
        """
        message_times = []
        
        for message in messages:
            time_value = (
                message.get('simulated_datetime')
                or (message.get('metadata') or {}).get('simulated_datetime')
                or message.get('date')
                or message.get('timestamp')
                or message.get('sent_at')
                or message.get('created_at')
                or message.get('time')
            )

            if not time_value:
                continue

            try:
                if isinstance(time_value, str):
                    # ISO 형식 시도
                    if 'T' in time_value:
                        message_time = datetime.fromisoformat(time_value.replace('Z', '+00:00'))
                    else:
                        # 다른 형식들 시도
                        for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d']:
                            try:
                                message_time = datetime.strptime(time_value, fmt)
                                break
                            except ValueError:
                                continue
                        else:
                            continue
                elif isinstance(time_value, datetime):
                    message_time = time_value
                else:
                    continue

                message_times.append(message_time)

            except Exception:
                continue
        
        return message_times
    
    def set_data_range(self, start: datetime, end: datetime):
        """데이터의 실제 시간 범위 설정
        
        Args:
            start: 데이터의 가장 오래된 메시지 시간
            end: 데이터의 가장 최근 메시지 시간
        """
        self._data_start = start
        self._data_end = end
        
        # 기본 범위를 데이터 범위로 설정
        self.start_datetime.setDateTime(QDateTime(start))
        self.end_datetime.setDateTime(QDateTime(end))
    
    def _set_quick_range(self, hours: int = 0, days: int = 0):
        """빠른 선택 범위 설정

        데이터의 가장 최근 시간을 기준으로 지정된 시간만큼 이전부터의 범위를 설정합니다.
        시뮬레이션 모드에서는 시뮬레이션 시간을 기준으로 계산합니다.

        Args:
            hours: 최근 몇 시간 (기본값: 0)
            days: 최근 몇 일 (기본값: 0)

        Examples:
            >>> _set_quick_range(hours=4)  # 최근 4시간
            >>> _set_quick_range(days=7)   # 최근 7일
        """
        # 데이터의 가장 최근 시간을 기준으로 사용
        if hasattr(self, '_data_end'):
            end = self._data_end
        else:
            end = self._get_current_sim_time()

        if days > 0:
            start = end - timedelta(days=days)
        else:
            start = end - timedelta(hours=hours)

        self.start_datetime.setDateTime(QDateTime(start))
        self.end_datetime.setDateTime(QDateTime(end))
    
    def _set_today(self):
        """오늘 00:00 ~ 현재 시간으로 설정

        시뮬레이션 모드에서는 시뮬레이션 시간을 기준으로 "오늘"을 계산합니다.
        """
        now = self._get_current_sim_time()
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        self.start_datetime.setDateTime(QDateTime(start))
        self.end_datetime.setDateTime(QDateTime(now))
    
    def _set_yesterday(self):
        """어제 00:00 ~ 23:59로 설정

        시뮬레이션 모드에서는 시뮬레이션 시간을 기준으로 "어제"를 계산합니다.
        """
        now = self._get_current_sim_time()
        yesterday = now - timedelta(days=1)
        start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)

        self.start_datetime.setDateTime(QDateTime(start))
        self.end_datetime.setDateTime(QDateTime(end))
    
    def _apply_range(self):
        """선택한 시간 범위 적용 및 즉시 데이터 수집"""
        start = self.start_datetime.dateTime().toPyDateTime()
        end = self.end_datetime.dateTime().toPyDateTime()
        
        # 유효성 검증
        if not self._validate_range(start, end):
            return
        
        # 시그널 발생 (시간 범위 변경 + 즉시 수집 요청)
        self.time_range_changed.emit(start, end)
    
    def _validate_range(self, start: datetime, end: datetime) -> bool:
        """시간 범위 유효성 검증
        
        Args:
            start: 시작 시간
            end: 종료 시간
            
        Returns:
            유효하면 True, 그렇지 않으면 False
        """
        if end <= start:
            QMessageBox.warning(
                self,
                "유효하지 않은 시간 범위",
                "종료 시간은 시작 시간 이후여야 합니다."
            )
            return False
        
        return True
    
    def get_time_range(self) -> Tuple[datetime, datetime]:
        """선택된 시간 범위 반환
        
        사용자가 입력한 로컬 시간을 시스템 타임존으로 해석하고 UTC로 변환합니다.
        
        Returns:
            (시작 시간, 종료 시간) 튜플 (UTC aware datetime)
        """
        from datetime import timezone
        import time
        
        start = self.start_datetime.dateTime().toPyDateTime()
        end = self.end_datetime.dateTime().toPyDateTime()
        
        # naive datetime을 로컬 시간으로 간주하고 UTC로 변환
        if start.tzinfo is None:
            # 로컬 타임존 오프셋 계산 (초 단위)
            local_offset_seconds = -time.timezone if time.daylight == 0 else -time.altzone
            from datetime import timedelta
            local_tz = timezone(timedelta(seconds=local_offset_seconds))
            
            # 로컬 시간으로 해석
            start = start.replace(tzinfo=local_tz)
            # UTC로 변환
            start = start.astimezone(timezone.utc)
        
        if end.tzinfo is None:
            # 로컬 타임존 오프셋 계산
            local_offset_seconds = -time.timezone if time.daylight == 0 else -time.altzone
            from datetime import timedelta
            local_tz = timezone(timedelta(seconds=local_offset_seconds))
            
            # 로컬 시간으로 해석
            end = end.replace(tzinfo=local_tz)
            # UTC로 변환
            end = end.astimezone(timezone.utc)
        
        return (start, end)
    
    def set_time_range(self, start: datetime, end: datetime):
        """시간 범위 설정
        
        Args:
            start: 시작 시간
            end: 종료 시간
        """
        self.start_datetime.setDateTime(QDateTime(start))
        self.end_datetime.setDateTime(QDateTime(end))
    
    def reset_to_default(self):
        """기본값으로 리셋 (최근 30일)"""
        self._setup_default_range()
