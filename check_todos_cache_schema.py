# -*- coding: utf-8 -*-
"""
TODO 캐시 DB 스키마 확인
"""
import sqlite3
import os

cache_db_path = "../virtualoffice/src/virtualoffice/todos_cache.db"
if not os.path.exists(cache_db_path):
    print(f"❌ 캐시 DB를 찾을 수 없습니다: {cache_db_path}")
    exit(1)

conn = sqlite3.connect(cache_db_path)
cursor = conn.cursor()

print("=" * 80)
print("TODO 캐시 DB 테이블 목록")
print("=" * 80)

# 테이블 목록
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

for table_name, in tables:
    print(f"\n테이블: {table_name}")
    
    # 컬럼 정보
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    
    print("  컬럼:")
    for col in columns:
        print(f"    - {col[1]} ({col[2]})")
    
    # 샘플 데이터 (최대 3개)
    cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
    rows = cursor.fetchall()
    
    if rows:
        print("\n  샘플 데이터:")
        for i, row in enumerate(rows, 1):
            print(f"\n  [{i}]")
            for j, col in enumerate(columns):
                col_name = col[1]
                value = row[j]
                if isinstance(value, str) and len(value) > 100:
                    value = value[:100] + "..."
                print(f"    {col_name}: {value}")

conn.close()
