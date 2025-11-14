#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""VDOS 시뮬레이션 시간 확인"""
import sqlite3
import sys

conn = sqlite3.connect('virtualoffice/src/virtualoffice/vdos.db')
cursor = conn.cursor()

# 테이블 목록
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
print("=== 테이블 목록 ===")
for row in cursor.fetchall():
    print(f"  - {row[0]}")

# simulation_state 확인
print("\n=== simulation_state 테이블 ===")
try:
    cursor.execute("PRAGMA table_info(simulation_state)")
    columns = cursor.fetchall()
    print("컬럼:")
    for col in columns:
        print(f"  - {col[1]} ({col[2]})")
    
    cursor.execute("SELECT * FROM simulation_state LIMIT 1")
    row = cursor.fetchone()
    if row:
        print(f"\n현재 상태:")
        for i, col in enumerate(columns):
            print(f"  {col[1]}: {row[i]}")
except Exception as e:
    print(f"오류: {e}")

# emails 테이블에 sim_day 같은 컬럼이 있는지 확인
print("\n=== emails 테이블 구조 ===")
cursor.execute("PRAGMA table_info(emails)")
for row in cursor.fetchall():
    print(f"  - {row[1]} ({row[2]})")

# chat_messages 테이블 구조
print("\n=== chat_messages 테이블 구조 ===")
cursor.execute("PRAGMA table_info(chat_messages)")
for row in cursor.fetchall():
    print(f"  - {row[1]} ({row[2]})")

conn.close()
