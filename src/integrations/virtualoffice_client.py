"""VirtualOffice API 클라이언트

이 모듈은 virtualoffice 시스템의 REST API와 통신하는 클라이언트를 제공합니다.
"""

import logging
from typing import Dict, List, Optional, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .models import PersonaInfo, SimulationStatus
from .connection_manager import ConnectionManager
from .validators import (
    validate_email_response,
    validate_message_response,
    validate_simulation_status,
    validate_persona_list
)

logger = logging.getLogger(__name__)


class VirtualOfficeClient:
    """VirtualOffice API 클라이언트
    
    virtualoffice의 Email Server, Chat Server, Simulation Manager와 통신합니다.
    
    Attributes:
        email_url: Email Server URL (예: http://127.0.0.1:8000)
        chat_url: Chat Server URL (예: http://127.0.0.1:8001)
        sim_url: Simulation Manager URL (예: http://127.0.0.1:8015)
        session: HTTP 세션 (재시도 로직 포함)
    """
    
    def __init__(
        self,
        email_url: str = "http://127.0.0.1:8000",
        chat_url: str = "http://127.0.0.1:8001",
        sim_url: str = "http://127.0.0.1:8015",
        timeout: int = 5,
        use_connection_manager: bool = True
    ):
        """VirtualOfficeClient 초기화
        
        Args:
            email_url: Email Server URL
            chat_url: Chat Server URL
            sim_url: Simulation Manager URL
            timeout: 요청 타임아웃 (초)
            use_connection_manager: ConnectionManager 사용 여부 (기본값: True)
        """
        self.email_url = email_url.rstrip('/')
        self.chat_url = chat_url.rstrip('/')
        self.sim_url = sim_url.rstrip('/')
        self.timeout = timeout
        
        # HTTP 세션 설정
        self.session = requests.Session()
        
        # 재시도 로직 설정
        # - 최대 3회 재시도
        # - 연결 오류, 타임아웃, 5xx 오류 시 재시도
        # - 백오프: 0.5초, 1초, 2초
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "DELETE"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # ConnectionManager 설정
        self.connection_manager = None
        if use_connection_manager:
            self.connection_manager = ConnectionManager(
                max_retries=3,
                base_delay=1.0,
                max_delay=60.0,
                backoff_factor=2.0
            )
        
        # 마지막 성공 ID 추적 (연결 복구 시 사용)
        self.last_successful_email_id = 0
        self.last_successful_message_id = 0
        
        logger.info(
            f"VirtualOfficeClient 초기화: "
            f"email={self.email_url}, chat={self.chat_url}, sim={self.sim_url}, "
            f"connection_manager={'활성화' if use_connection_manager else '비활성화'}"
        )
    
    def test_connection(self) -> Dict[str, bool]:
        """각 서버의 연결 상태 확인
        
        각 서버에 헬스 체크 요청을 보내 연결 가능 여부를 확인합니다.
        
        Returns:
            Dict[str, bool]: 서버별 연결 상태
                - "email": Email Server 연결 상태
                - "chat": Chat Server 연결 상태
                - "sim": Simulation Manager 연결 상태
        
        Example:
            >>> client = VirtualOfficeClient()
            >>> status = client.test_connection()
            >>> print(status)
            {"email": True, "chat": True, "sim": True}
        """
        status = {
            "email": False,
            "chat": False,
            "sim": False
        }
        
        # Email Server 연결 테스트
        try:
            # /health 엔드포인트가 없으므로 /docs로 테스트
            response = self.session.get(
                f"{self.email_url}/docs",
                timeout=self.timeout
            )
            status["email"] = response.status_code == 200
            logger.info(f"Email Server 연결: {status['email']}")
        except Exception as e:
            logger.warning(f"Email Server 연결 실패: {e}")
        
        # Chat Server 연결 테스트
        try:
            # /health 엔드포인트가 없으므로 /docs로 테스트
            response = self.session.get(
                f"{self.chat_url}/docs",
                timeout=self.timeout
            )
            status["chat"] = response.status_code == 200
            logger.info(f"Chat Server 연결: {status['chat']}")
        except Exception as e:
            logger.warning(f"Chat Server 연결 실패: {e}")
        
        # Simulation Manager 연결 테스트
        try:
            # /health 엔드포인트가 없으므로 /docs로 테스트
            response = self.session.get(
                f"{self.sim_url}/docs",
                timeout=self.timeout
            )
            status["sim"] = response.status_code == 200
            logger.info(f"Simulation Manager 연결: {status['sim']}")
        except Exception as e:
            logger.warning(f"Simulation Manager 연결 실패: {e}")
        
        return status
    
    def get_personas(self) -> List[PersonaInfo]:
        """페르소나 목록 조회
        
        Simulation Manager에서 사용 가능한 페르소나 목록을 조회합니다.
        
        Returns:
            List[PersonaInfo]: 페르소나 정보 리스트
        
        Raises:
            requests.exceptions.RequestException: API 요청 실패 시
            ValueError: 응답 데이터 형식이 잘못된 경우
        
        Example:
            >>> client = VirtualOfficeClient()
            >>> personas = client.get_personas()
            >>> for p in personas:
            ...     print(f"{p.name} ({p.role})")
        """
        try:
            response = self.session.get(
                f"{self.sim_url}/api/v1/people",
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            
            if not isinstance(data, list):
                raise ValueError(f"예상치 못한 응답 형식: {type(data)}")
            
            personas = [PersonaInfo.from_api_response(item) for item in data]
            logger.info(f"페르소나 {len(personas)}개 조회 완료")
            
            return personas
            
        except requests.exceptions.RequestException as e:
            logger.error(f"페르소나 조회 실패: {e}")
            raise
        except (KeyError, ValueError) as e:
            logger.error(f"페르소나 데이터 파싱 실패: {e}")
            raise ValueError(f"잘못된 페르소나 데이터 형식: {e}")
    
    def get_emails(
        self,
        mailbox: str,
        since_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """메일 수집
        
        지정된 메일박스에서 메일을 조회합니다.
        since_id가 제공되면 해당 ID 이후의 메일만 조회합니다 (증분 수집).
        
        Args:
            mailbox: 메일박스 주소 (예: "pm.1@multiproject.dev")
            since_id: 마지막 조회한 메일 ID (None이면 전체 조회)
        
        Returns:
            List[Dict[str, Any]]: 메일 데이터 리스트
                각 메일은 다음 필드를 포함:
                - id: 메일 ID
                - sender: 발신자 이메일
                - to: 수신자 리스트
                - cc: 참조 리스트
                - bcc: 숨은참조 리스트
                - subject: 제목
                - body: 본문
                - thread_id: 스레드 ID (선택적)
                - sent_at: 발송 시간 (ISO 8601)
        
        Raises:
            requests.exceptions.RequestException: API 요청 실패 시
            ValueError: 응답 데이터 형식이 잘못된 경우
        
        Example:
            >>> client = VirtualOfficeClient()
            >>> # 전체 메일 조회
            >>> emails = client.get_emails("pm.1@multiproject.dev")
            >>> # 증분 조회
            >>> new_emails = client.get_emails("pm.1@multiproject.dev", since_id=1000)
        """
        try:
            url = f"{self.email_url}/mailboxes/{mailbox}/emails"
            params = {}
            
            if since_id is not None:
                params["since_id"] = since_id
            
            response = self.session.get(
                url,
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            
            if not isinstance(data, list):
                raise ValueError(f"예상치 못한 응답 형식: {type(data)}")
            
            # 데이터 검증 (잘못된 데이터 필터링)
            valid_emails, errors = validate_email_response(data, strict=False)
            
            if errors:
                logger.warning(
                    f"이메일 검증 중 {len(errors)}개 오류 발생. "
                    f"유효한 이메일: {len(valid_emails)}개"
                )
            
            # 마지막 성공 ID 업데이트
            if valid_emails:
                max_id = max(email["id"] for email in valid_emails)
                self.last_successful_email_id = max(self.last_successful_email_id, max_id)
            
            logger.info(
                f"메일 {len(valid_emails)}개 조회 완료 "
                f"(mailbox={mailbox}, since_id={since_id})"
            )
            
            return valid_emails
            
        except requests.exceptions.RequestException as e:
            logger.error(f"메일 조회 실패: {e}")
            raise
        except (KeyError, ValueError) as e:
            logger.error(f"메일 데이터 파싱 실패: {e}")
            raise ValueError(f"잘못된 메일 데이터 형식: {e}")
    
    def get_messages(
        self,
        handle: str,
        since_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """채팅 메시지 수집
        
        지정된 사용자의 DM(Direct Message)을 조회합니다.
        since_id가 제공되면 해당 ID 이후의 메시지만 조회합니다 (증분 수집).
        
        Args:
            handle: 사용자 채팅 핸들 (예: "pm")
            since_id: 마지막 조회한 메시지 ID (None이면 전체 조회)
        
        Returns:
            List[Dict[str, Any]]: 메시지 데이터 리스트
                각 메시지는 다음 필드를 포함:
                - id: 메시지 ID
                - room_slug: 룸 식별자 (예: "dm:designer:dev")
                - sender: 발신자 핸들
                - body: 메시지 본문
                - sent_at: 발송 시간 (ISO 8601)
        
        Raises:
            requests.exceptions.RequestException: API 요청 실패 시
            ValueError: 응답 데이터 형식이 잘못된 경우
        
        Example:
            >>> client = VirtualOfficeClient()
            >>> # 전체 메시지 조회
            >>> messages = client.get_messages("pm")
            >>> # 증분 조회
            >>> new_messages = client.get_messages("pm", since_id=500)
        """
        try:
            url = f"{self.chat_url}/users/{handle}/dms"
            params = {}
            
            if since_id is not None:
                params["since_id"] = since_id
            
            response = self.session.get(
                url,
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            
            if not isinstance(data, list):
                raise ValueError(f"예상치 못한 응답 형식: {type(data)}")
            
            # 데이터 검증 (잘못된 데이터 필터링)
            valid_messages, errors = validate_message_response(data, strict=False)
            
            if errors:
                logger.warning(
                    f"메시지 검증 중 {len(errors)}개 오류 발생. "
                    f"유효한 메시지: {len(valid_messages)}개"
                )
            
            # 마지막 성공 ID 업데이트
            if valid_messages:
                max_id = max(msg["id"] for msg in valid_messages)
                self.last_successful_message_id = max(self.last_successful_message_id, max_id)
            
            logger.info(
                f"메시지 {len(valid_messages)}개 조회 완료 "
                f"(handle={handle}, since_id={since_id})"
            )
            
            return valid_messages
            
        except requests.exceptions.RequestException as e:
            logger.error(f"메시지 조회 실패: {e}")
            raise
        except (KeyError, ValueError) as e:
            logger.error(f"메시지 데이터 파싱 실패: {e}")
            raise ValueError(f"잘못된 메시지 데이터 형식: {e}")
    
    def get_simulation_status(self) -> SimulationStatus:
        """시뮬레이션 상태 조회
        
        Simulation Manager에서 현재 시뮬레이션 상태를 조회합니다.
        
        Returns:
            SimulationStatus: 시뮬레이션 상태 정보
                - current_tick: 현재 틱 번호
                - sim_time: 시뮬레이션 시간 (ISO 8601)
                - is_running: 실행 중 여부
                - auto_tick: 자동 틱 진행 여부
        
        Raises:
            requests.exceptions.RequestException: API 요청 실패 시
            ValueError: 응답 데이터 형식이 잘못된 경우
        
        Example:
            >>> client = VirtualOfficeClient()
            >>> status = client.get_simulation_status()
            >>> print(f"Tick: {status.current_tick}, Running: {status.is_running}")
        """
        try:
            response = self.session.get(
                f"{self.sim_url}/api/v1/simulation",
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            
            if not isinstance(data, dict):
                raise ValueError(f"예상치 못한 응답 형식: {type(data)}")
            
            # 필수 필드 검증
            required_fields = ["current_tick", "sim_time", "is_running", "auto_tick"]
            missing_fields = [f for f in required_fields if f not in data]
            if missing_fields:
                raise ValueError(f"필수 필드 누락: {missing_fields}")
            
            status = SimulationStatus.from_api_response(data)
            logger.debug(
                f"시뮬레이션 상태: tick={status.current_tick}, "
                f"running={status.is_running}"
            )
            
            return status
            
        except requests.exceptions.RequestException as e:
            logger.error(f"시뮬레이션 상태 조회 실패: {e}")
            raise
        except (KeyError, ValueError) as e:
            logger.error(f"시뮬레이션 상태 데이터 파싱 실패: {e}")
            raise ValueError(f"잘못된 시뮬레이션 상태 데이터 형식: {e}")
