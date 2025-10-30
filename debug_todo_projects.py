#!/usr/bin/env python3
"""
TODO 프로젝트 데이터 디버깅
"""

import sys
import os
sys.path.append('.')
sys.path.append('src')

import sqlite3

def check_todo_projects():
    """TODO 프로젝트 데이터 확인"""
    db_path = 'C:/Users/USER/Desktop/virtual-office-orchestration/virtualoffice/src/virtualoffice/todos_cache.db'
    
    if not os.path.exists(db_path):
        print(f"❌ 데이터베이스 파일이 없습니다: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # 현재 TODO 데이터 확인
        cur.execute('SELECT id, title, project, status FROM todos ORDER BY created_at DESC LIMIT 5')
        rows = cur.fetchall()
        
        print('=== 최근 TODO 데이터 ===')
        for row in rows:
            print(f'ID: {row[0]}')
            print(f'제목: {row[1][:40]}...')
            print(f'프로젝트: {row[2]}')
            print(f'상태: {row[3]}')
            print('---')
        
        # 프로젝트별 통계 (활성 TODO만)
        cur.execute('SELECT project, COUNT(*) FROM todos WHERE status != "done" GROUP BY project')
        stats = cur.fetchall()
        
        print('=== 활성 TODO 프로젝트 통계 ===')
        for project, count in stats:
            project_name = project if project else '미분류'
            print(f'{project_name}: {count}개')
        
        # 전체 TODO 개수
        cur.execute('SELECT COUNT(*) FROM todos WHERE status != "done"')
        total_active = cur.fetchone()[0]
        print(f'\n전체 활성 TODO: {total_active}개')
        
        conn.close()
        
    except Exception as e:
        print(f'데이터베이스 확인 실패: {e}')

if __name__ == "__main__":
    check_todo_projects()