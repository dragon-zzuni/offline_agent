#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""이도윤 메시지 및 TODO 생성 디버깅"""
import sqlite3
import os
import json

print("=" * 120)
print("1. VDOS DB에서 이도윤이 받은 메시지 확인")
print("=" * 120)

vdos_db_path = os.path.join(os.path.dirname(__file__), "../virtualoffice/src/virtualoffice/vdos.db")

if not os.path.exists(vdos_db_path):
    print(f"VDOS DB 파일을 찾을 수 없습니다: {vdos_db_path}")
    exit(1)

vdos_conn = sqlite3.connect(vdos_db_path)
vdos_cursor = vdos_conn.cursor()

# 이도윤이 받은 메시지 확인
vdos_query = """
SELECT 
    id,
    sender,
    recipient,
    body
FROM chat_messages 
WHERE recipient = 'leedoyoon_marketer'
ORDER BY id DESC 
LIMIT 10
"""

vdos_cursor.execute(vdos_query)
vdos_rows = vdos_cursor.fetchall()

print(f"\n이도윤(leedoyoon_marketer)이 받은 메시지 최근 10개:\n")

for i, row in enumerate(vdos_rows, 1):
    msg_id, sender, recipient, body = row
    print(f"\n[메시지 #{i}]")
    print(f"ID: {msg_id}")
    print(f"발신자: {sender}")
    print(f"수신자: {recipient}")
    print(f"내용: {body[:200]}")
    print("-" * 100)

# 이도윤이 보낸 메시지도 확인
vdos_query2 = """
SELECT 
    id,
    sender,
    recipient,
    body
FROM chat_messages 
WHERE sender = 'leedoyoon_marketer'
ORDER BY id DESC 
LIMIT 5
"""

vdos_cursor.execute(vdos_query2)
vdos_rows2 = vdos_cursor.fetchall()

print(f"\n\n이도윤(leedoyoon_marketer)이 보낸 메시지 최근 5개:\n")

for i, row in enumerate(vdos_rows2, 1):
    msg_id, sender, recipient, body = row
    print(f"\n[메시지 #{i}]")
    print(f"ID: {msg_id}")
    print(f"발신자: {sender}")
    print(f"수신자: {recipient}")
    print(f"내용: {body[:200]}")
    print("-" * 100)

vdos_conn.close()

print("\n\n" + "=" * 120)
print("2. todos_cache.db에서 이도윤 TODO 확인")
print("=" * 120)

db_path = os.path.join(os.path.dirname(__file__), "../virtualoffice/src/virtualoffice/todos_cache.db")

if not os.path.exists(db_path):
    print(f"DB 파일을 찾을 수 없습니다: {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 이도윤 TODO 조회
query = """
SELECT 
    id, 
    title, 
    description, 
    priority, 
    requester,
    evidence,
    persona_name,
    recipient_type,
    source_type
FROM todos 
WHERE persona_name = '이도윤'
ORDER BY created_at DESC 
LIMIT 10
"""

cursor.execute(query)
rows = cursor.fetchall()

if rows:
    print(f"\n이도윤 TODO 최근 10개:\n")
    
    for i, row in enumerate(rows, 1):
        todo_id, title, description, priority, requester, evidence, persona, recipient_type, source_type = row
        
        print(f"\n[TODO #{i}]")
        print(f"ID: {todo_id}")
        print(f"제목: {title}")
        print(f"설명: {description[:150]}...")
        print(f"발신자: {requester}")
        print(f"우선순위: {priority}")
        print(f"수신 타입: {recipient_type}")
        print(f"소스 타입: {source_type}")
        
        # evidence 파싱
        if evidence:
            try:
                evidence_data = json.loads(evidence)
                if isinstance(evidence_data, list) and len(evidence_data) > 0:
                    print(f"Evidence ({len(evidence_data)}개):")
                    for j, reason in enumerate(evidence_data, 1):
                        print(f"  {j}. {reason}")
                else:
                    print(f"Evidence: 빈 배열")
            except:
                print(f"Evidence 파싱 실패")
        
        print("-" * 100)
else:
    print("\n⚠️ 이도윤 TODO가 없습니다!")
    
    # 다른 페르소나 확인
    cursor.execute("SELECT DISTINCT persona_name, COUNT(*) FROM todos GROUP BY persona_name")
    persona_stats = cursor.fetchall()
    
    print("\n현재 DB에 있는 페르소나별 TODO:")
    for persona, count in persona_stats:
        print(f"  - {persona}: {count}개")

conn.close()
