#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""중복 TODO 확인"""
import sqlite3
import os
import json

db_path = os.path.join(os.path.dirname(__file__), "../virtualoffice/src/virtualoffice/todos_cache.db")

if not os.path.exists(db_path):
    print(f"DB 파일을 찾을 수 없습니다: {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# "이정두님께 업데이트 드립니다" TODO 찾기
query = """
SELECT 
    id, 
    title, 
    description, 
    requester,
    source_message,
    created_at
FROM todos 
WHERE description LIKE '%이정두%업데이트%'
ORDER BY created_at DESC
"""

cursor.execute(query)
rows = cursor.fetchall()

print("=" * 100)
print(f"'이정두님께 업데이트 드립니다' 관련 TODO: {len(rows)}개")
print("=" * 100)

for i, row in enumerate(rows, 1):
    todo_id, title, description, requester, source_message, created_at = row
    
    print(f"\n[TODO #{i}]")
    print(f"ID: {todo_id}")
    print(f"제목: {title}")
    print(f"설명: {description}")
    print(f"요청자: {requester}")
    print(f"생성일: {created_at}")
    
    # source_message 파싱
    if source_message:
        try:
            msg = json.loads(source_message)
            print(f"\n원본 메시지:")
            print(f"  msg_id: {msg.get('msg_id')}")
            print(f"  sender: {msg.get('sender')}")
            print(f"  subject: {msg.get('subject')}")
            print(f"  body: {msg.get('body', '')[:200]}")
            print(f"  platform: {msg.get('platform')}")
        except:
            print(f"  source_message 파싱 실패")
    
    print("-" * 100)

conn.close()
