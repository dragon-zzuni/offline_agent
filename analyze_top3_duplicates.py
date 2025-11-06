#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TOP3 중복 문제 분석"""

import sqlite3
from pathlib import Path

def analyze_top3_duplicates():
    """TOP3 중복 문제 분석"""
    
    print("=" * 80)
    print("TOP3 중복 문제 분석")
    print("=" * 80)
    
    todos_db = Path("virtualoffice/src/virtualoffice/todos_cache.db")
    
    if not todos_db.exists():
        print(f"\n❌ TODO DB 없음: {todos_db}")
        return
    
    conn = sqlite3.connect(todos_db)
    cursor = conn.cursor()
    
    # TOP3 TODO 조회
    print("\n[1] 현재 TOP3 TODO:")
    cursor.execute("""
        SELECT id, title, description, type, priority, requester, 
               source_message, project_tag, is_top3
        FROM todos
        WHERE is_top3 = 1
        ORDER BY priority DESC, created_at DESC
    """)
    
    top3_todos = cursor.fetchall()
    print(f"  총 {len(top3_todos)}개")
    
    if not top3_todos:
        print("  ❌ TOP3 TODO 없음")
        conn.close()
        return
    
    for i, todo in enumerate(top3_todos, 1):
        todo_id, title, description, todo_type, priority, requester, source_msg, project_tag, is_top3 = todo
        print(f"\n  {i}. [{todo_id[:8]}...] {title}")
        print(f"     유형: {todo_type}")
        print(f"     우선순위: {priority}")
        print(f"     요청자: {requester}")
        print(f"     프로젝트: {project_tag}")
        print(f"     설명: {description[:100] if description else 'N/A'}...")
        print(f"     원본 메시지 ID: {source_msg[:50] if source_msg else 'N/A'}...")
    
    # 중복 분석
    print("\n[2] 중복 분석:")
    
    # 같은 source_message를 가진 TODO 찾기
    cursor.execute("""
        SELECT source_message, COUNT(*) as count, GROUP_CONCAT(type) as types
        FROM todos
        WHERE is_top3 = 1 AND source_message IS NOT NULL
        GROUP BY source_message
        HAVING count > 1
    """)
    
    duplicates = cursor.fetchall()
    if duplicates:
        print(f"  ⚠️ 같은 원본 메시지에서 생성된 중복 TODO: {len(duplicates)}개")
        for source_msg, count, types in duplicates:
            print(f"\n    원본 메시지: {source_msg[:50]}...")
            print(f"    중복 개수: {count}개")
            print(f"    유형들: {types}")
            
            # 해당 TODO들의 상세 정보
            cursor.execute("""
                SELECT id, title, type, priority
                FROM todos
                WHERE source_message = ? AND is_top3 = 1
            """, (source_msg,))
            
            dup_todos = cursor.fetchall()
            for dup_id, dup_title, dup_type, dup_priority in dup_todos:
                print(f"      - [{dup_id[:8]}...] {dup_type}: {dup_title[:40]}... (우선순위: {dup_priority})")
    else:
        print("  ✅ 같은 원본 메시지에서 생성된 중복 없음")
    
    # 비슷한 제목을 가진 TODO 찾기
    print("\n[3] 비슷한 제목 분석:")
    cursor.execute("""
        SELECT id, title, type, priority, source_message
        FROM todos
        WHERE is_top3 = 1
        ORDER BY title
    """)
    
    similar_todos = cursor.fetchall()
    
    # 제목의 첫 30자로 그룹화
    title_groups = {}
    for todo_id, title, todo_type, priority, source_msg in similar_todos:
        title_key = title[:30] if title else ""
        if title_key not in title_groups:
            title_groups[title_key] = []
        title_groups[title_key].append((todo_id, title, todo_type, priority, source_msg))
    
    # 2개 이상인 그룹만 출력
    has_similar = False
    for title_key, todos in title_groups.items():
        if len(todos) > 1:
            has_similar = True
            print(f"\n  ⚠️ 비슷한 제목: '{title_key}...'")
            for todo_id, title, todo_type, priority, source_msg in todos:
                print(f"    - [{todo_id[:8]}...] {todo_type}: {title[:50]}... (우선순위: {priority})")
                print(f"      원본: {source_msg[:50] if source_msg else 'N/A'}...")
    
    if not has_similar:
        print("  ✅ 비슷한 제목의 TODO 없음")
    
    # 전체 TODO 중 같은 source_message를 가진 것들
    print("\n[4] 전체 TODO 중 중복 원본 메시지:")
    cursor.execute("""
        SELECT source_message, COUNT(*) as count, GROUP_CONCAT(type) as types, GROUP_CONCAT(is_top3) as top3_flags
        FROM todos
        WHERE source_message IS NOT NULL
        GROUP BY source_message
        HAVING count > 1
        ORDER BY count DESC
        LIMIT 10
    """)
    
    all_duplicates = cursor.fetchall()
    if all_duplicates:
        print(f"  ⚠️ 중복 원본 메시지: {len(all_duplicates)}개 (상위 10개)")
        for source_msg, count, types, top3_flags in all_duplicates:
            print(f"\n    원본 메시지: {source_msg[:50]}...")
            print(f"    중복 개수: {count}개")
            print(f"    유형들: {types}")
            print(f"    TOP3 포함: {top3_flags}")
    else:
        print("  ✅ 중복 원본 메시지 없음")
    
    conn.close()
    
    print("\n" + "=" * 80)
    print("분석 완료")
    print("=" * 80)

if __name__ == "__main__":
    analyze_top3_duplicates()
