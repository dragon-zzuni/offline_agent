# -*- coding: utf-8 -*-
"""
Top-3 TODO 상세 내용 확인
"""
import sqlite3
import json
from pathlib import Path

# TODO DB 경로
todo_db_path = Path("virtualoffice/src/virtualoffice/todos_cache.db")

conn = sqlite3.connect(str(todo_db_path))
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("=" * 80)
print("⭐ Top-3 TODO 상세 정보")
print("=" * 80)

# Top-3 TODO 조회
cur.execute("""
    SELECT id, title, description, persona_name, requester, priority, source_message
    FROM todos
    WHERE status != 'done' AND is_top3 = 1
    ORDER BY priority DESC
""")

top3_todos = cur.fetchall()

for idx, row in enumerate(top3_todos, 1):
    print(f"\n[{idx}] {row['title']}")
    print(f"    persona_name: {row['persona_name']}")
    print(f"    requester: {row['requester']}")
    print(f"    priority: {row['priority']}")
    print(f"    description: {row['description'][:100]}...")
    
    # source_message 파싱
    try:
        source_msg = json.loads(row['source_message'])
        sender = source_msg.get('sender', 'N/A')
        msg_type = source_msg.get('type', 'N/A')
        subject = source_msg.get('subject', source_msg.get('content', '')[:50])
        
        print(f"    source_message:")
        print(f"      - type: {msg_type}")
        print(f"      - sender: {sender}")
        print(f"      - subject/content: {subject}...")
    except:
        print(f"    source_message: (파싱 실패)")

conn.close()

print("\n" + "=" * 80)
print("✅ 완료")
