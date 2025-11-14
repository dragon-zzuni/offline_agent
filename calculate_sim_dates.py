#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""VDOS tick을 시뮬레이션 날짜로 변환"""
import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect('virtualoffice/src/virtualoffice/vdos.db')
cursor = conn.cursor()

# VDOS 설정 (기본값)
TICKS_PER_HOUR = 480  # 1시간 = 480 tick
WORK_START_HOUR = 9
WORK_END_HOUR = 18
WORK_HOURS_PER_DAY = WORK_END_HOUR - WORK_START_HOUR  # 9시간
TICKS_PER_DAY = TICKS_PER_HOUR * WORK_HOURS_PER_DAY  # 4320 tick

print(f"=== VDOS 시뮬레이션 설정 ===")
print(f"1시간 = {TICKS_PER_HOUR} tick")
print(f"근무시간: {WORK_START_HOUR}:00 ~ {WORK_END_HOUR}:00 ({WORK_HOURS_PER_DAY}시간)")
print(f"1일 = {TICKS_PER_DAY} tick")

# 현재 tick
cursor.execute("SELECT current_tick FROM simulation_state WHERE id=1")
current_tick = cursor.fetchone()[0]
current_day = current_tick // TICKS_PER_DAY
current_hour_offset = (current_tick % TICKS_PER_DAY) // TICKS_PER_HOUR
current_hour = WORK_START_HOUR + current_hour_offset

print(f"\n=== 현재 시뮬레이션 상태 ===")
print(f"현재 tick: {current_tick}")
print(f"현재 day: {current_day} (0부터 시작)")
print(f"현재 시간: {current_hour}시")
print(f"→ Day {current_day + 1}, {current_hour}:00")

# 이메일 sent_at 범위
cursor.execute("SELECT MIN(sent_at), MAX(sent_at), COUNT(*) FROM emails")
min_time, max_time, count = cursor.fetchone()
print(f"\n=== 이메일 실제 생성 시간 ===")
print(f"첫 이메일: {min_time}")
print(f"마지막 이메일: {max_time}")
print(f"총 {count}개")

# tick_log 범위
cursor.execute("SELECT MIN(tick), MAX(tick), COUNT(*) FROM tick_log")
min_tick, max_tick, tick_count = cursor.fetchone()
min_day = min_tick // TICKS_PER_DAY
max_day = max_tick // TICKS_PER_DAY

print(f"\n=== tick_log 범위 ===")
print(f"tick 범위: {min_tick} ~ {max_tick} ({tick_count}개 tick)")
print(f"day 범위: Day {min_day} ~ Day {max_day}")
print(f"→ 총 {max_day - min_day + 1}일")

# 이메일을 tick 순서대로 정렬하여 가상 날짜 할당
print(f"\n=== 이메일 시뮬레이션 날짜 분포 계산 ===")
cursor.execute("SELECT id, sent_at FROM emails ORDER BY sent_at")
emails = cursor.fetchall()

# 시작 날짜 (2025-10-14 월요일로 가정)
START_DATE = datetime(2025, 10, 14)

# 각 이메일에 tick 할당 (균등 분배)
ticks_per_email = max_tick / len(emails)

day_distribution = {}
for i, (email_id, sent_at) in enumerate(emails):
    # 이메일의 가상 tick
    virtual_tick = int(i * ticks_per_email)
    virtual_day = virtual_tick // TICKS_PER_DAY
    
    # 영업일 계산 (주말 제외)
    business_days_passed = 0
    current_date = START_DATE
    while business_days_passed < virtual_day:
        current_date += timedelta(days=1)
        if current_date.weekday() < 5:  # 월~금
            business_days_passed += 1
    
    date_key = current_date.strftime("%Y-%m-%d")
    day_distribution[date_key] = day_distribution.get(date_key, 0) + 1

print(f"이메일을 {len(day_distribution)}일에 분산:")
for date_key in sorted(day_distribution.keys()):
    print(f"  {date_key}: {day_distribution[date_key]}건")

conn.close()
