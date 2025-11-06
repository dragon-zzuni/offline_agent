"""VirtualOffice 연동 모듈"""

from .virtualoffice_client import VirtualOfficeClient
from .models import SimulationStatus, PersonaInfo, VirtualOfficeConfig
from .converters import (
    convert_email_to_internal_format,
    convert_message_to_internal_format,
    build_persona_maps
)
from .polling_worker import PollingWorker
from .simulation_monitor import SimulationMonitor

__all__ = [
    'VirtualOfficeClient',
    'SimulationStatus',
    'PersonaInfo',
    'VirtualOfficeConfig',
    'convert_email_to_internal_format',
    'convert_message_to_internal_format',
    'build_persona_maps',
    'PollingWorker',
    'SimulationMonitor',
]
