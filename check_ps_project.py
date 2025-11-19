# -*- coding: utf-8 -*-
"""
PS 프로젝트 TODO 확인
"""
import sqlite3
import os

cache_db_path = "../virtualoffice/src/virtualoffice/todos_cache.db"
if not os.path.exists(cache_db_path):
    print(f"❌ 캐시 DB를 찾을 수 없습니다: {cache_db_path}")
    exit(1)

conn = sqlite3.connect(cache_db_path)
cursor = conn.cursor()

print("=" * 80)
print("PS 프로젝트 TODO 확인")
print("=" * 80)

# PS 프로젝트 TODO 찾기
cursor.execute("""
    SELECT id, title, project_tag, project_full_name, type, priority, deadline, status
    FROM todos
    WHERE project_tag = 'PS' AND status != 'done'
    ORDER BY deadline DESC
    LIMIT 20
""")

rows = cursor.fetchall()

print(f"\nPS 프로젝트 TODO: {len(rows)}개\n")

for i, row in enumerate(rows, 1):
    (todo_id, title, project_tag, project_full_name, todo_type, priority, deadline, status) = row
    
    print(f"{i}. {todo_id}")
    print(f"   제목: {title}")
    print(f"   프로젝트: {project_tag} ({project_full_name})")
    print(f"   유형: {todo_type}, 우선순위: {priority}")
    print(f"   마감: {deadline or '없음'}")
    print()

# 전체 PS 프로젝트 TODO 개수
cursor.execute("SELECT COUNT(*) FROM todos WHERE project_tag = 'PS' AND status != 'done'")
total_ps = cursor.fetchone()[0]

print("=" * 80)
print(f"전체 PS 프로젝트 pending TODO: {total_ps}개")
print("=" * 80)

# 프로젝트 풀네임 확인
cursor.execute("SELECT DISTINCT project_tag, project_full_name FROM todos WHERE project_tag = 'PS'")
projects = cursor.fetchall()

print("\nPS 프로젝트 정보:")
for tag, fullname in projects:
    print(f"  태그: {tag}")
    print(f"  풀네임: {fullname}")

conn.close()
