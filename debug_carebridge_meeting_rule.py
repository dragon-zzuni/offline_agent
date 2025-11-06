"""
CareBridge 미팅 규칙 디버깅
"""
import sqlite3
import json

# 1. DB에서 TODO 확인
db_path = r"C:\Users\USER\Desktop\virtual-office-orchestration\virtualoffice\src\virtualoffice\todos_cache.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=" * 80)
print("1. CareBridge 프로젝트 + 미팅 유형 TODO 검색")
print("=" * 80)

cursor.execute("""
    SELECT id, title, requester, type, project, priority, deadline
    FROM todos
    WHERE (project = 'CI' OR project LIKE '%CareBridge%' OR project LIKE '%carebridge%')
    AND (type = 'meeting' OR type = '미팅' OR type LIKE '%meeting%' OR type LIKE '%미팅%')
    ORDER BY created_at DESC
    LIMIT 20
""")

todos = cursor.fetchall()
print(f"\n찾은 TODO: {len(todos)}개\n")

for todo in todos:
    todo_id, title, requester, todo_type, project, priority, deadline = todo
    print(f"ID: {todo_id}")
    print(f"  제목: {title[:80]}")
    print(f"  요청자: {requester}")
    print(f"  유형: {todo_type}")
    print(f"  프로젝트: {project}")
    print(f"  우선순위: {priority}")
    print(f"  마감일: {deadline}")
    print()

print("=" * 80)
print("2. 임보연 관련 TODO 검색")
print("=" * 80)

cursor.execute("""
    SELECT id, title, requester, type, project
    FROM todos
    WHERE requester LIKE '%boyeon%' OR requester LIKE '%임보연%' OR requester LIKE '%limboyeon%'
    LIMIT 10
""")

boyeon_todos = cursor.fetchall()
print(f"\n임보연 관련 TODO: {len(boyeon_todos)}개\n")

for todo in boyeon_todos:
    todo_id, title, requester, todo_type, project = todo
    print(f"ID: {todo_id}")
    print(f"  제목: {title[:80]}")
    print(f"  요청자: {requester}")
    print(f"  유형: {todo_type}")
    print(f"  프로젝트: {project}")
    print()

print("=" * 80)
print("3. 전형우 관련 TODO 검색")
print("=" * 80)

cursor.execute("""
    SELECT id, title, requester, type, project
    FROM todos
    WHERE requester LIKE '%hyungwoo%' OR requester LIKE '%전형우%' OR requester LIKE '%jeon%'
    LIMIT 10
""")

hyungwoo_todos = cursor.fetchall()
print(f"\n전형우 관련 TODO: {len(hyungwoo_todos)}개\n")

for todo in hyungwoo_todos:
    todo_id, title, requester, todo_type, project = todo
    print(f"ID: {todo_id}")
    print(f"  제목: {title[:80]}")
    print(f"  요청자: {requester}")
    print(f"  유형: {todo_type}")
    print(f"  프로젝트: {project}")
    print()

print("=" * 80)
print("4. VDOS DB에서 사람 정보 확인")
print("=" * 80)

vdos_db_path = r"C:\Users\USER\Desktop\virtual-office-orchestration\virtualoffice\src\virtualoffice\vdos.db"
vdos_conn = sqlite3.connect(vdos_db_path)
vdos_cursor = vdos_conn.cursor()

vdos_cursor.execute("SELECT email_address, name, chat_handle FROM people")
people = vdos_cursor.fetchall()

print(f"\n사람 정보: {len(people)}명\n")

person_mapping = {}
for email, name, handle in people:
    if email:
        person_mapping[email] = name
    if handle:
        person_mapping[handle] = name
    
    if '임보연' in name or '전형우' in name:
        print(f"이름: {name}")
        print(f"  이메일: {email}")
        print(f"  핸들: {handle}")
        print()

print("=" * 80)
print("5. 사람 매핑 JSON")
print("=" * 80)
print(json.dumps(person_mapping, ensure_ascii=False, indent=2))

conn.close()
vdos_conn.close()

print("\n" + "=" * 80)
print("결론:")
print("=" * 80)
print("1. CareBridge + 미팅 TODO가 있는지 확인")
print("2. 임보연이 요청자인 TODO가 있는지 확인")
print("3. 전형우가 요청자인 TODO가 있는지 확인")
print("4. LLM 프롬프트에 사람 매핑이 제대로 전달되는지 확인 필요")
