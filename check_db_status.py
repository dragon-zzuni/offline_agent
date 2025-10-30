#!/usr/bin/env python3
"""
데이터베이스 상태 확인
"""

import sqlite3
import os

def check_db_status():
    """데이터베이스 상태 확인"""
    db_path = 'C:/Users/USER/Desktop/virtual-office-orchestration/virtualoffice/src/virtualoffice/todos_cache.db'
    print(f'DB 파일 존재: {os.path.exists(db_path)}')

    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # 테이블 구조 확인
        cur.execute('PRAGMA table_info(todos)')
        columns = cur.fetchall()
        print('테이블 컬럼:', [col[1] for col in columns])
        
        # 전체 TODO 개수
        cur.execute('SELECT COUNT(*) FROM todos')
        total = cur.fetchone()[0]
        print(f'전체 TODO: {total}개')
        
        # 프로젝트가 있는 TODO
        cur.execute('SELECT COUNT(*) FROM todos WHERE project IS NOT NULL AND project != ""')
        with_project = cur.fetchone()[0]
        print(f'프로젝트 있는 TODO: {with_project}개')
        
        # 프로젝트별 분포
        cur.execute('SELECT project, COUNT(*) FROM todos WHERE project IS NOT NULL AND project != "" GROUP BY project')
        stats = cur.fetchall()
        print('프로젝트 분포:', stats)
        
        # Care Connect 관련 TODO 직접 확인
        cur.execute('SELECT id, title, project FROM todos WHERE source_message LIKE "%Care Connect%" LIMIT 3')
        care_todos = cur.fetchall()
        print('\nCare Connect TODO 샘플:')
        for todo_id, title, project in care_todos:
            print(f'  {todo_id}: {title} → {project}')
        
        conn.close()

if __name__ == "__main__":
    check_db_status()