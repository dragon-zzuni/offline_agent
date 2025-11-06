#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""페르소나별 TODO 확인"""
import sqlite3
from pathlib import Path

DB_PATH = Path("../virtualoffice/src/virtualoffice/todos_cache.db")

if not DB_PATH.exists():
    print(f"❌ DB 파일이 없습니다: {DB_PATH}")
    exit(1)

conn = sqlite3.connect(str(DB_PATH))
cur = conn.cursor()

print("📊 페르소나별 TODO 통계:")
cur.execute("""
    SELECT 
        COALESCE(persona_name, '(NULL)') as persona,
        COUNT(*) as count,
        SUM(CASE WHEN status != 'done' THEN 1 ELSE 0 END) as active
    FROM todos
    GROUP BY persona_name
    ORDER BY count DESC
""")

for row in cur.fetchall():
    print(f"  {row[0]:20s}: 전체 {row[1]:3d}개, 활성 {row[2]:3d}개")

print("\n📋 이정두 페르소나 TODO 샘플 (최근 10개):")
cur.execute("""
    SELECT id, title, requester, persona_name, status
    FROM todos
    WHERE persona_name = '이정두'
    ORDER BY created_at DESC
    LIMIT 10
""")

for row in cur.fetchall():
    print(f"  [{row[4]}] {row[1][:50]:50s} (요청자: {row[2]}, 페르소나: {row[3]})")

print("\n📋 다른 페르소나 TODO 샘플 (최근 5개):")
cur.execute("""
    SELECT id, title, requester, persona_name, status
    FROM todos
    WHERE persona_name != '이정두' AND persona_name IS NOT NULL
    ORDER BY created_at DESC
    LIMIT 5
""")

for row in cur.fetchall():
    print(f"  [{row[4]}] {row[1][:50]:50s} (요청자: {row[2]}, 페르소나: {row[3]})")

print("\n🔍 persona_name이 NULL인 TODO:")
cur.execute("""
    SELECT COUNT(*) FROM todos WHERE persona_name IS NULL
""")
null_count = cur.fetchone()[0]
print(f"  {null_count}개")

if null_count > 0:
    print("\n  샘플 (최근 5개):")
    cur.execute("""
        SELECT id, title, requester, status
        FROM todos
        WHERE persona_name IS NULL
        ORDER BY created_at DESC
        LIMIT 5
    """)
    for row in cur.fetchall():
        print(f"    [{row[3]}] {row[1][:50]:50s} (요청자: {row[2]})")

conn.close()
