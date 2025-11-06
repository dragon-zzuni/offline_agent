#!/usr/bin/env python3
"""
프로젝트 분류 정확성 검증
"""

import sys
import os
sys.path.append('.')
sys.path.append('src')

import sqlite3
import json
from src.services.project_tag_service import ProjectTagService

def verify_project_classification():
    """프로젝트 분류 정확성 검증"""
    db_path = 'C:/Users/USER/Desktop/virtual-office-orchestration/virtualoffice/src/virtualoffice/todos_cache.db'
    
    if not os.path.exists(db_path):
        print(f"❌ 데이터베이스 파일이 없습니다: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # 프로젝트 서비스 초기화
        service = ProjectTagService()
        
        # 프로젝트 태그 정보 확인
        print('=== 사용 가능한 프로젝트 태그 ===')
        projects = service.get_all_projects()
        for project in projects:
            print(f'{project.code}: {project.name} - {project.description}')
        
        print('\n=== Care Connect 관련 TODO 분석 ===')
        
        # Care Connect 관련 TODO 찾기
        cur.execute("""
            SELECT id, title, source_message, project 
            FROM todos 
            WHERE source_message LIKE '%Care Connect%' 
            AND status != 'done'
            ORDER BY created_at DESC
        """)
        care_connect_todos = cur.fetchall()
        
        print(f'Care Connect 관련 TODO: {len(care_connect_todos)}개')
        
        for i, (todo_id, title, source_message, current_project) in enumerate(care_connect_todos[:5], 1):
            print(f'\n{i}. TODO: {title}')
            print(f'   현재 프로젝트: {current_project}')
            
            if source_message:
                try:
                    message_data = json.loads(source_message)
                    subject = message_data.get('subject', '')
                    content = message_data.get('content', '')
                    
                    print(f'   제목: {subject}')
                    print(f'   내용: {content[:100]}...')
                    
                    # 프로젝트 추출 테스트
                    test_message = {
                        'subject': subject,
                        'content': content,
                        'sender': message_data.get('sender', '')
                    }
                    
                    extracted_project = service.extract_project_from_message(test_message)
                    print(f'   추출된 프로젝트: {extracted_project}')
                    
                    # 올바른 분류인지 확인
                    if 'care connect' in (subject + content).lower():
                        expected_project = 'CARE'
                        if current_project != expected_project:
                            print(f'   ❌ 잘못된 분류! {current_project} → {expected_project}로 수정 필요')
                        else:
                            print(f'   ✅ 올바른 분류')
                    
                except Exception as e:
                    print(f'   ❌ 메시지 파싱 실패: {e}')
        
        print('\n=== 프로젝트별 현재 분포 ===')
        cur.execute("""
            SELECT project, COUNT(*) 
            FROM todos 
            WHERE status != 'done' AND project IS NOT NULL 
            GROUP BY project 
            ORDER BY COUNT(*) DESC
        """)
        stats = cur.fetchall()
        
        for project, count in stats:
            print(f'{project}: {count}개')
        
        conn.close()
        
    except Exception as e:
        print(f'❌ 검증 실패: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_project_classification()