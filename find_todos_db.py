# -*- coding: utf-8 -*-
"""TODO DB 찾기"""
import sqlite3
import os

# 가능한 DB 경로들
possible_paths = [
    "virtualoffice/src/virtualoffice/vdos.db",
    "offline_agent/data/todos.db",
    "offline_agent/todos.db",
    "data/todos.db",
]

for path in possible_paths:
    if os.path.exists(path):
        print(f"\n✅ DB 발견: {path}")
        try:
            conn = sqlite3.connect(path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            print(f"   테이블: {tables}")
            
            if "todos" in tables:
                cursor.execute("SELECT COUNT(*) FROM todos")
                count = cursor.fetchone()[0]
                print(f"   ✅ todos 테이블 발견! ({count}개 레코드)")
            
            conn.close()
        except Exception as e:
            print(f"   ❌ 오류: {e}")
    else:
        print(f"❌ 없음: {path}")
