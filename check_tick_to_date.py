#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""VDOS tick → 시뮬레이션 시간 매핑 검사"""
import os
import sqlite3
from datetime import datetime, timezone, timedelta

DB_PATH = 'virtualoffice/src/virtualoffice/vdos.db'
SIM_HOURS_PER_DAY = int(os.getenv("VDOS_HOURS_PER_DAY", "8"))
TICKS_PER_DAY = max(1, SIM_HOURS_PER_DAY * 60)  # tick_log는 분 단위 tick 누적


def parse_ts(value: str) -> datetime:
    if not value:
        raise ValueError("빈 timestamp")
    normalized = value.replace("Z", "+00:00")
    dt = datetime.fromisoformat(normalized)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def format_sim_time(tick: int, base_dt: datetime) -> str:
    tick = max(1, tick)
    day_index = (tick - 1) // TICKS_PER_DAY
    minutes_of_day = int(((tick - 1) % TICKS_PER_DAY) / TICKS_PER_DAY * 1440)
    sim_dt = base_dt + timedelta(days=day_index, minutes=minutes_of_day)
    label = f"Day {day_index + 1} {minutes_of_day // 60:02d}:{minutes_of_day % 60:02d}"
    return label, sim_dt


conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# 현재 tick
cursor.execute("SELECT current_tick FROM simulation_state WHERE id=1")
current_tick = cursor.fetchone()[0]
print(f"현재 tick: {current_tick}")

# tick_log 기준 시간 확보
cursor.execute("SELECT tick, created_at FROM tick_log ORDER BY tick ASC LIMIT 1")
first_row = cursor.fetchone()
if not first_row:
    raise SystemExit("tick_log 테이블에 데이터가 없습니다.")
base_tick, base_created_at = first_row
base_dt = parse_ts(base_created_at)
print(f"기준 tick: {base_tick} (created_at={base_dt.isoformat()})")

# tick 범위
cursor.execute("SELECT MIN(tick), MAX(tick), COUNT(*) FROM tick_log")
min_tick, max_tick, tick_count = cursor.fetchone()
print(f"tick 범위: {min_tick} ~ {max_tick} ({tick_count}개)")

print("\n=== tick_log 샘플 (최근 10개) ===")
cursor.execute("SELECT tick, reason, created_at FROM tick_log ORDER BY tick DESC LIMIT 10")
for tick, reason, created_at in cursor.fetchall():
    label, sim_dt = format_sim_time(tick, base_dt)
    print(f"tick={tick:6d} | reason={reason:30s} | created_at={created_at} | {label} ({sim_dt.date()})")

print("\n=== tick_log 샘플 (처음 10개) ===")
cursor.execute("SELECT tick, reason, created_at FROM tick_log ORDER BY tick ASC LIMIT 10")
for tick, reason, created_at in cursor.fetchall():
    label, sim_dt = format_sim_time(tick, base_dt)
    print(f"tick={tick:6d} | reason={reason:30s} | created_at={created_at} | {label} ({sim_dt.date()})")

print("\n=== 이메일 sent_at 범위 ===")
cursor.execute("SELECT MIN(sent_at), MAX(sent_at), COUNT(*) FROM emails")
row = cursor.fetchone()
print(f"첫 이메일: {row[0]}")
print(f"마지막 이메일: {row[1]}")
print(f"총 이메일: {row[2]}개")

print("\n=== tick_log created_at 범위 ===")
cursor.execute("SELECT MIN(created_at), MAX(created_at) FROM tick_log")
row = cursor.fetchone()
print(f"첫 tick 기록 시간: {row[0]}")
print(f"마지막 tick 기록 시간: {row[1]}")

conn.close()
