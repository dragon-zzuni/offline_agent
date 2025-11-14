#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""tick_log 테이블 구조 확인"""
import sqlite3

conn = sqlite3.connect('virtualoffice/src/virtualoffice/vdos.db')
cursor = conn.cursor()

print("=== tick_log 테이블 구조 ===")
cursor.execute("PRAGMA table_info(tick_log)")
for row in cursor.fetchall():
    print(f"  - {row[1]} ({row[2]})")

print("\n=== tick_log 샘플 데이터 (최근 10개) ===")
cursor.execute("SELECT * FROM tick_log ORDER BY tick DESC LIMIT 10")
columns = [desc[0] for desc in cursor.description]
print(f"컬럼: {columns}")
for row in cursor.fetchall():
    print(row)

print("\n=== events 테이블 구조 ===")
cursor.execute("PRAGMA table_info(events)")
for row in cursor.fetchall():
    print(f"  - {row[1]} ({row[2]})")

print("\n=== events 샘플 (최근 10개) ===")
cursor.execute("SELECT * FROM events ORDER BY tick DESC LIMIT 10")
columns = [desc[0] for desc in cursor.description]
print(f"컬럼: {columns}")
for row in cursor.fetchall():
    print(row)

conn.close()
