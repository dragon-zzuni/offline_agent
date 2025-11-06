"""
TODO의 source_message 확인
"""
import sqlite3
import json

db_path = "C:/Users/USER/Desktop/virtual-office-orchestration/virtualoffice/src/virtualoffice/todos_cache.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 김용준의 TODO 중 하나의 source_message 확인
cursor.execute("""
    SELECT id, title, persona_name, requester, source_message 
    FROM todos 
    WHERE persona_name = '김용준' 
    LIMIT 5
""")

todos = cursor.fetchall()

print("=" * 80)
print("김용준 페르소나의 TODO source_message 확인")
print("=" * 80)

for i, (todo_id, title, persona, requester, source_msg_str) in enumerate(todos, 1):
    print(f"\n{i}. {title}")
    print(f"   페르소나: {persona}")
    print(f"   요청자: {requester}")
    
    if source_msg_str:
        try:
            source_msg = json.loads(source_msg_str)
            print(f"   원본 메시지:")
            print(f"     - 발신자: {source_msg.get('sender', 'N/A')}")
            print(f"     - 플랫폼: {source_msg.get('platform', 'N/A')}")
            print(f"     - 제목: {source_msg.get('subject', 'N/A')[:50]}")
        except:
            print(f"   원본 메시지: JSON 파싱 실패")
    else:
        print(f"   원본 메시지: 없음")

conn.close()
