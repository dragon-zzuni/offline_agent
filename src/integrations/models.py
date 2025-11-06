"""VirtualOffice 연동 데이터 모델

이 모듈은 virtualoffice API 응답을 표현하는 데이터 클래스를 제공합니다.
"""

from dataclasses import dataclass, asdict, field
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime
import json


@dataclass
class PersonaInfo:
    """페르소나 정보
    
    virtualoffice 시뮬레이션의 가상 직원 정보를 표현합니다.
    
    Attributes:
        id: 페르소나 ID
        name: 페르소나 이름
        email_address: 이메일 주소
        chat_handle: 채팅 핸들
        role: 역할 (예: "프로젝트 매니저", "개발자")
    """
    id: int
    name: str
    email_address: str
    chat_handle: str
    role: str
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "PersonaInfo":
        """API 응답에서 PersonaInfo 객체 생성
        
        Args:
            data: API 응답 딕셔너리
        
        Returns:
            PersonaInfo: 생성된 객체
        
        Example:
            >>> data = {
            ...     "id": 1,
            ...     "name": "이민주",
            ...     "email_address": "pm.1@multiproject.dev",
            ...     "chat_handle": "pm",
            ...     "role": "프로젝트 매니저"
            ... }
            >>> persona = PersonaInfo.from_api_response(data)
        """
        return cls(
            id=data["id"],
            name=data["name"],
            email_address=data["email_address"],
            chat_handle=data["chat_handle"],
            role=data.get("role", "Unknown")
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환
        
        Returns:
            Dict[str, Any]: 딕셔너리 표현
        """
        return asdict(self)


@dataclass
class SimulationStatus:
    """시뮬레이션 상태
    
    virtualoffice 시뮬레이션의 현재 상태를 표현합니다.
    
    Attributes:
        current_tick: 현재 틱 번호
        sim_time: 시뮬레이션 시간 (ISO 8601 형식)
        is_running: 실행 중 여부
        auto_tick: 자동 틱 진행 여부
    """
    current_tick: int
    sim_time: str
    is_running: bool
    auto_tick: bool
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "SimulationStatus":
        """API 응답에서 SimulationStatus 객체 생성
        
        Args:
            data: API 응답 딕셔너리
        
        Returns:
            SimulationStatus: 생성된 객체
        """
        return cls(
            current_tick=data["current_tick"],
            sim_time=data["sim_time"],
            is_running=data["is_running"],
            auto_tick=data["auto_tick"]
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환
        
        Returns:
            Dict[str, Any]: 딕셔너리 표현
        """
        return asdict(self)


@dataclass
class VirtualOfficeConfig:
    """VirtualOffice 연동 설정
    
    Attributes:
        email_url: Email Server URL
        chat_url: Chat Server URL
        sim_url: Simulation Manager URL
        polling_interval: 폴링 간격 (초)
        selected_persona: 선택된 페르소나 이메일 주소
    """
    email_url: str = "http://127.0.0.1:8000"
    chat_url: str = "http://127.0.0.1:8001"
    sim_url: str = "http://127.0.0.1:8015"
    polling_interval: int = 5
    selected_persona: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환
        
        Returns:
            Dict[str, Any]: 딕셔너리 표현
        """
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VirtualOfficeConfig":
        """딕셔너리에서 VirtualOfficeConfig 객체 생성
        
        Args:
            data: 딕셔너리
        
        Returns:
            VirtualOfficeConfig: 생성된 객체
        """
        return cls(**data)
    
    def save_to_file(self, path: Path) -> None:
        """설정을 파일에 저장
        
        Args:
            path: 저장할 파일 경로
        
        Example:
            >>> config = VirtualOfficeConfig()
            >>> config.save_to_file(Path("data/virtualoffice_config.json"))
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
    
    @classmethod
    def load_from_file(cls, path: Path) -> "VirtualOfficeConfig":
        """파일에서 설정 로드
        
        Args:
            path: 로드할 파일 경로
        
        Returns:
            VirtualOfficeConfig: 로드된 설정 객체
        
        Raises:
            FileNotFoundError: 파일이 존재하지 않는 경우
            json.JSONDecodeError: JSON 파싱 실패 시
        
        Example:
            >>> config = VirtualOfficeConfig.load_from_file(Path("data/virtualoffice_config.json"))
        """
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)


@dataclass
class TickHistoryEntry:
    """틱 히스토리 항목
    
    각 틱에서 발생한 활동을 추적합니다.
    
    Attributes:
        tick: 틱 번호
        sim_time: 시뮬레이션 시간 (ISO 8601 형식)
        timestamp: 실제 시간 (틱이 발생한 시각)
        email_count: 해당 틱에서 수집된 이메일 수
        message_count: 해당 틱에서 수집된 메시지 수
        total_count: 총 항목 수 (email_count + message_count)
    """
    tick: int
    sim_time: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    email_count: int = 0
    message_count: int = 0
    
    @property
    def total_count(self) -> int:
        """총 항목 수
        
        Returns:
            int: 이메일 수 + 메시지 수
        """
        return self.email_count + self.message_count
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환
        
        Returns:
            Dict[str, Any]: 딕셔너리 표현
        """
        data = asdict(self)
        data["total_count"] = self.total_count
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TickHistoryEntry":
        """딕셔너리에서 TickHistoryEntry 객체 생성
        
        Args:
            data: 딕셔너리
        
        Returns:
            TickHistoryEntry: 생성된 객체
        """
        # total_count는 계산되는 속성이므로 제외
        data_copy = data.copy()
        data_copy.pop("total_count", None)
        return cls(**data_copy)
