#!/usr/bin/env python3
"""
프로젝트 태그 수정 및 할당
"""

import sys
import os
sys.path.append('.')
sys.path.append('src')

import sqlite3
import json
from src.services.project_tag_service import ProjectTagService

def assign_test_projects():
    """테스트용 프로젝트 할당"""
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
        
        # 활성 TODO 가져오기
        cur.execute('SELECT id, title, source_message FROM todos WHERE status != "done" AND project IS NULL LIMIT 20')
        todos = cur.fetchall()
        
        print(f'=== {len(todos)}개 TODO에 프로젝트 할당 시작 ===')
        
        updated_count = 0
        for i, (todo_id, title, source_message) in enumerate(todos):
            # 1. 메시지 기반 프로젝트 추출 시도
            project = None
            if source_message:
                try:
                    if source_message.startswith('{'):
                        message_data = json.loads(source_message)
                    else:
                        message_data = {'content': source_message}
                    
                    project = service.extract_project_from_message(message_data)
                except Exception as e:
                    pass
            
            # 2. 추출 실패 시 순환 할당
            if not project:
                project = projects[i % len(projects)]
            
            # 3. 데이터베이스 업데이트
            cur.execute('UPDATE todos SET project = ? WHERE id = ?', (project, todo_id))
            updated_count += 1
            
            print(f'{i+1:2d}. [{project}] {title[:40]}...')
        
        conn.commit()
        print(f'\n✅ {updated_count}개 TODO에 프로젝트 할당 완료')
        
        # 결과 확인
        cur.execute('SELECT project, COUNT(*) FROM todos WHERE status != "done" AND project IS NOT NULL GROUP BY project ORDER BY project')
        stats = cur.fetchall()
        
        print('\n=== 프로젝트별 TODO 통계 ===')
        for project, count in stats:
            print(f'{project}: {count}개')
        
        conn.close()
        
    except Exception as e:
        print(f'❌ 프로젝트 할당 실패: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    assign_test_projects()