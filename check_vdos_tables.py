#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""VDOS DB 테이블 확인"""
import sqlite3
from pathlib import Path

VDOS_DB = Path("../virtualoffice/src/virtualoffice/vdos.db")

if not VDOS_DB.exists():
    print(f"❌ VDOS DB 파일이 없습니다: {VDOS_DB}")
    exit(1)

conn = sqlite3.connect(str(VDOS_DB))
cur = conn.cursor()

print("📋 VDOS DB 테이블 목록:")
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = cur.fetchall()

for table in tables:
    table_name = table[0]
    print(f"\n테이블: {table_name}")
    
    # 테이블 스키마 확인
    cur.execute(f"PRAGMA table_info({table_name})")
    columns = cur.fetchall()
    for col in columns:
        print(f"  {col[1]:20s} {col[2]:15s}")
    
    # 레코드 수 확인
    cur.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = cur.fetchone()[0]
    print(f"  → {count}개 레코드")

conn.close()
