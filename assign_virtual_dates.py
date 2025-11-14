#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
VDOS 메시지에 가상 시뮬레이션 날짜 할당

실제 sent_at은 모두 2025-11-12이지만, 
시뮬레이션 순서에 따라 가상 날짜를 할당합니다.
"""
import sqlite3
from datetime import datetime, timedelta

# VDOS 설정
TICKS_PER_HOUR = 480
WORK_START_HOUR = 9
WORK_END_HOUR = 18
WORK_HOURS_PER_DAY = WORK_END_HOUR - WORK_START_HOUR
TICKS_PER_DAY = TICKS_PER_HOUR * WORK_HOURS_PER_DAY  # 4320

# 시뮬레이션 시작 날짜 (2025-11-13 목요일)
START_DATE = datetime(2025, 11, 13, WORK_START_HOUR, 0, 0)
# 종료 날짜: 2026-01-07 (8주 프로젝트)

def tick_to_datetime(tick: int) -> datetime:
    """tick을 시뮬레이션 datetime으로 변환"""
    day_num = tick // TICKS_PER_DAY
    hour_offset = (tick % TICKS_PER_DAY) // TICKS_PER_HOUR
    minute_offset = ((tick % TICKS_PER_DAY) % TICKS_PER_HOUR) // 8  # 480 tick/hour = 8 tick/minute
    
    # 영업일 계산 (주말 제외)
    business_days_passed = 0
    current_date = START_DATE
    while business_days_passed < day_num:
        current_date += timedelta(days=1)
        if current_date.weekday() < 5:  # 월~금
            business_days_passed += 1
    
    # 시간 추가
    result = current_date + timedelta(hours=hour_offset, minutes=minute_offset)
    return result

def main():
    conn = sqlite3.connect('virtualoffice/src/virtualoffice/vdos.db')
    cursor = conn.cursor()
    
    # 1. emails 테이블에 virtual_date 컬럼 추가
    print("=== emails 테이블 업데이트 ===")
    try:
        cursor.execute("ALTER TABLE emails ADD COLUMN virtual_date TEXT")
        print("✅ virtual_date 컬럼 추가")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e):
            print("⚠️  virtual_date 컬럼이 이미 존재합니다")
        else:
            raise
    
    # 2. chat_messages 테이블에 virtual_date 컬럼 추가
    print("\n=== chat_messages 테이블 업데이트 ===")
    try:
        cursor.execute("ALTER TABLE chat_messages ADD COLUMN virtual_date TEXT")
        print("✅ virtual_date 컬럼 추가")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e):
            print("⚠️  virtual_date 컬럼이 이미 존재합니다")
        else:
            raise
    
    # 3. 8주 프로젝트 기간 설정 (40 영업일)
    TOTAL_BUSINESS_DAYS = 40  # 8주 * 5일
    TOTAL_TICKS = TOTAL_BUSINESS_DAYS * TICKS_PER_DAY
    print(f"\n프로젝트 기간: 8주 (40 영업일)")
    print(f"총 tick: {TOTAL_TICKS}")
    
    # 4. 이메일에 가상 날짜 할당
    print("\n=== 이메일 가상 날짜 할당 ===")
    cursor.execute("SELECT id, sent_at FROM emails ORDER BY sent_at")
    emails = cursor.fetchall()
    
    ticks_per_email = TOTAL_TICKS / len(emails)
    
    day_distribution = {}
    for i, (email_id, sent_at) in enumerate(emails):
        virtual_tick = int(i * ticks_per_email)
        virtual_date = tick_to_datetime(virtual_tick)
        virtual_date_str = virtual_date.strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute(
            "UPDATE emails SET virtual_date = ? WHERE id = ?",
            (virtual_date_str, email_id)
        )
        
        date_key = virtual_date.strftime("%Y-%m-%d")
        day_distribution[date_key] = day_distribution.get(date_key, 0) + 1
    
    print(f"✅ {len(emails)}개 이메일 업데이트 완료")
    print(f"\n일별 분포:")
    for date_key in sorted(day_distribution.keys()):
        print(f"  {date_key}: {day_distribution[date_key]}건")
    
    # 5. 메시지에 가상 날짜 할당
    print("\n=== 메시지 가상 날짜 할당 ===")
    cursor.execute("SELECT id, sent_at FROM chat_messages ORDER BY sent_at")
    messages = cursor.fetchall()
    
    ticks_per_message = TOTAL_TICKS / len(messages)
    
    day_distribution = {}
    for i, (msg_id, sent_at) in enumerate(messages):
        virtual_tick = int(i * ticks_per_message)
        virtual_date = tick_to_datetime(virtual_tick)
        virtual_date_str = virtual_date.strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute(
            "UPDATE chat_messages SET virtual_date = ? WHERE id = ?",
            (virtual_date_str, msg_id)
        )
        
        date_key = virtual_date.strftime("%Y-%m-%d")
        day_distribution[date_key] = day_distribution.get(date_key, 0) + 1
    
    print(f"✅ {len(messages)}개 메시지 업데이트 완료")
    print(f"\n일별 분포:")
    for date_key in sorted(day_distribution.keys()):
        print(f"  {date_key}: {day_distribution[date_key]}건")
    
    conn.commit()
    conn.close()
    
    print("\n✅ 모든 업데이트 완료!")

if __name__ == "__main__":
    main()
