#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""전체 TODO 상태 확인"""

import sqlite3
from pathlib import Path

def check_all_todos():
    """전체 TODO 상태 확인"""
    
    print("=" * 80)
    print("전체 TODO 상태 확인")
    print("=" * 80)
    
    todos_db = Path("offline_agent/data/multi_project_8week_ko/todos_cache.db")
    
    if not todos_db.exists():
        print(f"\n❌ TODO DB 없음: {todos_db}")
        return
    
    conn = sqlite3.connect(todos_db)
    cursor = conn.cursor()
    
    # 전체 TODO 개수
    print("\n[1] 전체 TODO 개수:")
    cursor.execute("SELECT COUNT(*) FROM todos")
    total_count = cursor.fetchone()[0]
    print(f"  총 {total_count}개")
    
    # requester별 분포
    print("\n[2] requester별 분포:")
    cursor.execute("""
        SELECT requester, COUNT(*) as count
        FROM todos
        GROUP BY requester
        ORDER BY count DESC
    """)
    
    requesters = cursor.fetchall()
    for requester, count in requesters:
        print(f"  {requester if requester else '(NULL)'}: {count}개")
    
    # TOP3 상태
    print("\n[3] TOP3 상태:")
    cursor.execute("""
        SELECT requester, COUNT(*) as count
        FROM todos
        WHERE is_top3 = 1
        GROUP BY requester
        ORDER BY count DESC
    """)
    
    top3_dist = cursor.fetchall()
    if top3_dist:
        for requester, count in top3_dist:
            print(f"  {requester if requester else '(NULL)'}: {count}개")
    else:
        print("  ❌ TOP3 TODO 없음")
    
    # 최근 생성된 TODO
    print("\n[4] 최근 생성된 TODO (10개):")
    cursor.execute("""
        SELECT id, title, requester, priority, project_tag, created_at
        FROM todos
        ORDER BY created_at DESC
        LIMIT 10
    """)
    
    recent_todos = cursor.fetchall()
    for todo in recent_todos:
        todo_id, title, requester, priority, project_tag, created_at = todo
        print(f"  [{todo_id[:8]}...] {title[:40]}...")
        print(f"    요청자: {requester}, 우선순위: {priority}, 프로젝트: {project_tag}")
        print(f"    생성: {created_at}")
        print()
    
    # 우선순위 분포
    print("\n[5] 우선순위 분포:")
    cursor.execute("""
        SELECT priority, COUNT(*) as count
        FROM todos
        GROUP BY priority
        ORDER BY priority DESC
    """)
    
    priority_dist = cursor.fetchall()
    for priority, count in priority_dist:
        print(f"  우선순위 {priority if priority else '(NULL)'}: {count}개")
    
    conn.close()
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    check_all_todos()
