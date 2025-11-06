#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HA 태그가 달린 TODO 중 Care Connect 관련 항목 확인
"""
import sqlite3
import sys
import os
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def check_ha_todos():
    """HA 태그가 달린 TODO 확인"""
    
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
    
    # HA 태그가 달린 TODO 찾기
    cur.execute("""
        SELECT id, title, description, project, requester
        FROM todos
        WHERE project = 'HA'
        ORDER BY created_at DESC
        LIMIT 20
    """)
    
    todos = cur.fetchall()
    
    if not todos:
        print("✅ HA 태그가 달린 TODO가 없습니다")
        conn.close()
        return
    
    print(f"\n📋 HA 태그가 달린 TODO {len(todos)}개:")
    print("=" * 100)
    
    for i, todo in enumerate(todos, 1):
        print(f"\n{i}. ID: {todo['id']}")
        print(f"   제목: {todo['title']}")
        print(f"   요청자: {todo['requester']}")
        print(f"   설명: {todo['description'][:200]}...")
        print(f"   프로젝트: {todo['project']}")
        
        # Care Connect 관련 키워드 확인
        text = f"{todo['title']} {todo['description']}".lower()
        if 'care connect' in text or 'careconnect' in text:
            print(f"   ⚠️ Care Connect 관련 TODO인데 HA 태그가 달려있음!")
    
    conn.close()

if __name__ == "__main__":
    check_ha_todos()
