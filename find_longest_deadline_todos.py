# -*- coding: utf-8 -*-
"""
마감일이 가장 먼 TODO들 찾기
"""
import sqlite3
import os
from datetime import datetime

cache_db_path = "../virtualoffice/src/virtualoffice/todos_cache.db"
if not os.path.exists(cache_db_path):
    print(f"❌ 캐시 DB를 찾을 수 없습니다: {cache_db_path}")
    exit(1)

conn = sqlite3.connect(cache_db_path)
cursor = conn.cursor()

now = datetime.now()

print("=" * 80)
print("마감일이 가장 먼 TODO 상위 10개")
print("=" * 80)

# 마감일이 있는 TODO만 가져오기 (status != 'done')
cursor.execute("""
    SELECT id, title, description, priority, deadline, requester, type, status,
           project_tag, project_full_name, recipient_type, source_type, persona_name
    FROM todos
    WHERE deadline IS NOT NULL 
      AND status != 'done'
    ORDER BY deadline DESC
    LIMIT 10
""")

rows = cursor.fetchall()

for i, row in enumerate(rows, 1):
    (todo_id, title, description, priority, deadline, requester, todo_type, 
     status, project_tag, project_full_name, recipient_type, source_type, persona_name) = row
    
    # 마감일 계산
    deadline_dt = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
    days_left = (deadline_dt - now).days
    deadline_display = f"D-{days_left}" if days_left >= 0 else f"D+{abs(days_left)} (지남)"
    
    print(f"\n{i}. {todo_id}")
    print(f"   제목: {title[:50] if title else ''}")
    print(f"   설명: {description[:50] if description else ''}...")
    print(f"   프로젝트: {project_tag} ({project_full_name})")
    print(f"   요청자: {requester}")
    print(f"   유형: {todo_type}")
    print(f"   마감: {deadline_display} ({deadline})")
    print(f"   우선순위: {priority}")
    print(f"   페르소나: {persona_name}")

print("\n" + "=" * 80)
print("분석:")
print("=" * 80)
print("LLM이 선정한 TODO:")
print("  1. task_28bb72d8acb6 - D-5 (2025-11-24)")
print("  2. review_59135d354176 - D-5 (2025-11-24)")
print("  3. task_f5ae076689bd - D-16 (2025-12-05)")
print("\n위 리스트에 D-19 이상인 TODO가 있다면, LLM이 잘못 선정한 것입니다.")

# 전체 TODO 개수 확인
cursor.execute("SELECT COUNT(*) FROM todos WHERE deadline IS NOT NULL AND status != 'done'")
total_with_deadline = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM todos WHERE status != 'done'")
total_pending = cursor.fetchone()[0]

print(f"\n전체 pending TODO: {total_pending}개")
print(f"마감일이 있는 pending TODO: {total_with_deadline}개")

conn.close()
