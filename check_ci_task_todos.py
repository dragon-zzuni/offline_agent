# -*- coding: utf-8 -*-
"""
CI 프로젝트의 전형우 업무처리 TODO 확인
"""
import sqlite3
import json

# DB 연결
db_path = "data/multi_project_8week_ko/todos_cache.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 먼저 스키마 확인
cursor.execute("PRAGMA table_info(todos)")
columns = cursor.fetchall()
print("=== DB 스키마 ===")
for col in columns:
    print(f"{col[1]} ({col[2]})")
print()

# 조건: 프로젝트=CI, 유형=task, 요청자=전형우
cursor.execute("""
    SELECT id, title, requester, type, priority, deadline
    FROM todos
    WHERE status != 'done'
    AND type = 'task'
    ORDER BY priority DESC, deadline ASC
""")

rows = cursor.fetchall()

print(f"\n=== CI 프로젝트의 task 유형 TODO: {len(rows)}개 ===\n")

for row in rows:
    todo_id, title, requester, todo_type, priority, deadline = row
    print(f"ID: {todo_id}")
    print(f"  제목: {title[:60]}")
    print(f"  요청자: {requester}")
    print(f"  유형: {todo_type}")
    print(f"  우선순위: {priority}")
    print(f"  마감일: {deadline}")
    print()

# 전형우가 요청한 것만 필터링
print("\n=== 전형우가 요청한 task 유형 TODO ===\n")

jeonhyungwoo_todos = [row for row in rows if '전형우' in row[2] or 'hyungwoo' in row[2].lower() or 'jeon' in row[2].lower()]

print(f"전형우 TODO: {len(jeonhyungwoo_todos)}개\n")

for row in jeonhyungwoo_todos:
    todo_id, title, requester, todo_type, priority, deadline = row
    print(f"ID: {todo_id}")
    print(f"  제목: {title[:60]}")
    print(f"  요청자: {requester}")
    print(f"  우선순위: {priority}")
    print()

conn.close()
