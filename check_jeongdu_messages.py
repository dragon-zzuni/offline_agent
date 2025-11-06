#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""이정두의 메시지 확인"""

import sqlite3
from pathlib import Path

def check_jeongdu_messages():
    """이정두의 메시지 확인"""
    
    print("=" * 80)
    print("이정두 메시지 확인")
    print("=" * 80)
    
    vdos_db = Path("virtualoffice/src/virtualoffice/vdos.db")
    
    if not vdos_db.exists():
        print(f"\n❌ VDOS DB 없음: {vdos_db}")
        return
    
    conn = sqlite3.connect(vdos_db)
    cursor = conn.cursor()
    
    # 테이블 확인
    print("\n[1] 테이블 목록:")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    for table in tables:
        print(f"  - {table[0]}")
    
    # 이정두가 받은 이메일
    print("\n[2] 이정두가 받은 이메일:")
    cursor.execute("""
        SELECT id, subject, sender, created_at
        FROM emails
        WHERE recipient = '이정두'
        ORDER BY created_at DESC
        LIMIT 10
    """)
    
    emails = cursor.fetchall()
    print(f"  총 {len(emails)}개 (최근 10개)")
    
    for email in emails:
        email_id, subject, sender, created_at = email
        print(f"\n  [{email_id}] {subject}")
        print(f"    발신: {sender}, 수신: 이정두")
        print(f"    시간: {created_at}")
    
    # 이정두가 받은 채팅
    print("\n[3] 이정두가 받은 채팅:")
    cursor.execute("""
        SELECT id, content, sender, created_at
        FROM chat_messages
        WHERE recipient = '이정두'
        ORDER BY created_at DESC
        LIMIT 10
    """)
    
    chats = cursor.fetchall()
    print(f"  총 {len(chats)}개 (최근 10개)")
    
    for chat in chats:
        chat_id, content, sender, created_at = chat
        print(f"\n  [{chat_id}] {content[:50]}...")
        print(f"    발신: {sender}, 수신: 이정두")
        print(f"    시간: {created_at}")
    
    # 전체 페르소나 목록
    print("\n[4] 전체 페르소나 목록:")
    cursor.execute("SELECT DISTINCT recipient FROM emails")
    email_recipients = cursor.fetchall()
    
    cursor.execute("SELECT DISTINCT recipient FROM chat_messages")
    chat_recipients = cursor.fetchall()
    
    all_personas = set()
    for r in email_recipients:
        if r[0]:
            all_personas.add(r[0])
    for r in chat_recipients:
        if r[0]:
            all_personas.add(r[0])
    
    print(f"  총 {len(all_personas)}명:")
    for persona in sorted(all_personas):
        # 이메일 개수
        cursor.execute("SELECT COUNT(*) FROM emails WHERE recipient = ?", (persona,))
        email_count = cursor.fetchone()[0]
        
        # 채팅 개수
        cursor.execute("SELECT COUNT(*) FROM chat_messages WHERE recipient = ?", (persona,))
        chat_count = cursor.fetchone()[0]
        
        print(f"    - {persona}: 이메일 {email_count}개, 채팅 {chat_count}개")
    
    conn.close()
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    check_jeongdu_messages()
