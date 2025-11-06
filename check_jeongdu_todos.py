#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""이정두 페르소나의 TODO 및 TOP3 확인"""

import sys
import os
import sqlite3
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def check_jeongdu_todos():
    """이정두 페르소나의 TODO 확인"""
    
    print("=" * 80)
    print("이정두 페르소나 TODO 및 TOP3 확인")
    print("=" * 80)
    
    # TODO DB 경로
    todos_db = Path("offline_agent/data/multi_project_8week_ko/todos_cache.db")
    
    if not todos_db.exists():
        print(f"\n❌ TODO DB 없음: {todos_db}")
        return
    
    conn = sqlite3.connect(todos_db)
    cursor = conn.cursor()
    
    # 1. 이정두의 전체 TODO 확인
    print("\n[1] 이정두의 전체 TODO:")
    cursor.execute("""
        SELECT id, content, priority, project_tag, is_top3, created_at
        FROM todos
        WHERE persona_name = '이정두'
        ORDER BY created_at DESC
    """)
    
    todos = cursor.fetchall()
    print(f"  총 {len(todos)}개")
    
    if todos:
        print("\n  상세:")
        for todo in todos[:10]:  # 최근 10개만
            todo_id, content, priority, project_tag, is_top3, created_at = todo
            top3_mark = "⭐" if is_top3 else "  "
            print(f"    {top3_mark} [{todo_id}] {content[:50]}...")
            print(f"       우선순위: {priority}, 프로젝트: {project_tag}, TOP3: {is_top3}")
            print(f"       생성: {created_at}")
    
    # 2. TOP3 TODO 확인
    print("\n[2] 이정두의 TOP3 TODO:")
    cursor.execute("""
        SELECT id, content, priority, project_tag, created_at
        FROM todos
        WHERE persona_name = '이정두' AND is_top3 = 1
        ORDER BY priority DESC, created_at DESC
    """)
    
    top3_todos = cursor.fetchall()
    print(f"  총 {len(top3_todos)}개")
    
    if top3_todos:
        for i, todo in enumerate(top3_todos, 1):
            todo_id, content, priority, project_tag, created_at = todo
            print(f"\n  {i}. [{todo_id}] {content[:60]}...")
            print(f"     우선순위: {priority}, 프로젝트: {project_tag}")
            print(f"     생성: {created_at}")
    else:
        print("  ❌ TOP3 TODO 없음")
    
    # 3. 우선순위별 분포
    print("\n[3] 우선순위별 분포:")
    cursor.execute("""
        SELECT priority, COUNT(*) as count
        FROM todos
        WHERE persona_name = '이정두'
        GROUP BY priority
        ORDER BY priority DESC
    """)
    
    priority_dist = cursor.fetchall()
    for priority, count in priority_dist:
        print(f"  우선순위 {priority}: {count}개")
    
    # 4. 프로젝트별 분포
    print("\n[4] 프로젝트별 분포:")
    cursor.execute("""
        SELECT project_tag, COUNT(*) as count
        FROM todos
        WHERE persona_name = '이정두'
        GROUP BY project_tag
        ORDER BY count DESC
    """)
    
    project_dist = cursor.fetchall()
    for project_tag, count in project_dist:
        print(f"  {project_tag}: {count}개")
    
    # 5. 최근 생성된 TODO (TOP3 후보)
    print("\n[5] 최근 생성된 고우선순위 TODO (TOP3 후보):")
    cursor.execute("""
        SELECT id, content, priority, project_tag, is_top3, created_at
        FROM todos
        WHERE persona_name = '이정두' AND priority >= 7
        ORDER BY created_at DESC
        LIMIT 10
    """)
    
    high_priority_todos = cursor.fetchall()
    if high_priority_todos:
        for todo in high_priority_todos:
            todo_id, content, priority, project_tag, is_top3, created_at = todo
            top3_mark = "⭐" if is_top3 else "  "
            print(f"  {top3_mark} [{todo_id}] 우선순위 {priority}: {content[:50]}...")
            print(f"     프로젝트: {project_tag}, 생성: {created_at}")
    else:
        print("  ❌ 우선순위 7 이상인 TODO 없음")
    
    # 6. TOP3 선정 규칙 확인
    print("\n[6] TOP3 선정 가능 TODO (우선순위 >= 7):")
    cursor.execute("""
        SELECT COUNT(*) as count
        FROM todos
        WHERE persona_name = '이정두' AND priority >= 7
    """)
    
    eligible_count = cursor.fetchone()[0]
    print(f"  선정 가능한 TODO: {eligible_count}개")
    
    if eligible_count < 3:
        print(f"  ⚠️ TOP3 선정에 필요한 최소 개수(3개) 미달")
    
    conn.close()
    
    print("\n" + "=" * 80)
    print("확인 완료")
    print("=" * 80)

if __name__ == "__main__":
    check_jeongdu_todos()
