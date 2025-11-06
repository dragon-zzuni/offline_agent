#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""이정두가 받은 메시지 확인"""

import sqlite3
from pathlib import Path

def check_jeongdu_received():
    """이정두가 받은 메시지 확인"""
    
    print("=" * 80)
    print("이정두가 받은 메시지 확인")
    print("=" * 80)
    
    vdos_db = Path("virtualoffice/src/virtualoffice/vdos.db")
    
    if not vdos_db.exists():
        print(f"\n❌ VDOS DB 없음: {vdos_db}")
        return
    
    conn = sqlite3.connect(vdos_db)
    cursor = conn.cursor()
    
    # email_recipients 테이블 스키마
    print("\n[1] email_recipients 테이블 스키마:")
    cursor.execute("PRAGMA table_info(email_recipients)")
    columns = cursor.fetchall()
    for col in columns:
        print(f"  {col[1]} ({col[2]})")
    
    # 이정두의 이메일 주소 찾기
    print("\n[2] 이정두의 이메일 주소:")
    cursor.execute("SELECT * FROM people WHERE name = '이정두'")
    jeongdu = cursor.fetchone()
    if jeongdu:
        cursor.execute("PRAGMA table_info(people)")
        columns = [col[1] for col in cursor.fetchall()]
        for i, col in enumerate(columns):
            print(f"  {col}: {jeongdu[i]}")
    
    # 이정두가 받은 이메일 (email_recipients 사용)
    print("\n[3] 이정두가 받은 이메일:")
    cursor.execute("""
        SELECT e.id, e.subject, e.sender, e.sent_at, er.kind
        FROM emails e
        JOIN email_recipients er ON e.id = er.email_id
        WHERE er.address = 'leejungdu@example.com'
        ORDER BY e.sent_at DESC
        LIMIT 10
    """)
    
    emails = cursor.fetchall()
    print(f"  총 {len(emails)}개 (최근 10개)")
    
    for email in emails:
        email_id, subject, sender, sent_at, recipient_type = email
        print(f"\n  [{email_id}] {subject}")
        print(f"    발신: {sender}, 수신: leejungdu@example.com ({recipient_type})")
        print(f"    시간: {sent_at}")
    
    # 이정두가 참여한 채팅방 (chat_members 스키마 확인 필요)
    print("\n[4] 이정두가 참여한 채팅방:")
    
    # chat_members 스키마 확인
    cursor.execute("PRAGMA table_info(chat_members)")
    member_columns = [col[1] for col in cursor.fetchall()]
    print(f"  chat_members 컬럼: {member_columns}")
    
    # 채팅 메시지 샘플 (이정두가 받은 것)
    cursor.execute("""
        SELECT id, sender, body, sent_at
        FROM chat_messages
        WHERE sender != 'lee_jd'
        ORDER BY sent_at DESC
        LIMIT 5
    """)
    
    messages = cursor.fetchall()
    print(f"\n  최근 채팅 메시지 (이정두 제외): {len(messages)}개")
    
    for msg in messages:
        msg_id, sender, body, sent_at = msg
        print(f"    [{msg_id}] {sender}: {body[:50]}...")
        print(f"      시간: {sent_at}")
    
    # 전체 통계
    print("\n[5] 전체 통계:")
    
    # 이정두가 받은 이메일 총 개수
    cursor.execute("""
        SELECT COUNT(*)
        FROM email_recipients
        WHERE address = 'leejungdu@example.com'
    """)
    total_emails = cursor.fetchone()[0]
    print(f"  받은 이메일: {total_emails}개")
    
    # 이정두가 받은 채팅 총 개수 (이정두가 보낸 것 제외)
    cursor.execute("""
        SELECT COUNT(*)
        FROM chat_messages
        WHERE sender != 'lee_jd'
    """)
    total_chats = cursor.fetchone()[0]
    print(f"  받은 채팅: {total_chats}개")
    
    conn.close()
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    check_jeongdu_received()
