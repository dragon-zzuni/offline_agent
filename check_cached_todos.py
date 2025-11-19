# -*- coding: utf-8 -*-
"""
캐시된 TODO 중에서 로그에 나온 ID들 확인
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import sqlite3
from datetime import datetime
import json

# 로그에서 선정된 ID들
selected_ids = [
    "task_28bb72d8acb6",
    "review_59135d354176", 
    "task_f5ae076689bd"
]

# 캐시 DB 경로
cache_db_path = "../virtualoffice/src/virtualoffice/todos_cache.db"
if not os.path.exists(cache_db_path):
    print(f"❌ 캐시 DB를 찾을 수 없습니다: {cache_db_path}")
    sys.exit(1)

conn = sqlite3.connect(cache_db_path)
cursor = conn.cursor()

print("=" * 80)
print("LLM이 선정한 Top3 TODO 확인 (캐시 DB)")
print("=" * 80)

now = datetime.now()

for i, todo_id in enumerate(selected_ids, 1):
    # TODO 정보 가져오기
    cursor.execute("""
        SELECT id, title, description, priority, deadline, requester, type, status,
               project_tag, project_full_name, recipient_type, source_type
        FROM todos
        WHERE id = ?
    """, (todo_id,))
    
    row = cursor.fetchone()
    
    if row:
        (todo_id, title, description, priority, deadline, requester, todo_type, 
         status, project_tag, project_full_name, recipient_type, source_type) = row
        
        # 마감일 계산
        if deadline:
            deadline_dt = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
            days_left = (deadline_dt - now).days
            deadline_display = f"D-{days_left}" if days_left >= 0 else f"D+{abs(days_left)}"
        else:
            deadline_display = "없음"
        
        print(f"\n{i}. {todo_id}")
        print(f"   제목: {title[:60] if title else ''}")
        print(f"   설명: {description[:60] if description else ''}...")
        print(f"   프로젝트: {project_tag} ({project_full_name})")
        print(f"   요청자: {requester}")
        print(f"   유형: {todo_type}")
        print(f"   마감: {deadline_display} ({deadline})")
        print(f"   우선순위: {priority}")
        print(f"   상태: {status}")
        print(f"   수신방법: {source_type}")
        print(f"   수신타입: {recipient_type}")
    else:
        print(f"\n{i}. {todo_id}")
        print(f"   ❌ TODO를 찾을 수 없습니다")

conn.close()

print("\n" + "=" * 80)
print("분석:")
print("=" * 80)
print("로그에서는:")
print("  - TODO #2: 2025-11-24 마감")
print("  - TODO #3: 2025-11-24 마감")
print("  - TODO #44: 2025-12-05 마감")
print("\n실제 DB에서 확인한 마감일과 일치하는지 확인하세요.")
print("\n만약 스크린샷의 D-19 TODO가 위 3개가 아니라면,")
print("UI에 표시되는 TODO와 LLM이 선정한 TODO가 다를 수 있습니다.")
