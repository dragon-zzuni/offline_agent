# -*- coding: utf-8 -*-
"""
Polling Worker
백그라운드에서 주기적으로 새 데이터를 수집하는 워커 스레드
"""
import logging
import time
from typing import Dict, Any, Optional, TYPE_CHECKING
from PyQt6.QtCore import QThread, pyqtSignal

if TYPE_CHECKING:
    from data_sources.virtualoffice_source import VirtualOfficeDataSource

logger = logging.getLogger(__name__)


class PollingWorker(QThread):
    """백그라운드 폴링 워커
    
    VirtualOffice API에서 주기적으로 새 데이터를 수집하는 워커 스레드입니다.
    증분 수집(since_id)을 사용하여 효율적으로 새 메일/메시지만 조회합니다.
    
    Signals:
        new_data_received: 새 데이터 도착 시 발생
            - emails: 새 이메일 리스트
            - messages: 새 채팅 메시지 리스트
            - timestamp: 수집 시간 (ISO 8601)
        error_occurred: 오류 발생 시 발생
            - error_message: 오류 메시지
    
    Attributes:
        data_source: VirtualOfficeDataSource 인스턴스
        polling_interval: 폴링 간격 (초)
        running: 워커 실행 상태
    """
    
    # 시그널 정의
    new_data_received = pyqtSignal(dict)  # {"emails": [...], "messages": [...], "timestamp": "..."}
    error_occurred = pyqtSignal(str)      # 오류 메시지
    
    def __init__(self, data_source: "VirtualOfficeDataSource", polling_interval: int = 5):
        """PollingWorker 초기화
        
        Args:
            data_source: VirtualOfficeDataSource 인스턴스
            polling_interval: 폴링 간격 (초, 기본값: 5)
        """
        super().__init__()
        self.data_source = data_source
        self.polling_interval = polling_interval
        self.running = False
        
        # 오류 처리 관련
        self.consecutive_failures = 0
        self.max_consecutive_failures = 3
        self.backoff_factor = 2.0
        
        logger.info(f"PollingWorker 초기화: 폴링 간격={polling_interval}초")

    def run(self) -> None:
        """폴링 루프 실행
        
        워커 스레드의 메인 루프입니다.
        polling_interval 간격으로 새 데이터를 조회하고,
        새 데이터가 있으면 new_data_received 시그널을 발생시킵니다.
        
        오류 발생 시 exponential backoff를 사용하여 재시도합니다.
        """
        self.running = True
        logger.info("폴링 워커 시작")
        
        while self.running:
            try:
                # 증분 수집 (since_id 사용)
                import asyncio
                from datetime import datetime
                
                # 비동기 함수를 동기적으로 실행
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    new_messages = loop.run_until_complete(
                        self.data_source.collect_messages({"incremental": True})
                    )
                finally:
                    loop.close()
                
                # 성공 시 연속 실패 카운터 리셋
                self.consecutive_failures = 0
                
                # 새 데이터가 있으면 시그널 발생
                if new_messages:
                    # 이메일과 채팅 메시지 분리
                    emails = [m for m in new_messages if m.get("type") == "email"]
                    messages = [m for m in new_messages if m.get("type") == "messenger"]
                    
                    data = {
                        "emails": emails,
                        "messages": messages,
                        "timestamp": datetime.now().isoformat(),
                        "all_messages": new_messages  # 전체 메시지도 포함
                    }
                    
                    logger.info(
                        f"새 데이터 수집: 이메일 {len(emails)}개, "
                        f"채팅 {len(messages)}개"
                    )
                    self.new_data_received.emit(data)
                
                # 폴링 간격만큼 대기
                time.sleep(self.polling_interval)
                
            except Exception as e:
                # 연속 실패 카운터 증가
                self.consecutive_failures += 1
                
                error_msg = f"폴링 중 오류 발생 ({self.consecutive_failures}회): {e}"
                logger.error(error_msg)
                self.error_occurred.emit(error_msg)
                
                # Exponential backoff 계산
                # 1회 실패: polling_interval * 2^0 = polling_interval
                # 2회 실패: polling_interval * 2^1 = polling_interval * 2
                # 3회 실패: polling_interval * 2^2 = polling_interval * 4
                backoff_time = self.polling_interval * (
                    self.backoff_factor ** (self.consecutive_failures - 1)
                )
                
                # 최대 대기 시간 제한 (60초)
                backoff_time = min(backoff_time, 60)
                
                logger.warning(
                    f"재시도 대기 중: {backoff_time:.1f}초 "
                    f"(연속 실패: {self.consecutive_failures}회)"
                )
                
                # 연속 실패가 임계값을 초과하면 경고
                if self.consecutive_failures >= self.max_consecutive_failures:
                    warning_msg = (
                        f"연속 {self.consecutive_failures}회 실패. "
                        f"VirtualOffice 서버 연결을 확인하세요."
                    )
                    logger.error(warning_msg)
                    self.error_occurred.emit(warning_msg)
                
                time.sleep(backoff_time)
        
        logger.info("폴링 워커 종료")
    
    def stop(self) -> None:
        """폴링 중지
        
        워커 스레드를 안전하게 종료합니다.
        """
        logger.info("폴링 워커 중지 요청")
        self.running = False
    
    def set_polling_interval(self, interval: int) -> None:
        """폴링 간격 조정
        
        Args:
            interval: 새로운 폴링 간격 (초)
        
        Example:
            >>> worker.set_polling_interval(10)  # 10초로 변경
        """
        if interval <= 0:
            logger.warning(f"잘못된 폴링 간격: {interval}초. 변경하지 않습니다.")
            return
        
        old_interval = self.polling_interval
        self.polling_interval = interval
        logger.info(f"폴링 간격 변경: {old_interval}초 → {interval}초")
    
    def increase_polling_interval(self, factor: float = 2.0) -> None:
        """폴링 간격 증가
        
        시뮬레이션이 일시정지되었을 때 폴링 간격을 증가시킵니다.
        
        Args:
            factor: 증가 배율 (기본값: 2.0)
        
        Example:
            >>> worker.increase_polling_interval(2.0)  # 2배로 증가
        """
        new_interval = int(self.polling_interval * factor)
        # 최대 60초로 제한
        new_interval = min(new_interval, 60)
        self.set_polling_interval(new_interval)
    
    def decrease_polling_interval(self, factor: float = 2.0) -> None:
        """폴링 간격 감소
        
        시뮬레이션이 재개되었을 때 폴링 간격을 감소시킵니다.
        
        Args:
            factor: 감소 배율 (기본값: 2.0)
        
        Example:
            >>> worker.decrease_polling_interval(2.0)  # 1/2로 감소
        """
        new_interval = int(self.polling_interval / factor)
        # 최소 1초로 제한
        new_interval = max(new_interval, 1)
        self.set_polling_interval(new_interval)
    
    def reset_polling_interval(self, default_interval: int = 5) -> None:
        """폴링 간격 초기화
        
        Args:
            default_interval: 기본 폴링 간격 (초, 기본값: 5)
        
        Example:
            >>> worker.reset_polling_interval(5)  # 5초로 초기화
        """
        self.set_polling_interval(default_interval)
    
    def get_status(self) -> Dict[str, Any]:
        """워커 상태 조회
        
        Returns:
            Dict[str, Any]: 워커 상태 정보
                - running: 실행 중 여부
                - polling_interval: 현재 폴링 간격 (초)
                - consecutive_failures: 연속 실패 횟수
        
        Example:
            >>> status = worker.get_status()
            >>> print(f"Running: {status['running']}")
        """
        return {
            "running": self.running,
            "polling_interval": self.polling_interval,
            "consecutive_failures": self.consecutive_failures
        }
