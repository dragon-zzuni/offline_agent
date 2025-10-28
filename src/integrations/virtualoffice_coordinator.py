# -*- coding: utf-8 -*-
"""
VirtualOffice 연동 코디네이터

VirtualOffice 서버 연결, 페르소나 관리, 데이터 수집을 담당합니다.
"""
import logging
from typing import Optional, Callable
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal

from .virtualoffice_client import VirtualOfficeClient
from .models import PersonaInfo, VirtualOfficeConfig
from .polling_worker import PollingWorker
from .simulation_monitor import SimulationMonitor

logger = logging.getLogger(__name__)


class VirtualOfficeCoordinator(QObject):
    """VirtualOffice 연동 코디네이터"""
    
    # 시그널 정의
    connection_success = pyqtSignal(list, object)  # personas, sim_status
    connection_failed = pyqtSignal(str)  # error_message
    persona_changed = pyqtSignal(object)  # persona
    new_data_received = pyqtSignal(list, list)  # emails, messages
    polling_error = pyqtSignal(str)  # error_message
    
    def __init__(self, config_path: Path, parent=None):
        super().__init__(parent)
        self.config_path = config_path
        self.config: Optional[VirtualOfficeConfig] = None
        self.client: Optional[VirtualOfficeClient] = None
        self.polling_worker: Optional[PollingWorker] = None
        self.sim_monitor: Optional[SimulationMonitor] = None
        self.personas: list[PersonaInfo] = []
        self.selected_persona: Optional[PersonaInfo] = None
        
    def load_config(self) -> bool:
        """설정 파일 로드"""
        try:
            if self.config_path.exists():
                logger.info(f"VirtualOffice 설정 파일 로드 중: {self.config_path}")
                self.config = VirtualOfficeConfig.load_from_file(self.config_path)
                logger.info("✅ VirtualOffice 설정 파일 로드 완료")
                return True
            else:
                logger.info("VirtualOffice 설정 파일이 없습니다.")
                return False
        except Exception as e:
            logger.warning(f"VirtualOffice 설정 로드 실패: {e}")
            return False
    
    def save_config(self, email_url: str, chat_url: str, sim_url: str, 
                   selected_persona_email: Optional[str] = None) -> bool:
        """설정 파일 저장"""
        try:
            self.config = VirtualOfficeConfig(
                email_url=email_url,
                chat_url=chat_url,
                sim_url=sim_url,
                selected_persona_email=selected_persona_email
            )
            self.config.save_to_file(self.config_path)
            logger.info(f"✅ VirtualOffice 설정 저장 완료: {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"VirtualOffice 설정 저장 실패: {e}")
            return False
    
    def connect(self, email_url: str, chat_url: str, sim_url: str) -> None:
        """VirtualOffice 서버 연결"""
        try:
            logger.info("VirtualOffice 서버 연결 테스트 중...")
            
            # 클라이언트 생성
            self.client = VirtualOfficeClient(email_url, chat_url, sim_url)
            
            # 연결 테스트
            email_ok = self.client.test_email_connection()
            chat_ok = self.client.test_chat_connection()
            sim_ok = self.client.test_sim_connection()
            
            if not (email_ok and chat_ok and sim_ok):
                raise ConnectionError("일부 서버 연결 실패")
            
            logger.info("✅ 모든 서버 연결 성공")
            
            # 페르소나 목록 조회
            logger.info("페르소나 목록 조회 중...")
            self.personas = self.client.get_personas()
            logger.info(f"✅ {len(self.personas)}개 페르소나 조회 완료")
            
            # 시뮬레이션 상태 조회
            sim_status = self.client.get_simulation_status()
            
            # 연결 성공 시그널 발생
            self.connection_success.emit(self.personas, sim_status)
            
        except Exception as e:
            logger.error(f"❌ VirtualOffice 연결 실패: {e}", exc_info=True)
            self.connection_failed.emit(str(e))
    
    def select_persona(self, persona: PersonaInfo) -> None:
        """페르소나 선택"""
        self.selected_persona = persona
        self.persona_changed.emit(persona)
        logger.info(f"페르소나 변경: {persona.name} ({persona.email_address})")
    
    def start_polling(self, interval_seconds: int = 30) -> None:
        """폴링 워커 시작"""
        if not self.client or not self.selected_persona:
            logger.warning("클라이언트 또는 페르소나가 설정되지 않음")
            return
        
        try:
            # 기존 워커 중지
            self.stop_polling()
            
            # 새 워커 시작
            self.polling_worker = PollingWorker(
                self.client,
                self.selected_persona,
                interval_seconds
            )
            self.polling_worker.new_data.connect(self._on_new_data)
            self.polling_worker.error_occurred.connect(self._on_polling_error)
            self.polling_worker.start()
            
            logger.info(f"✅ PollingWorker 시작됨 (폴링 간격: {interval_seconds}초)")
            
        except Exception as e:
            logger.error(f"PollingWorker 시작 오류: {e}")
    
    def stop_polling(self) -> None:
        """폴링 워커 중지"""
        if self.polling_worker:
            logger.info("PollingWorker 중지 중...")
            self.polling_worker.stop()
            self.polling_worker.wait(3000)
            self.polling_worker = None
            logger.info("✅ PollingWorker 중지됨")
    
    def start_sim_monitor(self, interval_ms: int = 2000) -> None:
        """시뮬레이션 모니터 시작"""
        if not self.client:
            logger.warning("클라이언트가 설정되지 않음")
            return
        
        try:
            # 기존 모니터 중지
            self.stop_sim_monitor()
            
            # 새 모니터 시작
            self.sim_monitor = SimulationMonitor(self.client, interval_ms)
            self.sim_monitor.start()
            
            logger.info("✅ SimulationMonitor 시작됨")
            
        except Exception as e:
            logger.error(f"SimulationMonitor 시작 오류: {e}")
    
    def stop_sim_monitor(self) -> None:
        """시뮬레이션 모니터 중지"""
        if self.sim_monitor:
            logger.info("SimulationMonitor 중지 중...")
            self.sim_monitor.stop()
            self.sim_monitor = None
            logger.info("✅ SimulationMonitor 중지됨")
    
    def cleanup(self) -> None:
        """리소스 정리"""
        self.stop_polling()
        self.stop_sim_monitor()
    
    def _on_new_data(self, emails: list, messages: list) -> None:
        """새 데이터 수신 핸들러"""
        self.new_data_received.emit(emails, messages)
    
    def _on_polling_error(self, error_msg: str) -> None:
        """폴링 오류 핸들러"""
        self.polling_error.emit(error_msg)
