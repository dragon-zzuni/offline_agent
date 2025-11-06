"""
SimulationMonitor - VirtualOffice 시뮬레이션 상태 모니터링

이 모듈은 VirtualOffice 시뮬레이션의 상태를 주기적으로 폴링하고
틱 진행 및 상태 변경을 감지하여 UI에 알립니다.
"""

import logging
from typing import Optional, List
from collections import deque
from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from .virtualoffice_client import VirtualOfficeClient
from .models import SimulationStatus, TickHistoryEntry

logger = logging.getLogger(__name__)


class SimulationMonitor(QObject):
    """시뮬레이션 상태 모니터링 클래스
    
    VirtualOffice 시뮬레이션의 상태를 주기적으로 조회하고
    틱 진행 및 상태 변경을 감지하여 시그널을 발생시킵니다.
    
    Signals:
        status_updated: 시뮬레이션 상태가 업데이트될 때 발생 (SimulationStatus)
        tick_advanced: 틱이 진행될 때 발생 (int: new_tick)
        error_occurred: 오류 발생 시 (str: error_message)
    """
    
    # 시그널 정의
    status_updated = pyqtSignal(object)  # SimulationStatus 객체
    tick_advanced = pyqtSignal(int)      # 새로운 틱 번호
    error_occurred = pyqtSignal(str)     # 오류 메시지
    
    def __init__(self, client: VirtualOfficeClient, parent: Optional[QObject] = None):
        """SimulationMonitor 초기화
        
        Args:
            client: VirtualOfficeClient 인스턴스
            parent: 부모 QObject (선택적)
        """
        super().__init__(parent)
        
        self.client = client
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._poll_status)
        
        # 상태 추적
        self.current_tick: int = 0
        self.is_monitoring: bool = False
        self.polling_interval_ms: int = 2000  # 기본 2초
        
        # 틱 히스토리 추적 (최근 100개)
        self.tick_history: deque[TickHistoryEntry] = deque(maxlen=100)
        self.current_tick_entry: Optional[TickHistoryEntry] = None
        
        logger.info("SimulationMonitor 초기화 완료")
    
    def start_monitoring(self, interval_ms: int = 2000) -> None:
        """모니터링 시작
        
        Args:
            interval_ms: 폴링 간격 (밀리초, 기본 2000ms = 2초)
        """
        if self.is_monitoring:
            logger.warning("이미 모니터링 중입니다")
            return
        
        self.polling_interval_ms = interval_ms
        self.timer.start(interval_ms)
        self.is_monitoring = True
        
        logger.info(f"시뮬레이션 모니터링 시작 (간격: {interval_ms}ms)")
        
        # 즉시 한 번 폴링
        self._poll_status()
    
    def stop_monitoring(self) -> None:
        """모니터링 중지"""
        if not self.is_monitoring:
            logger.warning("모니터링이 실행 중이 아닙니다")
            return
        
        self.timer.stop()
        self.is_monitoring = False
        
        logger.info("시뮬레이션 모니터링 중지")
    
    def set_polling_interval(self, interval_ms: int) -> None:
        """폴링 간격 조정
        
        Args:
            interval_ms: 새로운 폴링 간격 (밀리초)
        """
        self.polling_interval_ms = interval_ms
        
        if self.is_monitoring:
            self.timer.setInterval(interval_ms)
            logger.info(f"폴링 간격 변경: {interval_ms}ms")
    
    def _poll_status(self) -> None:
        """시뮬레이션 상태 폴링 (내부 메서드)
        
        VirtualOffice API에서 시뮬레이션 상태를 조회하고
        변경 사항을 감지하여 시그널을 발생시킵니다.
        """
        try:
            # 시뮬레이션 상태 조회
            status = self.client.get_simulation_status()
            
            # 틱 변경 감지
            if status.current_tick != self.current_tick:
                # 이전 틱 항목을 히스토리에 추가
                if self.current_tick_entry is not None:
                    self.tick_history.append(self.current_tick_entry)
                    logger.debug(
                        f"틱 {self.current_tick_entry.tick} 히스토리 추가: "
                        f"이메일 {self.current_tick_entry.email_count}, "
                        f"메시지 {self.current_tick_entry.message_count}"
                    )
                
                # 새 틱 항목 생성
                old_tick = self.current_tick
                self.current_tick = status.current_tick
                self.current_tick_entry = TickHistoryEntry(
                    tick=status.current_tick,
                    sim_time=status.sim_time
                )
                
                logger.info(f"틱 진행 감지: {old_tick} -> {status.current_tick}")
                self.tick_advanced.emit(status.current_tick)
            
            # 상태 업데이트 시그널 발생
            self.status_updated.emit(status)
            
        except Exception as e:
            error_msg = f"시뮬레이션 상태 조회 실패: {e}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
    
    def record_new_data(self, email_count: int = 0, message_count: int = 0) -> None:
        """현재 틱에 새 데이터 기록
        
        Args:
            email_count: 새로 수집된 이메일 수
            message_count: 새로 수집된 메시지 수
        """
        if self.current_tick_entry is not None:
            self.current_tick_entry.email_count += email_count
            self.current_tick_entry.message_count += message_count
            logger.debug(
                f"틱 {self.current_tick_entry.tick} 데이터 기록: "
                f"+{email_count} 이메일, +{message_count} 메시지"
            )
    
    def get_tick_history(self, limit: Optional[int] = None) -> List[TickHistoryEntry]:
        """틱 히스토리 조회
        
        Args:
            limit: 반환할 최대 항목 수 (None이면 전체)
        
        Returns:
            List[TickHistoryEntry]: 틱 히스토리 목록 (최신순)
        """
        history = list(self.tick_history)
        history.reverse()  # 최신순으로 정렬
        
        if limit is not None:
            history = history[:limit]
        
        return history
    
    def clear_history(self) -> None:
        """틱 히스토리 초기화"""
        self.tick_history.clear()
        self.current_tick_entry = None
        logger.info("틱 히스토리 초기화 완료")
