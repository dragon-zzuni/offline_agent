"""TODO에 project_full_name이 있는지 확인"""
import sqlite3

db_path = r"C:\Users\USER\Desktop\virtual-office-orchestration\virtualoffice\src\virtualoffice\todos_cache.db"
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# 1. 테이블 스키마 확인
print("=" * 80)
print("todos 테이블 스키마")
print("=" * 80)
cursor.execute("PRAGMA table_info(todos)")
columns = cursor.fetchall()
for col in columns:
    print(f"{col['name']} ({col['type']})")

# 2. project_full_name이 있는 TODO 확인
print("\n" + "=" * 80)
print("project_full_name이 있는 TODO 샘플")
print("=" * 80)
cursor.execute("""
    SELECT id, title, project, project_full_name, requester, type
    FROM todos
    WHERE project = 'CI' AND type = 'review' AND requester LIKE '%hyungwoo%'
    LIMIT 5
""")

todos = cursor.fetchall()
for todo in todos:
    print(f"\nID: {todo['id']}")
    print(f"  제목: {todo['title'][:50]}")
    print(f"  프로젝트 코드: {todo['project']}")
    print(f"  프로젝트 풀네임: {todo['project_full_name']}")
    print(f"  요청자: {todo['requester']}")
    print(f"  유형: {todo['type']}")

conn.close()
