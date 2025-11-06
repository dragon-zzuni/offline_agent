"""
TODO 내용 상세 확인
"""
import sqlite3

db_path = "C:/Users/USER/Desktop/virtual-office-orchestration/virtualoffice/src/virtualoffice/todos_cache.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 김용준의 TODO 중 처음 5개 상세 확인
cursor.execute("""
    SELECT id, title, description, requester, persona_name 
    FROM todos 
    WHERE persona_name = '김용준' 
    LIMIT 5
""")

todos = cursor.fetchall()

print("=" * 80)
print("김용준 페르소나의 TODO 샘플 (처음 5개)")
print("=" * 80)

for i, (todo_id, title, desc, requester, persona) in enumerate(todos, 1):
    print(f"\n{i}. {title}")
    print(f"   페르소나: {persona}")
    print(f"   요청자: {requester}")
    print(f"   설명: {desc[:100] if desc else 'N/A'}...")

# 정지원이 언급된 TODO 찾기
print("\n" + "=" * 80)
print("'정지원'이 언급된 TODO 검색")
print("=" * 80)

cursor.execute("""
    SELECT id, title, description, requester, persona_name 
    FROM todos 
    WHERE title LIKE '%정지원%' OR description LIKE '%정지원%' OR requester LIKE '%정지원%'
    LIMIT 5
""")

jiwon_todos = cursor.fetchall()

if jiwon_todos:
    for i, (todo_id, title, desc, requester, persona) in enumerate(jiwon_todos, 1):
        print(f"\n{i}. {title}")
        print(f"   페르소나: {persona}")
        print(f"   요청자: {requester}")
        print(f"   설명: {desc[:100] if desc else 'N/A'}...")
else:
    print("\n'정지원'이 언급된 TODO가 없습니다.")

conn.close()
