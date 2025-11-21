# -*- coding: utf-8 -*-
"""
날짜/시간 유틸리티 함수

날짜 파싱 및 변환 관련 공통 함수를 제공합니다.
"""
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import logging
import json
import os

logger = logging.getLogger(__name__)

# 가상 날짜 매핑 캐시
_virtual_dates_cache = None

def load_virtual_dates() -> Dict[str, str]:
    """가상 날짜 매핑 로드 (비활성화됨)
    
    가상 날짜 시스템은 더 이상 사용하지 않습니다.
    VDOS의 실제 시뮬레이션 시간을 직접 사용합니다.
    
    Returns:
        빈 딕셔너리
    """
    # 가상 날짜 시스템 비활성화 - 실제 VDOS 시뮬레이션 시간 사용
    return {}


def parse_iso_datetime(value: Optional[str]) -> Optional[datetime]:
    """ISO 형식 날짜 문자열을 datetime 객체로 변환
    
    다양한 ISO 형식을 지원하며, 타임존 정보가 없으면 UTC로 간주합니다.
    
    Args:
        value: ISO 형식 날짜 문자열 (예: "2024-01-01T12:00:00Z")
        
    Returns:
        datetime 객체 또는 None (파싱 실패 시)
        
    Examples:
        >>> parse_iso_datetime("2024-01-01T12:00:00Z")
        datetime.datetime(2024, 1, 1, 12, 0, tzinfo=datetime.timezone.utc)
        
        >>> parse_iso_datetime("2024-01-01T12:00:00")
        datetime.datetime(2024, 1, 1, 12, 0, tzinfo=datetime.timezone.utc)
        
        >>> parse_iso_datetime(None)
        None
    """
    if not value:
        return None
    
    try:
        # Z를 +00:00으로 변환
        value_str = str(value).strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(value_str)
        
        # naive datetime이면 UTC로 간주
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        
        return dt
    except (ValueError, AttributeError) as e:
        logger.debug(f"날짜 파싱 실패 ({value}): {e}")
        return None


def parse_message_date(message: Dict[str, Any]) -> datetime:
    """메시지에서 날짜를 파싱하여 UTC aware datetime으로 반환
    
    메시지 딕셔너리에서 날짜 정보를 추출하고 파싱합니다.
    가상 날짜 매핑이 있으면 우선 사용하고, 없으면 실제 날짜를 사용합니다.
    
    Args:
        message: 메시지 딕셔너리
        
    Returns:
        UTC aware datetime 객체 (파싱 실패 시 현재 시간)
        
    Examples:
        >>> msg = {"date": "2024-01-01T12:00:00Z", "sender": "user"}
        >>> parse_message_date(msg)
        datetime.datetime(2024, 1, 1, 12, 0, tzinfo=datetime.timezone.utc)
    """
    # 실제 날짜 필드 추출 (우선순위: date > timestamp > datetime)
    date_str = (
        message.get("date") or 
        message.get("timestamp") or 
        message.get("datetime")
    )
    
    if not date_str:
        logger.warning(f"메시지에 날짜 정보가 없습니다: {message.get('msg_id')}")
        return datetime.now(timezone.utc)
    
    # ISO 형식 파싱
    dt = parse_iso_datetime(date_str)
    if dt:
        return dt
    
    # 파싱 실패 시 현재 시간 반환
    logger.warning(f"날짜 파싱 실패 ({date_str}), 현재 시간 사용")
    return datetime.now(timezone.utc)


def ensure_utc_aware(dt: Optional[datetime]) -> Optional[datetime]:
    """naive datetime을 UTC aware datetime으로 변환
    
    이미 timezone 정보가 있는 datetime은 그대로 반환합니다.
    
    Args:
        dt: datetime 객체 (naive 또는 aware)
        
    Returns:
        UTC aware datetime 객체 또는 None (입력이 None인 경우)
        
    Examples:
        >>> from datetime import datetime, timezone
        >>> naive_dt = datetime(2024, 1, 1, 12, 0, 0)
        >>> aware_dt = ensure_utc_aware(naive_dt)
        >>> aware_dt.tzinfo
        datetime.timezone.utc
        
        >>> already_aware = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        >>> ensure_utc_aware(already_aware) == already_aware
        True
    """
    if dt is None:
        return None
    
    if dt.tzinfo is None:
        # naive datetime을 UTC로 간주
        return dt.replace(tzinfo=timezone.utc)
    
    # 이미 aware datetime이면 그대로 반환
    return dt


def is_in_time_range(
    dt: datetime,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None
) -> bool:
    """datetime 객체가 지정된 시간 범위 내에 있는지 확인
    
    타임존이 없는 naive datetime은 UTC로 간주합니다.
    
    Args:
        dt: 확인할 datetime 객체
        start: 시작 시간 (None이면 제한 없음)
        end: 종료 시간 (None이면 제한 없음)
        
    Returns:
        시간 범위 내에 있으면 True, 그렇지 않으면 False
        
    Examples:
        >>> from datetime import datetime, timedelta, timezone
        >>> now = datetime.now(timezone.utc)
        >>> start = now - timedelta(hours=1)
        >>> end = now + timedelta(hours=1)
        >>> is_in_time_range(now, start, end)
        True
        
        >>> past = now - timedelta(hours=2)
        >>> is_in_time_range(past, start, end)
        False
    """
    # naive datetime을 UTC aware로 변환
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    if start:
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if dt < start:
            return False
    
    if end:
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        if dt > end:
            return False
    
    return True


def get_simulation_current_time(data_source) -> Optional[datetime]:
    """VDOS 시뮬레이션의 현재 시간 가져오기
    
    Args:
        data_source: VirtualOfficeSource 인스턴스
        
    Returns:
        시뮬레이션 현재 시간 (datetime) 또는 None
    """
    try:
        if not data_source:
            logger.warning("[SimTime] data_source가 None")
            return None
            
        # VirtualOfficeSource인지 확인
        if not hasattr(data_source, 'get_simulation_status_cached'):
            logger.warning(f"[SimTime] get_simulation_status_cached 메서드 없음: {type(data_source).__name__}")
            return None
        
        status = data_source.get_simulation_status_cached()
        if not status:
            logger.warning("[SimTime] status가 None")
            return None
        
        logger.info(f"[SimTime] status 키: {list(status.keys())}")
        
        # 1. sim_time 필드 확인 (하지만 "Day X HH:MM" 형식이므로 사용 불가)
        sim_time_str = status.get('sim_time')
        if sim_time_str:
            logger.info(f"[SimTime] sim_time 필드 발견: {sim_time_str} (Day X 형식이므로 틱 기반 계산 사용)")
            # "Day X HH:MM" 형식은 파싱하지 않고 틱 기반 계산 사용
        else:
            logger.info("[SimTime] sim_time 필드 없음")
        
        # 2. sim_time이 없으면 sim_base_dt + current_tick으로 계산
        if hasattr(data_source, '_compute_sim_datetime_from_tick'):
            current_tick = status.get('current_tick', 0)
            logger.info(f"[SimTime] current_tick: {current_tick}")
            
            if current_tick > 0:
                result = data_source._compute_sim_datetime_from_tick(current_tick)
                if result:
                    sim_dt, day_index, minutes_24h = result
                    logger.info(f"[SimTime] 틱 {current_tick}으로부터 계산: {sim_dt}")
                    return sim_dt
                else:
                    logger.warning(f"[SimTime] _compute_sim_datetime_from_tick({current_tick})이 None 반환")
            else:
                logger.warning("[SimTime] current_tick이 0 이하")
        else:
            logger.warning("[SimTime] _compute_sim_datetime_from_tick 메서드 없음")
        
        # 3. 마지막으로 sim_base_dt 사용 (최소한의 시작 시간)
        if hasattr(data_source, '_sim_base_dt'):
            sim_base_dt = data_source._sim_base_dt
            if sim_base_dt:
                logger.info(f"[SimTime] sim_base_dt 사용: {sim_base_dt}")
                return sim_base_dt
            else:
                logger.warning("[SimTime] _sim_base_dt가 None")
        else:
            logger.warning("[SimTime] _sim_base_dt 속성 없음")
        
        logger.warning("[SimTime] 모든 방법 실패")
        return None
        
    except Exception as e:
        logger.error(f"[SimTime] 시뮬레이션 현재 시간 가져오기 실패: {e}", exc_info=True)
        return None


def get_simulation_time_range(data_source) -> Optional[tuple[datetime, datetime]]:
    """VDOS 시뮬레이션의 시작 시간과 현재 시간 가져오기
    
    Args:
        data_source: VirtualOfficeSource 인스턴스
        
    Returns:
        (시작 시간, 현재 시간) 튜플 또는 None
    """
    try:
        if not data_source:
            return None
            
        # VirtualOfficeSource인지 확인
        if not hasattr(data_source, '_sim_base_dt'):
            return None
        
        # 시작 시간 (sim_base_dt)
        start_time = data_source._sim_base_dt
        if not start_time:
            return None
        
        # 현재 시간
        current_time = get_simulation_current_time(data_source)
        if not current_time:
            return None
        
        return (start_time, current_time)
    except Exception as e:
        logger.error(f"시뮬레이션 시간 범위 가져오기 실패: {e}")
        return None
