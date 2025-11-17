# -*- coding: utf-8 -*-
"""
날짜/시간 유틸리티 함수

날짜 파싱 및 변환 관련 공통 함수를 제공합니다.
"""
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
import logging
import json
import os

logger = logging.getLogger(__name__)

# 가상 날짜 매핑 캐시
_virtual_dates_cache = None

def load_virtual_dates() -> Dict[str, str]:
    """가상 날짜 매핑 로드 (캐싱)
    
    Returns:
        {item_type_id: iso_date_string} 형태의 딕셔너리
    """
    global _virtual_dates_cache
    
    if _virtual_dates_cache is not None:
        return _virtual_dates_cache
    
    try:
        # 프로젝트 루트에서 상대 경로로 파일 찾기
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        virtual_dates_file = os.path.join(
            project_root, 
            "data", 
            "multi_project_8week_ko", 
            "virtual_dates.json"
        )
        
        if os.path.exists(virtual_dates_file):
            with open(virtual_dates_file, 'r', encoding='utf-8') as f:
                _virtual_dates_cache = json.load(f)
                logger.info(f"✅ 가상 날짜 매핑 로드: {len(_virtual_dates_cache)}개")
                return _virtual_dates_cache
        else:
            logger.warning(f"가상 날짜 파일 없음: {virtual_dates_file}")
            _virtual_dates_cache = {}
            return _virtual_dates_cache
            
    except Exception as e:
        logger.error(f"가상 날짜 로드 실패: {e}")
        _virtual_dates_cache = {}
        return _virtual_dates_cache


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
    # 1. 가상 날짜 확인 (우선순위 최상위)
    virtual_dates = load_virtual_dates()
    if virtual_dates:
        # msg_id를 키로 직접 사용 (이미 email_{id} 또는 chat_{room}_{id} 형태)
        msg_id = message.get("msg_id")
        
        if msg_id:
            virtual_date_str = virtual_dates.get(msg_id)
            if virtual_date_str:
                dt = parse_iso_datetime(virtual_date_str)
                if dt:
                    logger.info(f"✅ 가상 날짜 적용: {msg_id} -> {virtual_date_str}")
                    return dt
            else:
                logger.warning(f"⚠️  가상 날짜 없음: {msg_id}")
    
    # 2. 실제 날짜 필드 추출 (우선순위: date > timestamp > datetime)
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


def parse_simulation_time(
    sim_time_str: str,
    sim_base: Optional[datetime] = None
) -> Optional[datetime]:
    """시뮬레이션 시간 문자열을 datetime으로 파싱

    "Day X HH:MM" 형식의 문자열을 datetime으로 변환합니다.

    Args:
        sim_time_str: 시뮬레이션 시간 문자열 (예: "Day 30 10:00")
        sim_base: 시뮬레이션 시작 날짜 (Day 1의 기준). None이면 2024-01-01 사용

    Returns:
        datetime 객체 또는 None (파싱 실패 시)

    Examples:
        >>> from datetime import datetime, timezone
        >>> parse_simulation_time("Day 30 10:00")
        datetime.datetime(2024, 1, 30, 10, 0, tzinfo=datetime.timezone.utc)

        >>> base = datetime(2023, 12, 17, 9, 0, tzinfo=timezone.utc)
        >>> parse_simulation_time("Day 30 14:30", sim_base=base)
        datetime.datetime(2024, 1, 15, 14, 30, tzinfo=datetime.timezone.utc)
    """
    if not sim_time_str:
        return None

    try:
        import re
        # Parse "Day X HH:MM" format
        match = re.match(r"Day\s+(\d+)\s+(\d{1,2}):(\d{2})", sim_time_str)
        if not match:
            logger.warning(f"시뮬레이션 시간 형식이 잘못됨: {sim_time_str}")
            return None

        day_index = int(match.group(1))
        hour = int(match.group(2))
        minute = int(match.group(3))

        # 기본 베이스: 2024-01-01 00:00 UTC (Day 1)
        if sim_base is None:
            sim_base = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
        elif sim_base.tzinfo is None:
            sim_base = sim_base.replace(tzinfo=timezone.utc)

        # Day 1 = sim_base, Day 2 = sim_base + 1 day, etc.
        days_offset = day_index - 1  # Day 1 is base day
        result = sim_base + timedelta(days=days_offset, hours=hour, minutes=minute)

        logger.debug(f"시뮬레이션 시간 파싱: {sim_time_str} → {result.isoformat()}")
        return result

    except Exception as e:
        logger.error(f"시뮬레이션 시간 파싱 오류 ({sim_time_str}): {e}")
        return None


def format_simulation_time(
    dt: datetime,
    sim_base: Optional[datetime] = None,
    format_type: str = "compact"
) -> str:
    """시뮬레이션 시간을 사용자 친화적 형식으로 포맷팅

    VirtualOffice 시뮬레이션 시간을 "Day X, HH:MM" 형식으로 표시합니다.

    Args:
        dt: 포맷할 datetime 객체
        sim_base: 시뮬레이션 시작 시간 (Day 1의 기준). None이면 날짜 기반 계산
        format_type: 포맷 타입
            - "compact": "Day 30, 10:00" (기본값)
            - "full": "Day 30, 2024-01-15 10:00"
            - "time_only": "10:00"

    Returns:
        포맷팅된 문자열

    Examples:
        >>> from datetime import datetime, timezone
        >>> dt = datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc)
        >>> sim_base = datetime(2023, 12, 17, 9, 0, tzinfo=timezone.utc)
        >>> format_simulation_time(dt, sim_base)
        'Day 30, 10:30'

        >>> format_simulation_time(dt, sim_base, format_type="time_only")
        '10:30'
    """
    if dt is None:
        return ""

    # UTC로 변환
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    if format_type == "time_only":
        return dt.strftime("%H:%M")

    # Day 계산
    if sim_base:
        # 시뮬레이션 베이스가 주어진 경우
        if sim_base.tzinfo is None:
            sim_base = sim_base.replace(tzinfo=timezone.utc)

        # 일 차이 계산
        delta = (dt - sim_base).days + 1  # Day 1부터 시작
        day_index = max(1, delta)
    else:
        # 베이스가 없으면 일자 기반으로 계산 (2024-01-01 = Day 1)
        # 이는 폴백 방식
        day_of_year = dt.timetuple().tm_yday
        day_index = day_of_year

    time_str = dt.strftime("%H:%M")

    if format_type == "full":
        date_str = dt.strftime("%Y-%m-%d")
        return f"Day {day_index}, {date_str} {time_str}"
    else:  # compact
        return f"Day {day_index}, {time_str}"
