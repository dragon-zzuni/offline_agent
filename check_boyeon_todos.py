#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""임보연 TODO 분석 스크립트"""
import sqlite3
import os
import json

# DB 경로
db_path = os.path.join(os.path.dirname(__file__), "../virtualoffice/src/virtualoffice/todos_cache.db")

if not os.path.exists(db_path):
    print(f"DB 파일을 찾을 수 없습니다: {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 임보연 TODO 조회 - evidence 필드 확인
query = """
SELECT 
    id, 
    title, 
    description, 
    priority, 
    requester,
    evidence
FROM todos 
WHERE persona_name = '임보연'
ORDER BY created_at DESC 
LIMIT 5
"""

cursor.execute(query)
rows = cursor.fetchall()

print(f"\n임보연 TODO 최근 5개 (evidence 상세):\n")
print("=" * 120)

for i, row in enumerate(rows, 1):
    todo_id, title, description, priority, requester, evidence = row
    
    print(f"\n[TODO #{i}]")
    print(f"ID: {todo_id}")
    print(f"제목: {title}")
    print(f"설명: {description[:100] if description else 'N/A'}...")
    print(f"발신자: {requester}")
    print(f"우선순위: {priority}")
    
    # evidence 원본 출력
    print(f"\nevidence 원본:")
    if evidence:
        print(f"{evidence[:500]}")
        print("\n...")
    else:
        print("  - evidence 없음")
    
    print("-" * 120)

conn.close()

# 이제 VDOS DB에서 원본 메시지 확인
print("\n\n" + "=" * 120)
print("VDOS DB에서 원본 메시지 확인")
print("=" * 120)

vdos_db_path = os.path.join(os.path.dirname(__file__), "../virtualoffice/src/virtualoffice/vdos.db")

if not os.path.exists(vdos_db_path):
    print(f"VDOS DB 파일을 찾을 수 없습니다: {vdos_db_path}")
    exit(1)

vdos_conn = sqlite3.connect(vdos_db_path)
vdos_cursor = vdos_conn.cursor()

# 임보연이 받은 메시지 확인
vdos_query = """
SELECT 
    id,
    sender,
    body,
    created_at
FROM chat_messages 
WHERE recipient = 'imboyeon_koreait'
ORDER BY created_at DESC 
LIMIT 10
"""

vdos_cursor.execute(vdos_query)
vdos_rows = vdos_cursor.fetchall()

print(f"\n임보연이 받은 메시지 최근 10개:\n")

for i, row in enumerate(vdos_rows, 1):
    msg_id, sender, body, created_at = row
    print(f"\n[메시지 #{i}]")
    print(f"ID: {msg_id}")
    print(f"발신자: {sender}")
    print(f"시간: {created_at}")
    print(f"내용: {body[:200]}")
    print("-" * 100)

vdos_conn.close()
