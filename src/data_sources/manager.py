# -*- coding: utf-8 -*-
"""
Data Source Manager
데이터 소스 추상화 및 관리
"""
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class DataSource(ABC):
    """데이터 소스 추상 인터페이스"""
    
    @abstractmethod
    async def collect_messages(self, options: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        메시지 수집
        
        Args:
            options: 수집 옵션 (시간 범위, 필터 등)
            
        Returns:
            메시지 리스트 (내부 포맷)
        """
        pass
    
    @abstractmethod
    def get_personas(self) -> List[Dict[str, Any]]:
        """
        페르소나 목록 조회
        
        Returns:
            페르소나 정보 리스트
        """
        pass
    
    @abstractmethod
    def get_source_type(self) -> str:
        """
        데이터 소스 타입 반환
        
        Returns:
            "json" 또는 "virtualoffice"
        """
        pass


class DataSourceManager:
    """데이터 소스 관리자"""
    
    def __init__(self):
        self.current_source: Optional[DataSource] = None
        self.source_type: str = "none"
        logger.info("DataSourceManager 초기화")
    
    def set_source(self, source: DataSource, source_type: str):
        """
        데이터 소스 전환
        
        Args:
            source: 새로운 데이터 소스
            source_type: 소스 타입 ("json" 또는 "virtualoffice")
        """
        self.current_source = source
        self.source_type = source_type
        logger.info(f"데이터 소스 전환: {source_type}")
    
    async def collect_messages(self, options: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        현재 소스에서 메시지 수집
        
        Args:
            options: 수집 옵션
            
        Returns:
            메시지 리스트
            
        Raises:
            RuntimeError: 데이터 소스가 설정되지 않은 경우
        """
        if not self.current_source:
            raise RuntimeError("데이터 소스가 설정되지 않았습니다")
        
        logger.info(f"메시지 수집 시작 (소스: {self.source_type})")
        messages = await self.current_source.collect_messages(options)
        logger.info(f"메시지 수집 완료: {len(messages)}개")
        return messages
    
    def get_personas(self) -> List[Dict[str, Any]]:
        """
        현재 소스에서 페르소나 목록 조회
        
        Returns:
            페르소나 리스트
            
        Raises:
            RuntimeError: 데이터 소스가 설정되지 않은 경우
        """
        if not self.current_source:
            raise RuntimeError("데이터 소스가 설정되지 않았습니다")
        
        return self.current_source.get_personas()
    
    def get_source_type(self) -> str:
        """현재 데이터 소스 타입 반환"""
        return self.source_type
    
    def is_source_set(self) -> bool:
        """데이터 소스가 설정되었는지 확인"""
        return self.current_source is not None
