# -*- coding: utf-8 -*-
"""
데이터 수집 서비스

VirtualOffice 데이터 수집 및 분석 로직을 담당합니다.
"""
import asyncio
import logging
import time
from typing import Dict, List, Optional, Any

from ..integrations.virtualoffice_client import VirtualOfficeClient
from ..integrations.polling_worker import PollingWorker
from ..integrations.simulation_monitor import SimulationMonitor

logger = logging.getLogger(__name__)


class DataCollectionService:
    """데이터 수집 서비스"""
    
    def __init__(self, assistant, time_filter_service):
        """DataCollectionService 초기화
        
        Args:
            assistant: SmartAssistant 인스턴스
            time_filter_service: TimeFilterService 인스턴스
        """
        self.assistant = assistant
        self.time_filter_service = time_filter_service
        
        # VirtualOffice 관련
        self.vo_client: Optional[VirtualOfficeClient] = None
        self.selected_persona: Optional[Any] = None
        self.polling_worker: Optional[PollingWorker] = None
        self.sim_monitor: Optional[SimulationMonitor] = None
        
        # 캐시 시스템
        self._persona_cache: Dict[str, Dict] = {}
        self._cache_valid_until: Dict[str, float] = {}
        self._last_simulation_tick: Optional[int] = None
        self._simulation_running: bool = False
        
        logger.info("DataCollectionService 초기화 완료")
    
    def set_vo_client(self, client: VirtualOfficeClient) -> None:
        """VirtualOffice 클라이언트 설정"""
        self.vo_client = client
        logger.info("VirtualOffice 클라이언트 설정됨")
    
    def set_selected_persona(self, persona: Any) -> None:
        """선택된 페르소나 설정"""
        self.selected_persona = persona
        logger.info(f"페르소나 설정: {persona.name if persona else 'None'}")
    
    async def collect_messages_with_time_filter(self, incremental: bool = False) -> List[Dict]:
        """시간 필터링을 적용한 메시지 수집
        
        Args:
            incremental: 증분 수집 여부
            
        Returns:
            수집된 메시지 리스트
        """
        try:
            if not self.assistant.data_source_manager.current_source:
                logger.warning("데이터 소스가 설정되지 않음")
                return []
            
            # 수집 옵션 준비
            collect_options = {"incremental": incremental}
            
            # 시간 필터링이 활성화된 경우 시간 범위 추가
            if self.time_filter_service.is_enabled:
                time_params = self.time_filter_service.get_collection_params()
                if time_params.get("time_filter_enabled"):
                    collect_options["time_range"] = {
                        "start": self.time_filter_service.current_range[0],
                        "end": self.time_filter_service.current_range[1]
                    }
                    logger.info(f"⏰ 시간 범위로 데이터 수집: {collect_options['time_range']}")
            
            # 데이터 수집
            data_source = self.assistant.data_source_manager.current_source
            messages = await data_source.collect_messages(collect_options)
            
            logger.info(f"📨 메시지 수집 완료: {len(messages)}개")
            return messages
            
        except Exception as e:
            logger.error(f"메시지 수집 오류: {e}", exc_info=True)
            return []
    
    def start_polling_worker(self) -> bool:
        """PollingWorker 시작
        
        Returns:
            시작 성공 여부
        """
        try:
            if self.polling_worker and self.polling_worker.isRunning():
                logger.info("PollingWorker가 이미 실행 중")
                return True
            
            data_source = self.assistant.data_source_manager.current_source
            if not data_source:
                logger.warning("데이터 소스가 없어 PollingWorker 시작 불가")
                return False
            
            # 시뮬레이션 상태에 따른 폴링 간격 조정
            current_tick, is_running = self._get_simulation_status()
            polling_interval = 30 if is_running else 60  # 실행 중: 30초, 정지: 60초
            
            self.polling_worker = PollingWorker(data_source, polling_interval=polling_interval)
            self.polling_worker.start()
            
            logger.info(f"✅ PollingWorker 시작됨 (폴링 간격: {polling_interval}초)")
            return True
            
        except Exception as e:
            logger.error(f"PollingWorker 시작 오류: {e}")
            return False
    
    def stop_polling_worker(self) -> bool:
        """PollingWorker 중지
        
        Returns:
            중지 성공 여부
        """
        try:
            if not self.polling_worker or not self.polling_worker.isRunning():
                logger.info("PollingWorker가 실행되지 않음")
                return True
            
            logger.info("PollingWorker 중지 중...")
            self.polling_worker.stop()
            
            # 최대 3초 대기
            if self.polling_worker.wait(3000):
                logger.info("✅ PollingWorker 중지됨")
                return True
            else:
                logger.warning("⚠️ PollingWorker 중지 시간 초과")
                return False
                
        except Exception as e:
            logger.error(f"PollingWorker 중지 오류: {e}")
            return False
    
    def start_simulation_monitor(self) -> bool:
        """SimulationMonitor 시작
        
        Returns:
            시작 성공 여부
        """
        try:
            if not self.vo_client:
                logger.warning("VirtualOffice 클라이언트가 없어 SimulationMonitor 시작 불가")
                return False
            
            if self.sim_monitor and self.sim_monitor.isRunning():
                logger.info("SimulationMonitor가 이미 실행 중")
                return True
            
            logger.info("SimulationMonitor 시작 중...")
            self.sim_monitor = SimulationMonitor(self.vo_client)
            self.sim_monitor.start()
            
            logger.info("✅ SimulationMonitor 시작됨")
            return True
            
        except Exception as e:
            logger.error(f"SimulationMonitor 시작 오류: {e}")
            return False
    
    def stop_simulation_monitor(self) -> bool:
        """SimulationMonitor 중지
        
        Returns:
            중지 성공 여부
        """
        try:
            if not self.sim_monitor or not self.sim_monitor.isRunning():
                logger.info("SimulationMonitor가 실행되지 않음")
                return True
            
            logger.info("SimulationMonitor 중지 중...")
            self.sim_monitor.stop()
            
            logger.info("✅ SimulationMonitor 중지됨")
            return True
            
        except Exception as e:
            logger.error(f"SimulationMonitor 중지 오류: {e}")
            return False
    
    def _get_simulation_status(self) -> tuple[int, bool]:
        """시뮬레이션 상태 조회
        
        Returns:
            tuple: (current_tick, is_running)
        """
        try:
            if self.sim_monitor:
                status = self.sim_monitor.get_status()
                return status.current_tick, status.is_running
            
            # SimulationMonitor가 없으면 API 직접 호출
            if self.vo_client:
                status = self.vo_client.get_simulation_status()
                return status.current_tick, status.is_running
            
            return 0, False
            
        except Exception as e:
            logger.debug(f"시뮬레이션 상태 조회 실패: {e}")
            return 0, False
    
    def get_cache_status(self) -> Dict[str, Any]:
        """캐시 상태 반환"""
        return {
            "cached_personas": list(self._persona_cache.keys()),
            "cache_count": len(self._persona_cache),
            "last_simulation_tick": self._last_simulation_tick,
            "simulation_running": self._simulation_running
        }
    
    def clear_cache(self) -> None:
        """캐시 초기화"""
        self._persona_cache.clear()
        self._cache_valid_until.clear()
        logger.info("🗑️ 데이터 수집 캐시 초기화됨")
    
    def get_status(self) -> Dict[str, Any]:
        """서비스 상태 반환"""
        return {
            "vo_client_connected": self.vo_client is not None,
            "selected_persona": self.selected_persona.name if self.selected_persona else None,
            "polling_worker_running": self.polling_worker and self.polling_worker.isRunning(),
            "sim_monitor_running": self.sim_monitor and self.sim_monitor.isRunning(),
            "cache_status": self.get_cache_status()
        }