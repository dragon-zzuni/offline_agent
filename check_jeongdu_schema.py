#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TODO DB 스키마 확인"""

import sqlite3
from pathlib import Path

def check_schema():
    """TODO DB 스키마 확인"""
    
    print("=" * 80)
    print("TODO DB 스키마 확인")
    print("=" * 80)
    
    todos_db = Path("offline_agent/data/multi_project_8week_ko/todos_cache.db")
    
    if not todos_db.exists():
        print(f"\n❌ TODO DB 없음: {todos_db}")
        return
    
    conn = sqlite3.connect(todos_db)
    cursor = conn.cursor()
    
    # 테이블 목록
    print("\n[1] 테이블 목록:")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    for table in tables:
        print(f"  - {table[0]}")
    
    # todos 테이블 스키마
    print("\n[2] todos 테이블 스키마:")
    cursor.execute("PRAGMA table_info(todos)")
    columns = cursor.fetchall()
    for col in columns:
        print(f"  {col[1]} ({col[2]})")
    
    # 이정두 데이터 샘플
    print("\n[3] 이정두 데이터 샘플:")
    cursor.execute("SELECT id, title, priority, requester, project_tag, is_top3 FROM todos WHERE requester = '이정두' LIMIT 3")
    samples = cursor.fetchall()
    
    if samples:
        for sample in samples:
            print(f"  ID: {sample[0]}")
            print(f"  제목: {sample[1]}")
            print(f"  우선순위: {sample[2]}")
            print(f"  요청자: {sample[3]}")
            print(f"  프로젝트: {sample[4]}")
            print(f"  TOP3: {sample[5]}")
            print()
    else:
        print("  ❌ 이정두 데이터 없음")
    
    # 전체 페르소나 목록
    print("\n[4] 전체 페르소나 목록 (requester 기준):")
    cursor.execute("SELECT DISTINCT requester FROM todos WHERE requester IS NOT NULL")
    personas = cursor.fetchall()
    for persona in personas:
        cursor.execute("SELECT COUNT(*) FROM todos WHERE requester = ?", (persona[0],))
        count = cursor.fetchone()[0]
        print(f"  - {persona[0]}: {count}개")
    
    conn.close()
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    check_schema()
