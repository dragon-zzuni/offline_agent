# -*- coding: utf-8 -*-
"""
Error Notifier
오류 알림 관리 시스템
"""

import logging
from typing import Dict, Optional, Callable
from datetime import datetime, timedelta
from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class ErrorNotifier(QObject):
    """오류 알림 관리자
    
    오류 발생 시 사용자에게 알림을 표시하고, 중복 알림을 방지합니다.
    
    Features:
        - 중복 알림 방지 (1분 이내 동일 오류)
        - 오류 타입별 분류
        - 재시도/취소 옵션 제공
        - 오류 히스토리 추적
    
    Signals:
        error_occurred: 오류 발생 시그널 (error_type: str, message: str, details: dict)
        retry_requested: 재시도 요청 시그널 (error_id: str)
    """
    
    # 시그널 정의
    error_occurred = pyqtSignal(str, str, dict)  # error_type, message, details
    retry_requested = pyqtSignal(str)  # error_id
    
    def __init__(self, parent: Optional[QObject] = None):
        """ErrorNotifier 초기화
        
        Args:
            parent: 부모 QObject (선택적)
        """
        super().__init__(parent)
        
        # 오류 히스토리 (error_key -> last_notification_time)
        self.error_history: Dict[str, datetime] = {}
        
        # 중복 알림 방지 시간 (초)
        self.duplicate_threshold = 60  # 1분
        
        # 오류 카운터
        self.error_counts: Dict[str, int] = {}
        
        logger.info("ErrorNotifier 초기화")
    
    def notify_error(
        self,
        error_type: str,
        message: str,
        details: Optional[Dict] = None,
        allow_retry: bool = True
    ) -> bool:
        """오류 알림 표시
        
        Args:
            error_type: 오류 타입 (예: "connection", "timeout", "api_error")
            message: 오류 메시지
            details: 추가 상세 정보 (선택적)
            allow_retry: 재시도 옵션 표시 여부
        
        Returns:
            bool: 알림이 표시되었으면 True, 중복으로 스킵되었으면 False
        
        Example:
            >>> notifier = ErrorNotifier()
            >>> notifier.notify_error(
            ...     "connection",
            ...     "VirtualOffice 서버에 연결할 수 없습니다",
            ...     {"url": "http://127.0.0.1:8000"}
            ... )
        """
        details = details or {}
        
        # 오류 키 생성 (타입 + 메시지)
        error_key = f"{error_type}:{message}"
        
        # 중복 알림 확인
        if self._is_duplicate(error_key):
            logger.debug(f"중복 오류 알림 스킵: {error_key}")
            return False
        
        # 오류 히스토리 업데이트
        self.error_history[error_key] = datetime.now()
        
        # 오류 카운터 증가
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        # 상세 정보에 재시도 옵션 추가
        details["allow_retry"] = allow_retry
        details["error_id"] = error_key
        details["error_count"] = self.error_counts[error_type]
        
        # 시그널 발생
        self.error_occurred.emit(error_type, message, details)
        
        logger.warning(
            f"오류 알림 표시: [{error_type}] {message} "
            f"(발생 횟수: {self.error_counts[error_type]})"
        )
        
        return True
    
    def _is_duplicate(self, error_key: str) -> bool:
        """중복 오류 확인
        
        Args:
            error_key: 오류 키
        
        Returns:
            bool: 중복이면 True, 아니면 False
        """
        if error_key not in self.error_history:
            return False
        
        last_time = self.error_history[error_key]
        elapsed = (datetime.now() - last_time).total_seconds()
        
        return elapsed < self.duplicate_threshold
    
    def request_retry(self, error_id: str) -> None:
        """재시도 요청
        
        Args:
            error_id: 오류 ID (error_key)
        """
        logger.info(f"재시도 요청: {error_id}")
        self.retry_requested.emit(error_id)
    
    def clear_history(self) -> None:
        """오류 히스토리 초기화"""
        self.error_history.clear()
        self.error_counts.clear()
        logger.info("오류 히스토리 초기화")
    
    def get_error_summary(self) -> Dict[str, int]:
        """오류 요약 조회
        
        Returns:
            Dict[str, int]: 오류 타입별 발생 횟수
        """
        return self.error_counts.copy()
    
    def set_duplicate_threshold(self, seconds: int) -> None:
        """중복 알림 방지 시간 설정
        
        Args:
            seconds: 중복 방지 시간 (초)
        """
        self.duplicate_threshold = seconds
        logger.info(f"중복 알림 방지 시간 설정: {seconds}초")


class ErrorHandler:
    """오류 처리 헬퍼 클래스
    
    일반적인 오류 처리 패턴을 제공합니다.
    """
    
    @staticmethod
    def classify_error(exception: Exception) -> str:
        """예외를 오류 타입으로 분류
        
        Args:
            exception: 예외 객체
        
        Returns:
            str: 오류 타입
        """
        import requests
        
        if isinstance(exception, requests.exceptions.ConnectionError):
            return "connection"
        elif isinstance(exception, requests.exceptions.Timeout):
            return "timeout"
        elif isinstance(exception, requests.exceptions.HTTPError):
            status_code = getattr(exception.response, "status_code", None)
            if status_code == 401:
                return "authentication"
            elif status_code == 403:
                return "authorization"
            elif status_code == 404:
                return "not_found"
            elif status_code >= 500:
                return "server_error"
            else:
                return "http_error"
        elif isinstance(exception, ValueError):
            return "validation"
        else:
            return "unknown"
    
    @staticmethod
    def get_user_friendly_message(error_type: str, exception: Exception) -> str:
        """사용자 친화적인 오류 메시지 생성
        
        Args:
            error_type: 오류 타입
            exception: 예외 객체
        
        Returns:
            str: 사용자 친화적인 메시지
        """
        messages = {
            "connection": "서버에 연결할 수 없습니다. 네트워크 연결을 확인하세요.",
            "timeout": "요청 시간이 초과되었습니다. 서버가 응답하지 않습니다.",
            "authentication": "인증에 실패했습니다. API 키를 확인하세요.",
            "authorization": "권한이 없습니다. 접근 권한을 확인하세요.",
            "not_found": "요청한 리소스를 찾을 수 없습니다.",
            "server_error": "서버 오류가 발생했습니다. 잠시 후 다시 시도하세요.",
            "http_error": "HTTP 오류가 발생했습니다.",
            "validation": "데이터 형식이 올바르지 않습니다.",
            "unknown": "알 수 없는 오류가 발생했습니다."
        }
        
        base_message = messages.get(error_type, messages["unknown"])
        
        # 예외 메시지 추가
        exception_msg = str(exception)
        if exception_msg:
            return f"{base_message}\n상세: {exception_msg}"
        
        return base_message
    
    @staticmethod
    def should_retry(error_type: str) -> bool:
        """재시도 가능 여부 판단
        
        Args:
            error_type: 오류 타입
        
        Returns:
            bool: 재시도 가능하면 True, 아니면 False
        """
        # 재시도 가능한 오류 타입
        retryable_errors = {
            "connection",
            "timeout",
            "server_error"
        }
        
        return error_type in retryable_errors
