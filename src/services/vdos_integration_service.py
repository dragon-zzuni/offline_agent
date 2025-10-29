# -*- coding: utf-8 -*-
"""
VDOS 통합 서비스

VirtualOffice 데이터베이스 연동 및 관련 기능을 담당합니다.
"""
import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any

from ..utils.vdos_connector import VDOSConnector

logger = logging.getLogger(__name__)


class VDOSIntegrationService:
    """VDOS 통합 서비스"""
    
    def __init__(self):
        """VDOSIntegrationService 초기화"""
        self.vdos_connector: Optional[VDOSConnector] = None
        self.todo_db_path: Optional[str] = None
        self.vo_config_path: Optional[Path] = None
        
        self._initialize_vdos_connection()
        logger.info("VDOSIntegrationService 초기화 완료")
    
    def _initialize_vdos_connection(self) -> None:
        """VDOS 연결 초기화"""
        try:
            self.vdos_connector = VDOSConnector()
            
            if self.vdos_connector.is_available:
                vdos_dir = os.path.dirname(self.vdos_connector.vdos_db_path)
                
                # TODO DB 경로 설정
                self.todo_db_path = os.path.join(vdos_dir, "todos_cache.db")
                logger.info(f"[VDOS] TODO DB 경로: {self.todo_db_path}")
                
                # VirtualOffice 설정 파일 경로
                self.vo_config_path = Path(vdos_dir) / "virtualoffice_config.json"
                logger.info(f"[VDOS] 설정 파일 경로: {self.vo_config_path}")
                
            else:
                # 폴백: 기본 경로
                self.todo_db_path = os.path.join("data", "todos_cache.db")
                self.vo_config_path = Path("data/virtualoffice_config.json")
                logger.warning(f"[VDOS] 연결 실패, 폴백 경로 사용")
                
        except Exception as e:
            logger.error(f"VDOS 연결 초기화 오류: {e}")
            # 폴백 설정
            self.todo_db_path = os.path.join("data", "todos_cache.db")
            self.vo_config_path = Path("data/virtualoffice_config.json")
    
    def get_todo_db_path(self) -> str:
        """TODO DB 경로 반환"""
        return self.todo_db_path or os.path.join("data", "todos_cache.db")
    
    def get_vo_config_path(self) -> Path:
        """VirtualOffice 설정 파일 경로 반환"""
        return self.vo_config_path or Path("data/virtualoffice_config.json")
    
    def is_available(self) -> bool:
        """VDOS 연결 가능 여부"""
        return self.vdos_connector and self.vdos_connector.is_available
    
    def get_people_data(self) -> list:
        """사람 정보 데이터 반환"""
        if self.vdos_connector and self.vdos_connector.is_available:
            return self.vdos_connector.get_people()
        return []
    
    def get_vdos_db_path(self) -> Optional[str]:
        """VDOS DB 경로 반환"""
        if self.vdos_connector:
            return self.vdos_connector.vdos_db_path
        return None
    
    def get_status(self) -> Dict[str, Any]:
        """VDOS 연결 상태 반환"""
        return {
            "available": self.is_available(),
            "todo_db_path": self.get_todo_db_path(),
            "vo_config_path": str(self.get_vo_config_path()),
            "vdos_db_path": self.get_vdos_db_path(),
            "people_count": len(self.get_people_data()) if self.is_available() else 0
        }