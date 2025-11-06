#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VDOS DB 이메일 스키마 확인"""

import sqlite3
from pathlib import Path

def check_vdos_schema():
    """VDOS DB 스키마 확인"""
    
    print("=" * 80)
    print("VDOS DB 스키마 확인")
    print("=" * 80)
    
    vdos_db = Path("virtualoffice/src/virtualoffice/vdos.db")
    
    if not vdos_db.exists():
        print(f"\n❌ VDOS DB 없음: {vdos_db}")
        return
    
    conn = sqlite3.connect(vdos_db)
    cursor = conn.cursor()
    
    # emails 테이블 스키마
    print("\n[1] emails 테이블 스키마:")
    cursor.execute("PRAGMA table_info(emails)")
    columns = cursor.fetchall()
    for col in columns:
        print(f"  {col[1]} ({col[2]})")
    
    # chat_messages 테이블 스키마
    print("\n[2] chat_messages 테이블 스키마:")
    cursor.execute("PRAGMA table_info(chat_messages)")
    columns = cursor.fetchall()
    for col in columns:
        print(f"  {col[1]} ({col[2]})")
    
    # people 테이블 확인
    print("\n[3] people 테이블:")
    cursor.execute("SELECT name FROM people")
    people = cursor.fetchall()
    print(f"  총 {len(people)}명:")
    for person in people:
        print(f"    - {person[0]}")
    
    # 이메일 샘플
    print("\n[4] 이메일 샘플 (1개):")
    cursor.execute("SELECT * FROM emails LIMIT 1")
    sample = cursor.fetchone()
    if sample:
        cursor.execute("PRAGMA table_info(emails)")
        columns = [col[1] for col in cursor.fetchall()]
        for i, col in enumerate(columns):
            print(f"  {col}: {sample[i]}")
    
    # 채팅 샘플
    print("\n[5] 채팅 샘플 (1개):")
    cursor.execute("SELECT * FROM chat_messages LIMIT 1")
    sample = cursor.fetchone()
    if sample:
        cursor.execute("PRAGMA table_info(chat_messages)")
        columns = [col[1] for col in cursor.fetchall()]
        for i, col in enumerate(columns):
            print(f"  {col}: {sample[i]}")
    
    conn.close()
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    check_vdos_schema()
