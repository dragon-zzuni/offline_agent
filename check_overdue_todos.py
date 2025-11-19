# -*- coding: utf-8 -*-
"""
마감일이 지난 TODO 확인
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
print("마감일이 지난 TODO (status != 'done')")
print("=" * 80)

# 마감일이 지난 TODO 찾기
cursor.execute("""
    SELECT id, title, priority, deadline, requester, type, status,
           project_tag, is_top3
    FROM todos
    WHERE deadline IS NOT NULL 
      AND status != 'done'
      AND datetime(deadline) < datetime('now')
    ORDER BY deadline DESC
    LIMIT 20
""")

rows = cursor.fetchall()

print(f"\n총 {len(rows)}개의 마감일 지난 TODO 발견 (상위 20개 표시)\n")

for i, row in enumerate(rows, 1):
    (todo_id, title, priority, deadline, requester, todo_type, 
     status, project_tag, is_top3) = row
    
    # 마감일 계산
    deadline_dt = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
    days_overdue = (now - deadline_dt).days
    
    top3_mark = "⭐ Top3" if is_top3 else ""
    
    print(f"{i}. {todo_id} {top3_mark}")
    print(f"   제목: {title[:50] if title else ''}")
    print(f"   마감: D+{days_overdue} (지남) - {deadline}")
    print(f"   우선순위: {priority}, 유형: {todo_type}")
    print(f"   프로젝트: {project_tag}")
    print()

# 전체 통계
cursor.execute("""
    SELECT COUNT(*) 
    FROM todos 
    WHERE deadline IS NOT NULL 
      AND status != 'done'
      AND datetime(deadline) < datetime('now')
""")
total_overdue = cursor.fetchone()[0]

cursor.execute("""
    SELECT COUNT(*) 
    FROM todos 
    WHERE deadline IS NOT NULL 
      AND status != 'done'
      AND is_top3 = 1
      AND datetime(deadline) < datetime('now')
""")
overdue_in_top3 = cursor.fetchone()[0]

print("=" * 80)
print("통계:")
print("=" * 80)
print(f"마감일이 지난 pending TODO: {total_overdue}개")
print(f"마감일이 지났는데 Top3에 있는 TODO: {overdue_in_top3}개")

if overdue_in_top3 > 0:
    print("\n⚠️ 문제: 마감일이 지난 TODO가 Top3에 포함되어 있습니다!")
    print("   → 마감일이 지난 TODO는 우선순위를 낮춰야 합니다.")

conn.close()
