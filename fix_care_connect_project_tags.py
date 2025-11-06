#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Care Connect 관련 TODO의 프로젝트 태그를 수정하는 스크립트
"""
import sqlite3
import sys
import os
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def fix_care_connect_tags():
    """Care Connect 관련 TODO의 프로젝트 태그를 CARE로 수정"""
    
    # VDOS DB 경로 찾기
    vdos_db_paths = [
        Path("../virtualoffice/src/virtualoffice/vdos.db"),
        Path("../../virtualoffice/src/virtualoffice/vdos.db"),
    ]
    
    vdos_db_path = None
    for path in vdos_db_paths:
        if path.exists():
            vdos_db_path = str(path.resolve())
            break
    
    if not vdos_db_path:
        print("❌ VDOS 데이터베이스를 찾을 수 없습니다")
        return
    
    # TODO DB 경로 (VDOS DB와 같은 디렉토리)
    todo_db_path = Path(vdos_db_path).parent / "todos_cache.db"
    
    if not todo_db_path.exists():
        print(f"❌ TODO 데이터베이스를 찾을 수 없습니다: {todo_db_path}")
        return
    
    print(f"✅ TODO DB 발견: {todo_db_path}")
    
    # DB 연결
    conn = sqlite3.connect(str(todo_db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Care Connect 관련 TODO 찾기
    cur.execute("""
        SELECT id, title, description, project
        FROM todos
        WHERE (
            title LIKE '%Care Connect%' OR
            title LIKE '%care connect%' OR
            title LIKE '%CareConnect%' OR
            description LIKE '%Care Connect%' OR
            description LIKE '%care connect%' OR
            description LIKE '%CareConnect%'
        )
        AND project != 'CARE'
    """)
    
    todos = cur.fetchall()
    
    if not todos:
        print("✅ 수정할 TODO가 없습니다 (모든 Care Connect TODO가 이미 CARE 태그를 가지고 있음)")
        conn.close()
        return
    
    print(f"\n📋 {len(todos)}개의 Care Connect TODO 발견:")
    for todo in todos:
        print(f"  - ID: {todo['id']}")
        print(f"    제목: {todo['title'][:50]}...")
        print(f"    현재 프로젝트: {todo['project'] or '(없음)'}")
        print()
    
    # 사용자 확인
    response = input(f"\n이 {len(todos)}개 TODO의 프로젝트 태그를 CARE로 변경하시겠습니까? (y/n): ")
    
    if response.lower() != 'y':
        print("❌ 취소되었습니다")
        conn.close()
        return
    
    # 프로젝트 태그 업데이트
    updated_count = 0
    for todo in todos:
        cur.execute("""
            UPDATE todos
            SET project = 'CARE'
            WHERE id = ?
        """, (todo['id'],))
        updated_count += 1
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ {updated_count}개 TODO의 프로젝트 태그를 CARE로 변경했습니다")
    print("\n💡 GUI를 재시작하거나 새로고침하면 변경사항이 반영됩니다")

if __name__ == "__main__":
    fix_care_connect_tags()
