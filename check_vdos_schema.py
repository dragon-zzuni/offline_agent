#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""VDOS DB 스키마 확인"""
import sqlite3
import os

vdos_db_path = os.path.join(os.path.dirname(__file__), "../virtualoffice/src/virtualoffice/vdos.db")

if not os.path.exists(vdos_db_path):
    print(f"VDOS DB 파일을 찾을 수 없습니다: {vdos_db_path}")
    exit(1)

conn = sqlite3.connect(vdos_db_path)
cursor = conn.cursor()

print("=" * 100)
print("VDOS DB 테이블 목록")
print("=" * 100)

cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

for table in tables:
    table_name = table[0]
    print(f"\n테이블: {table_name}")
    
    # 테이블 스키마 확인
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    
    print("  컬럼:")
    for col in columns:
        col_id, col_name, col_type, not_null, default_val, pk = col
        print(f"    - {col_name} ({col_type})")

print("\n" + "=" * 100)
print("emails 테이블 샘플 데이터")
print("=" * 100)

cursor.execute("SELECT * FROM emails LIMIT 3")
rows = cursor.fetchall()

cursor.execute("PRAGMA table_info(emails)")
columns = [col[1] for col in cursor.fetchall()]

for i, row in enumerate(rows, 1):
    print(f"\n[{i}]")
    for col_name, value in zip(columns, row):
        if isinstance(value, str) and len(value) > 100:
            value = value[:100] + "..."
        print(f"  {col_name}: {value}")

print("\n" + "=" * 100)
print("email_recipients 테이블 확인")
print("=" * 100)

cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='email_recipients'")
if cursor.fetchone():
    print("✅ email_recipients 테이블 존재")
    
    cursor.execute("PRAGMA table_info(email_recipients)")
    columns = cursor.fetchall()
    
    print("\n컬럼:")
    for col in columns:
        col_id, col_name, col_type, not_null, default_val, pk = col
        print(f"  - {col_name} ({col_type})")
    
    print("\n샘플 데이터:")
    cursor.execute("SELECT * FROM email_recipients LIMIT 5")
    rows = cursor.fetchall()
    
    cursor.execute("PRAGMA table_info(email_recipients)")
    columns = [col[1] for col in cursor.fetchall()]
    
    for i, row in enumerate(rows, 1):
        print(f"\n[{i}]")
        for col_name, value in zip(columns, row):
            print(f"  {col_name}: {value}")
else:
    print("❌ email_recipients 테이블 없음")

conn.close()
