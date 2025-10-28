# -*- coding: utf-8 -*-
"""
VirtualOffice 연동 관리자
MainWindow에서 VirtualOffice 관련 로직을 분리
"""
import logging
from typing import Optional, Dict
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QMessageBox, QApplication

from src.integrations.virtualoffice_client import VirtualOfficeClient
from src.integrations.models import PersonaInfo, VirtualOfficeConfig
from src.integrations.polling_worker import PollingWorker
from src.integrations.simulation_monitor import SimulationMonitor

logger = logging.getLogger(__name__)


class VirtualOfficeManager:
    """VirtualOffice 연동 관리 클래스"""
    
    def __init__(self, main_window):
        """
        Args:
            main_window: MainWindow 인스턴스
        """
        self.main_window = main_window
        self.vo_client: Optional[VirtualOfficeClient] = None
        self.selected_persona: Optional[PersonaInfo] = None
        self.polling_worker: Optional[PollingWorker] = None
        self.sim_monitor: Optional[SimulationMonitor] = None
        
        # 캐시 시스템
        self._persona_cache: Dict[str, Dict] = {}
        self._last_simulation_tick: Optional[int] = None
        self._simulation_running: bool = False
        self._cache_valid_until: Dict[str, float] = {}
    
    def connect(self, email_url: str, chat_url: str, sim_url: str) -> bool:
        """
        VirtualOffice 서버에 연결
        
        Args:
            email_url: Email 서버 URL
            chat_url: Chat 서버 URL
            sim_url: Simulation Manager URL
            
        Returns:
            bool: 연결 성공 여부
        """
        try:
            logger.info("VirtualOffice 서버 연결 테스트 중...")
            
            # VirtualOfficeClient 생성
            self.vo_client = VirtualOfficeClient(email_url, chat_url, sim_url)
            
            # 연결 테스트
            connection_status = self.vo_client.test_connection()
            
            if not all(connection_status.values()):
                failed_servers = [k for k, v in connection_status.items() if not v]
                raise ConnectionError(f"일부 서버 연결 실패: {', '.join(failed_servers)}")
            
            logger.info("✅ 모든 서버 연결 성공")
            
            # 페르소나 목록 조회
            logger.info("페르소나 목록 조회 중...")
            personas = self.vo_client.get_personas()
            
            if not personas:
                raise ValueError("페르소나 목록이 비어있습니다.")
            
            logger.info(f"✅ {len(personas)}개 페르소나 조회 완료")
            
            # 시뮬레이션 상태 조회
            sim_status = self.vo_client.get_simulation_status()
            
            # SimulationMonitor 생성 및 시작
            logger.info("SimulationMonitor 시작 중...")
            self.sim_monitor = SimulationMonitor(self.vo_client)
            self.sim_monitor.status_updated.connect(self.main_window.on_sim_status_updated)
            self.sim_monitor.tick_advanced.connect(self.main_window.on_tick_advanced)
            self.sim_monitor.start_monitoring()
            logger.info("✅ SimulationMonitor 시작됨")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ VirtualOffice 연결 실패: {e}", exc_info=True)
            return False
    
    def start_polling(self, data_source, interval: int = 30):
        """
        폴링 워커 시작
        
        Args:
            data_source: 데이터 소스
            interval: 폴링 간격 (초)
        """
        try:
            if self.polling_worker and self.polling_worker.isRunning():
                logger.warning("PollingWorker가 이미 실행 중입니다")
                return
            
            logger.info(f"PollingWorker 시작 중... (폴링 간격: {interval}초)")
            self.polling_worker = PollingWorker(data_source, polling_interval=interval)
            self.polling_worker.new_data_received.connect(self.main_window.on_new_data_received)
            self.polling_worker.error_occurred.connect(self.main_window.on_polling_error)
            self.polling_worker.start()
            logger.info("✅ PollingWorker 시작됨")
            
        except Exception as e:
            logger.error(f"❌ PollingWorker 시작 실패: {e}", exc_info=True)
    
    def stop_polling(self):
        """폴링 워커 중지"""
        try:
            if self.polling_worker and self.polling_worker.isRunning():
                logger.info("PollingWorker 중지 중...")
                self.polling_worker.stop()
                self.polling_worker.wait(2000)
                self.polling_worker = None
                logger.info("✅ PollingWorker 중지됨")
        except Exception as e:
            logger.error(f"❌ PollingWorker 중지 실패: {e}")
    
    def set_persona(self, persona: PersonaInfo):
        """
        페르소나 설정
        
        Args:
            persona: 선택된 페르소나
        """
        self.selected_persona = persona
        logger.info(f"페르소나 설정: {persona.name} ({persona.email_address})")
    
    def get_simulation_status(self) -> tuple[int, bool]:
        """
        시뮬레이션 상태 조회
        
        Returns:
            tuple: (current_tick, is_running)
        """
        try:
            if self.sim_monitor:
                status = self.sim_monitor.get_status()
                return status.current_tick, status.is_running
            
            if self.vo_client:
                status = self.vo_client.get_simulation_status()
                return status.current_tick, status.is_running
            
            return 0, False
            
        except Exception as e:
            logger.debug(f"시뮬레이션 상태 조회 실패: {e}")
            return 0, False
    
    def should_use_cache(self, persona_key: str) -> bool:
        """
        캐시 사용 여부 결정
        
        Args:
            persona_key: 페르소나 식별 키
            
        Returns:
            bool: 캐시 사용 가능 여부
        """
        try:
            if persona_key not in self._persona_cache:
                return False
            
            current_tick, is_running = self.get_simulation_status()
            
            if is_running:
                logger.debug("시뮬레이션 실행 중 - 캐시 사용 안 함")
                return False
            
            if (self._last_simulation_tick is not None and 
                current_tick > 0 and 
                current_tick != self._last_simulation_tick):
                logger.debug(f"틱 변경됨 ({self._last_simulation_tick} → {current_tick}) - 캐시 무효화")
                self.invalidate_all_cache()
                return False
            
            import time
            cache_timeout = 300  # 5분
            if persona_key in self._cache_valid_until:
                if time.time() > self._cache_valid_until[persona_key]:
                    logger.debug("캐시 시간 만료 - 캐시 무효화")
                    return False
            
            logger.debug("캐시 사용 가능")
            return True
            
        except Exception as e:
            logger.error(f"캐시 확인 오류: {e}")
            return False
    
    def invalidate_all_cache(self):
        """모든 캐시 무효화"""
        self._persona_cache.clear()
        self._cache_valid_until.clear()
        logger.info("모든 캐시 무효화됨")
    
    def cleanup(self):
        """리소스 정리"""
        self.stop_polling()
        
        if self.sim_monitor:
            self.sim_monitor.stop_monitoring()
            self.sim_monitor = None
        
        self.vo_client = None
        self.selected_persona = None
        self.invalidate_all_cache()
        
        logger.info("VirtualOfficeManager 리소스 정리 완료")
