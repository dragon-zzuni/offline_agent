#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""DB 스키마 확인"""
import sqlite3
from pathlib import Path

DB_PATH = "data/multi_project_8week_ko/todos_cache.db"

db_path = Path(DB_PATH)
if not db_path.exists():
    print(f"❌ DB 파일이 없습니다: {db_path}")
    exit(1)

conn = sqlite3.connect(str(db_path))
cur = conn.cursor()

print("📋 todos 테이블 스키마:")
cur.execute("PRAGMA table_info(todos)")
for row in cur.fetchall():
    print(f"  {row[1]:20s} {row[2]:10s} {'NOT NULL' if row[3] else ''} {'DEFAULT ' + str(row[4]) if row[4] else ''}")

print("\n📊 데이터 통계:")
cur.execute("SELECT COUNT(*) FROM todos")
print(f"  전체 TODO: {cur.fetchone()[0]}개")

conn.close()
