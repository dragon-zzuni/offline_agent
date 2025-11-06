#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""올바른 TODO DB 확인"""

import sqlite3
from pathlib import Path

def check_correct_db():
    """올바른 TODO DB 확인"""
    
    print("=" * 80)
    print("올바른 TODO DB 확인")
    print("=" * 80)
    
    # GUI가 사용하는 DB
    gui_db = Path("virtualoffice/src/virtualoffice/todos_cache.db")
    
    if not gui_db.exists():
        print(f"\n❌ GUI DB 없음: {gui_db}")
        return
    
    print(f"\n✅ GUI DB 존재: {gui_db}")
    print(f"파일 크기: {gui_db.stat().st_size:,} bytes")
    
    conn = sqlite3.connect(gui_db)
    cursor = conn.cursor()
    
    # 전체 TODO 개수
    cursor.execute("SELECT COUNT(*) FROM todos")
    total_count = cursor.fetchone()[0]
    print(f"\n[1] 전체 TODO: {total_count}개")
    
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
    
    # 이정두의 TODO
    print("\n[4] 이정두의 TODO:")
    cursor.execute("""
        SELECT id, title, priority, is_top3
        FROM todos
        WHERE requester = '이정두'
        ORDER BY priority DESC
        LIMIT 10
    """)
    
    jeongdu_todos = cursor.fetchall()
    if jeongdu_todos:
        for todo in jeongdu_todos:
            todo_id, title, priority, is_top3 = todo
            top3_mark = "⭐" if is_top3 else "  "
            print(f"  {top3_mark} [{todo_id[:8]}...] 우선순위 {priority}: {title[:50]}...")
    else:
        print("  ❌ 이정두의 TODO 없음")
    
    # 이정두의 TOP3
    print("\n[5] 이정두의 TOP3:")
    cursor.execute("""
        SELECT id, title, priority
        FROM todos
        WHERE requester = '이정두' AND is_top3 = 1
        ORDER BY priority DESC
    """)
    
    top3_todos = cursor.fetchall()
    if top3_todos:
        for i, todo in enumerate(top3_todos, 1):
            todo_id, title, priority = todo
            print(f"  {i}. [{todo_id[:8]}...] 우선순위 {priority}: {title[:50]}...")
    else:
        print("  ❌ 이정두의 TOP3 없음")
    
    conn.close()
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    check_correct_db()
