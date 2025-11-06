# -*- coding: utf-8 -*-
"""
메시지 그룹화 유틸리티 모듈
일/주/월 단위로 메시지를 그룹화하는 함수들을 제공
"""
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
from collections import defaultdict
import logging

from utils.datetime_utils import parse_message_date

logger = logging.getLogger(__name__)


def group_by_day(messages: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """메시지를 일별로 그룹화
    
    Args:
        messages: 메시지 리스트
        
    Returns:
        날짜 문자열(YYYY-MM-DD)을 키로 하는 메시지 그룹 딕셔너리
    """
    groups = defaultdict(list)
    
    for message in messages:
        dt = parse_message_date(message)
        date_key = dt.strftime("%Y-%m-%d")
        groups[date_key].append(message)
    
    # 최신순 정렬 (내림차순)
    sorted_groups = dict(sorted(groups.items(), reverse=True))
    logger.info(f"📅 일별 그룹화 완료: {len(sorted_groups)}개 그룹")
    return sorted_groups


def group_by_week(messages: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """메시지를 주별로 그룹화 (월요일 시작)
    
    Args:
        messages: 메시지 리스트
        
    Returns:
        주 시작일 문자열(YYYY-MM-DD)을 키로 하는 메시지 그룹 딕셔너리
    """
    groups = defaultdict(list)
    
    for message in messages:
        dt = parse_message_date(message)
        
        # 해당 주의 월요일 날짜 계산 (weekday(): 월요일=0, 일요일=6)
        days_since_monday = dt.weekday()
        monday = dt - timedelta(days=days_since_monday)
        
        week_key = monday.strftime("%Y-%m-%d")
        groups[week_key].append(message)
    
    # 최신순 정렬 (내림차순)
    sorted_groups = dict(sorted(groups.items(), reverse=True))
    logger.info(f"📅 주별 그룹화 완료: {len(sorted_groups)}개 그룹")
    return sorted_groups


def group_by_month(messages: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """메시지를 월별로 그룹화
    
    Args:
        messages: 메시지 리스트
        
    Returns:
        월 문자열(YYYY-MM)을 키로 하는 메시지 그룹 딕셔너리
    """
    groups = defaultdict(list)
    
    for message in messages:
        dt = parse_message_date(message)
        month_key = dt.strftime("%Y-%m")
        groups[month_key].append(message)
    
    # 최신순 정렬 (내림차순)
    sorted_groups = dict(sorted(groups.items(), reverse=True))
    logger.info(f"📅 월별 그룹화 완료: {len(sorted_groups)}개 그룹")
    return sorted_groups


def get_group_date_range(group_key: str, unit: str) -> tuple[datetime, datetime]:
    """
    그룹 키와 단위로부터 시작/종료 날짜를 계산
    
    Args:
        group_key: 그룹 키 (YYYY-MM-DD 또는 YYYY-MM)
        unit: 그룹화 단위 ("daily", "weekly", "monthly")
        
    Returns:
        (시작 datetime, 종료 datetime) 튜플
    """
    try:
        if unit == "daily":
            # YYYY-MM-DD 형식
            start = datetime.strptime(group_key, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            end = start + timedelta(days=1) - timedelta(microseconds=1)
            
        elif unit == "weekly":
            # YYYY-MM-DD 형식 (월요일)
            start = datetime.strptime(group_key, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            end = start + timedelta(days=7) - timedelta(microseconds=1)
            
        elif unit == "monthly":
            # YYYY-MM 형식
            start = datetime.strptime(group_key, "%Y-%m").replace(tzinfo=timezone.utc)
            # 다음 달 1일에서 1마이크로초 빼기
            if start.month == 12:
                end = start.replace(year=start.year + 1, month=1) - timedelta(microseconds=1)
            else:
                end = start.replace(month=start.month + 1) - timedelta(microseconds=1)
        else:
            raise ValueError(f"지원하지 않는 단위: {unit}")
        
        return start, end
        
    except Exception as e:
        logger.error(f"날짜 범위 계산 오류 ({group_key}, {unit}): {e}")
        now = datetime.now(timezone.utc)
        return now, now
