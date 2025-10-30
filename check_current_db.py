#!/usr/bin/env python3
"""
현재 사용 중인 데이터베이스 상태 확인
"""

import sqlite3
import json
import os

# VDOS 데이터베이스 경로
DB_PATH = "../virtualoffice/src/virtualoffice/todos_cache.db"

def check_current_db():
    """현재 데이터베이스 상태 확인"""
    if not os.path.exists(DB_PATH):
        print(f"❌ 데이터베이스 파일이 없습니다: {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # 전체 통계
    cur.execute("SELECT COUNT(*) FROM todos")
    total = cur.fetchone()[0]
    print(f"📊 전체 TODO: {total}개")
    
    # 프로젝트 분포
    cur.execute("SELECT project, COUNT(*) FROM todos WHERE project IS NOT NULL GROUP BY project ORDER BY COUNT(*) DESC")
    projects = cur.fetchall()
    print(f"🏷️ 프로젝트 분포: {projects}")
    
    # 프로젝트가 없는 TODO 개수
    cur.execute("SELECT COUNT(*) FROM todos WHERE project IS NULL OR project = ''")
    no_project = cur.fetchone()[0]
    print(f"❌ 프로젝트 미할당: {no_project}개")
    
    # 원본 메시지가 있는 TODO 확인
    cur.execute("SELECT COUNT(*) FROM todos WHERE source_message IS NOT NULL AND source_message != ''")
    with_msg = cur.fetchone()[0]
    print(f"📄 원본 메시지 있는 TODO: {with_msg}개")
    
    # 샘플 TODO 확인 (프로젝트와 원본 메시지 포함)
    cur.execute("""
        SELECT id, title, project, source_message 
        FROM todos 
        WHERE source_message IS NOT NULL AND source_message != ''
        LIMIT 5
    """)
    samples = cur.fetchall()
    
    print("\n📋 샘플 TODO (원본 메시지 포함):")
    for todo_id, title, project, source_msg in samples:
        print(f"\n  ID: {todo_id}")
        print(f"  제목: {title[:50]}...")
        print(f"  프로젝트: {project}")
        
        # 원본 메시지 파싱
        if source_msg:
            try:
                if source_msg.startswith('{'):
                    msg_data = json.loads(source_msg)
                    sender = msg_data.get("sender", "")
                    subject = msg_data.get("subject", "")
                    content = msg_data.get("content", "")
                    print(f"  발신자: {sender}")
                    if subject:
                        print(f"  제목: {subject}")
                    print(f"  내용: {content[:100]}...")
                else:
                    print(f"  원본: {source_msg[:100]}...")
            except Exception as e:
                print(f"  파싱 오류: {e}")
    
    conn.close()

if __name__ == "__main__":
    print("🔍 현재 사용 중인 데이터베이스 상태 확인")
    print("=" * 50)
    check_current_db()