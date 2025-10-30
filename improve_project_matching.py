#!/usr/bin/env python3
"""
프로젝트 매칭 정확도 개선 스크립트
"""

import sys
import os
sys.path.append('.')
sys.path.append('src')

import sqlite3
import json
from src.services.project_tag_service import ProjectTagService

def improve_project_matching():
    """프로젝트 매칭 정확도 개선"""
    db_path = 'C:/Users/USER/Desktop/virtual-office-orchestration/virtualoffice/src/virtualoffice/todos_cache.db'
    
    if not os.path.exists(db_path):
        print(f"❌ 데이터베이스 파일이 없습니다: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # 프로젝트 서비스 초기화
        service = ProjectTagService()
        
        # 모든 활성 TODO 가져오기
        cur.execute('SELECT id, title, source_message FROM todos WHERE status != "done"')
        todos = cur.fetchall()
        
        print(f'=== {len(todos)}개 TODO 프로젝트 매칭 개선 시작 ===')
        
        updated_count = 0
        for i, (todo_id, title, source_message) in enumerate(todos):
            if i >= 10:  # 처음 10개만 처리
                break
                
            project = None
            
            # 1. source_message에서 프로젝트 추출 시도
            if source_message:
                try:
                    if source_message.startswith('{'):
                        message_data = json.loads(source_message)
                    else:
                        message_data = {'content': source_message, 'subject': title}
                    
                    # 제목과 내용을 모두 포함해서 분석
                    enhanced_message = {
                        'content': f"{title} {message_data.get('content', '')} {message_data.get('subject', '')}",
                        'subject': message_data.get('subject', title),
                        'sender': message_data.get('sender', '')
                    }
                    
                    project = service.extract_project_from_message(enhanced_message)
                    
                    print(f'{i+1:2d}. TODO: {title[:40]}...')
                    print(f'     메시지: {str(enhanced_message.get("content", ""))[:60]}...')
                    print(f'     추출된 프로젝트: {project}')
                    
                except Exception as e:
                    print(f'     ❌ 메시지 파싱 실패: {e}')
            
            # 2. 프로젝트가 추출되면 DB 업데이트
            if project:
                cur.execute('UPDATE todos SET project = ? WHERE id = ?', (project, todo_id))
                updated_count += 1
                print(f'     ✅ {project} 프로젝트로 업데이트')
            else:
                print(f'     ⚠️ 프로젝트 추출 실패')
            
            print()
        
        if updated_count > 0:
            conn.commit()
            print(f'✅ {updated_count}개 TODO 프로젝트 매칭 개선 완료')
        else:
            print('⚠️ 개선된 TODO가 없습니다')
        
        conn.close()
        
    except Exception as e:
        print(f'❌ 프로젝트 매칭 개선 실패: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    improve_project_matching()