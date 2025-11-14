#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""VDOS tick을 날짜로 변환"""
import sqlite3

conn = sqlite3.connect('virtualoffice/src/virtualoffice/vdos.db')
cursor = conn.cursor()

# 현재 tick
cursor.execute("SELECT current_tick FROM simulation_state WHERE id=1")
current_tick = cursor.fetchone()[0]
print(f"현재 tick: {current_tick}")

# tick_log 확인
print("\n=== tick_log 샘플 (최근 10개) ===")
cursor.execute("SELECT tick, sim_day, sim_hour, real_time FROM tick_log ORDER BY tick DESC LIMIT 10")
for row in cursor.fetchall():
    print(f"tick={row[0]}, day={row[1]}, hour={row[2]}, time={row[3]}")

# 첫 tick
print("\n=== tick_log 샘플 (처음 10개) ===")
cursor.execute("SELECT tick, sim_day, sim_hour, real_time FROM tick_log ORDER BY tick ASC LIMIT 10")
for row in cursor.fetchall():
    print(f"tick={row[0]}, day={row[1]}, hour={row[2]}, time={row[3]}")

# tick당 시간 계산
print("\n=== tick 설정 확인 ===")
cursor.execute("SELECT MIN(tick), MAX(tick) FROM tick_log")
min_tick, max_tick = cursor.fetchone()
print(f"tick 범위: {min_tick} ~ {max_tick}")

cursor.execute("SELECT MIN(sim_day), MAX(sim_day) FROM tick_log")
min_day, max_day = cursor.fetchone()
print(f"sim_day 범위: {min_day} ~ {max_day}")

# 이메일과 tick 매칭 확인
print("\n=== 이메일 sent_at 범위 ===")
cursor.execute("SELECT MIN(sent_at), MAX(sent_at), COUNT(*) FROM emails")
row = cursor.fetchone()
print(f"첫 이메일: {row[0]}")
print(f"마지막 이메일: {row[1]}")
print(f"총 이메일: {row[2]}개")

# tick_log와 이메일 시간 비교
print("\n=== tick_log 시간 범위 ===")
cursor.execute("SELECT MIN(real_time), MAX(real_time) FROM tick_log")
row = cursor.fetchone()
print(f"첫 tick: {row[0]}")
print(f"마지막 tick: {row[1]}")

conn.close()
