#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
특정 HA 태그 TODO를 CARE로 수정
"""
import sqlite3
import sys
import os
from pathlib import Path
import json

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def fix_specific_todo():
    """특정 TODO의 프로젝트 태그 수정"""
    
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
    
    # 스크린샷의 TODO 찾기: 요청자가 jungjiwon이고 유형이 meeting이고 HA 태그
    cur.execute("""
        SELECT id, title, description, project, requester, type, source_message
        FROM todos
        WHERE requester = 'jungjiwon@koreaitcompany.com'
        AND type = 'meeting'
        AND project = 'HA'
        ORDER BY created_at DESC
        LIMIT 10
    """)
    
    todos = cur.fetchall()
    
    if not todos:
        print("✅ 해당 조건의 TODO가 없습니다")
        conn.close()
        return
    
    print(f"\n📋 {len(todos)}개의 TODO 발견:")
    print("=" * 100)
    
    care_connect_todos = []
    
    for i, todo in enumerate(todos, 1):
        print(f"\n{i}. ID: {todo['id']}")
        print(f"   제목: {todo['title']}")
        print(f"   요청자: {todo['requester']}")
        print(f"   유형: {todo['type']}")
        print(f"   프로젝트: {todo['project']}")
        
        # source_message 확인
        source_message = todo['source_message']
        if source_message:
            try:
                msg_data = json.loads(source_message)
                msg_subject = msg_data.get('subject', '')
                msg_content = msg_data.get('content', '')
                
                print(f"   원본 메시지 제목: {msg_subject[:100]}")
                
                # Care Connect 관련 확인
                text = f"{msg_subject} {msg_content}".lower()
                if 'care connect' in text or 'careconnect' in text:
                    print(f"   ⚠️ Care Connect 관련 메시지!")
                    care_connect_todos.append(todo)
            except:
                pass
    
    if not care_connect_todos:
        print("\n✅ Care Connect 관련 TODO가 없습니다")
        conn.close()
        return
    
    print(f"\n\n📌 Care Connect 관련 TODO {len(care_connect_todos)}개 발견!")
    
    # 사용자 확인
    response = input(f"\n이 {len(care_connect_todos)}개 TODO의 프로젝트 태그를 CARE로 변경하시겠습니까? (y/n): ")
    
    if response.lower() != 'y':
        print("❌ 취소되었습니다")
        conn.close()
        return
    
    # 프로젝트 태그 업데이트
    updated_count = 0
    for todo in care_connect_todos:
        cur.execute("""
            UPDATE todos
            SET project = 'CARE'
            WHERE id = ?
        """, (todo['id'],))
        updated_count += 1
        print(f"✅ {todo['id']} → CARE")
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ {updated_count}개 TODO의 프로젝트 태그를 CARE로 변경했습니다")
    print("\n💡 GUI를 재시작하거나 새로고침하면 변경사항이 반영됩니다")

if __name__ == "__main__":
    fix_specific_todo()
