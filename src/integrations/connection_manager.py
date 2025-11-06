# -*- coding: utf-8 -*-
"""
Connection Manager
VirtualOffice API 연결 관리 및 재시도 로직
"""

import logging
import time
from typing import Callable, TypeVar, Optional, Any
from functools import wraps
import requests

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ConnectionManager:
    """연결 관리자
    
    VirtualOffice API 호출 시 재시도 로직 및 오류 처리를 담당합니다.
    
    Features:
        - Exponential backoff를 사용한 자동 재시도
        - 연속 실패 추적
        - 연결 상태 모니터링
        - 오류 알림
    
    Attributes:
        max_retries: 최대 재시도 횟수
        base_delay: 기본 대기 시간 (초)
        max_delay: 최대 대기 시간 (초)
        backoff_factor: 백오프 배수
        consecutive_failures: 연속 실패 횟수
        last_success_time: 마지막 성공 시간
        is_connected: 연결 상태
    """
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0
    ):
        """ConnectionManager 초기화
        
        Args:
            max_retries: 최대 재시도 횟수 (기본값: 3)
            base_delay: 기본 대기 시간 초 (기본값: 1.0)
            max_delay: 최대 대기 시간 초 (기본값: 60.0)
            backoff_factor: 백오프 배수 (기본값: 2.0)
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        
        self.consecutive_failures = 0
        self.last_success_time: Optional[float] = None
        self.is_connected = False
        
        logger.info(
            f"ConnectionManager 초기화: "
            f"max_retries={max_retries}, base_delay={base_delay}s, "
            f"max_delay={max_delay}s, backoff_factor={backoff_factor}"
        )
    
    def execute_with_retry(
        self,
        func: Callable[..., T],
        *args,
        **kwargs
    ) -> T:
        """재시도 로직이 적용된 함수 실행
        
        함수 실행 중 오류가 발생하면 exponential backoff를 사용하여
        자동으로 재시도합니다.
        
        Args:
            func: 실행할 함수
            *args: 함수 인자
            **kwargs: 함수 키워드 인자
        
        Returns:
            T: 함수 실행 결과
        
        Raises:
            Exception: 최대 재시도 횟수 초과 시 마지막 예외 발생
        
        Example:
            >>> manager = ConnectionManager()
            >>> result = manager.execute_with_retry(client.get_emails, "pm@example.com")
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                # 함수 실행
                result = func(*args, **kwargs)
                
                # 성공 시 상태 업데이트
                self.consecutive_failures = 0
                self.last_success_time = time.time()
                self.is_connected = True
                
                if attempt > 0:
                    logger.info(f"재시도 성공 (시도 {attempt + 1}/{self.max_retries + 1})")
                
                return result
                
            except (
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.HTTPError
            ) as e:
                last_exception = e
                self.consecutive_failures += 1
                self.is_connected = False
                
                # 마지막 시도인 경우 예외 발생
                if attempt >= self.max_retries:
                    logger.error(
                        f"최대 재시도 횟수 초과 ({self.max_retries}회): {e}"
                    )
                    raise
                
                # 대기 시간 계산 (exponential backoff)
                delay = min(
                    self.base_delay * (self.backoff_factor ** attempt),
                    self.max_delay
                )
                
                logger.warning(
                    f"연결 오류 발생 (시도 {attempt + 1}/{self.max_retries + 1}): {e}. "
                    f"{delay:.1f}초 후 재시도..."
                )
                
                time.sleep(delay)
            
            except Exception as e:
                # 재시도 불가능한 오류 (예: 인증 오류, 잘못된 요청)
                logger.error(f"재시도 불가능한 오류 발생: {e}")
                self.consecutive_failures += 1
                self.is_connected = False
                raise
        
        # 이 코드는 실행되지 않아야 하지만 안전을 위해 추가
        if last_exception:
            raise last_exception
        raise RuntimeError("예상치 못한 오류")
    
    def reset(self) -> None:
        """연결 상태 초기화
        
        연속 실패 횟수를 0으로 리셋하고 연결 상태를 True로 설정합니다.
        """
        self.consecutive_failures = 0
        self.is_connected = True
        logger.info("연결 상태 초기화")
    
    def get_status(self) -> dict:
        """연결 상태 조회
        
        Returns:
            dict: 연결 상태 정보
                - is_connected: 연결 상태
                - consecutive_failures: 연속 실패 횟수
                - last_success_time: 마지막 성공 시간 (Unix timestamp)
        """
        return {
            "is_connected": self.is_connected,
            "consecutive_failures": self.consecutive_failures,
            "last_success_time": self.last_success_time
        }
    
    def is_healthy(self) -> bool:
        """연결 상태가 정상인지 확인
        
        Returns:
            bool: 연결 상태가 정상이면 True, 아니면 False
        """
        # 연속 실패가 3회 이상이면 비정상
        return self.consecutive_failures < 3


def with_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0
):
    """재시도 로직을 적용하는 데코레이터
    
    함수에 자동 재시도 기능을 추가합니다.
    
    Args:
        max_retries: 최대 재시도 횟수
        base_delay: 기본 대기 시간 (초)
        max_delay: 최대 대기 시간 (초)
        backoff_factor: 백오프 배수
    
    Example:
        >>> @with_retry(max_retries=3, base_delay=1.0)
        ... def fetch_data():
        ...     return requests.get("http://example.com/api")
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            manager = ConnectionManager(
                max_retries=max_retries,
                base_delay=base_delay,
                max_delay=max_delay,
                backoff_factor=backoff_factor
            )
            return manager.execute_with_retry(func, *args, **kwargs)
        return wrapper
    return decorator
