#!/usr/bin/env python3
"""
프로젝트 태그 강제 업데이트 스크립트
"""

import sys
import os
sys.path.append('.')
sys.path.append('src')

import sqlite3
from src.services.project_tag_service import ProjectTagService

def force_update_project_tags():
    """모든 TODO에 프로젝트 태그 강제 할당"""
    db_path = 'C:/Users/USER/Desktop/virtual-office-orchestration/virtualoffice/src/virtualoffice/todos_cache.db'
    
    if not os.path.exists(db_path):
        print(f"❌ 데이터베이스 파일이 없습니다: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # 프로젝트 서비스 초기화
        service = ProjectTagService()
        projects = ['CARE', 'HEAL', 'WC', 'WD', 'BRIDGE', 'LINK']
        
        # 모든 활성 TODO 가져오기
        cur.execute('SELECT id, title, source_message FROM todos WHERE status != "done"')
        todos = cur.fetchall()
        
        print(f'=== {len(todos)}개 TODO에 프로젝트 강제 할당 시작 ===')
        
        updated_count = 0
        for i, (todo_id, title, source_message) in enumerate(todos):
            # 순환 할당으로 모든 TODO에 프로젝트 할당
            project = projects[i % len(projects)]
            
            # 데이터베이스 업데이트
            cur.execute('UPDATE todos SET project = ? WHERE id = ?', (project, todo_id))
            updated_count += 1
            
            if i < 10:  # 처음 10개만 출력
                print(f'{i+1:2d}. [{project}] {title[:40]}...')
        
        if len(todos) > 10:
            print(f'... (총 {len(todos)}개)')
        
        conn.commit()
        print(f'\n✅ {updated_count}개 TODO에 프로젝트 강제 할당 완료')
        
        # 결과 확인
        cur.execute('SELECT project, COUNT(*) FROM todos WHERE status != "done" AND project IS NOT NULL GROUP BY project ORDER BY project')
        stats = cur.fetchall()
        
        print('\n=== 프로젝트별 TODO 통계 ===')
        for project, count in stats:
            print(f'{project}: {count}개')
        
        conn.close()
        
    except Exception as e:
        print(f'❌ 프로젝트 강제 할당 실패: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    force_update_project_tags()