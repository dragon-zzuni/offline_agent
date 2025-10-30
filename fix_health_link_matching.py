#!/usr/bin/env python3
"""
Health Link 프로젝트 매칭 수정
"""

import sys
import os
sys.path.append('.')
sys.path.append('src')

import sqlite3
import json

def fix_health_link_matching():
    """Health Link와 Care Connect 프로젝트 매칭 수정"""
    db_path = 'C:/Users/USER/Desktop/virtual-office-orchestration/virtualoffice/src/virtualoffice/todos_cache.db'
    
    if not os.path.exists(db_path):
        print(f"❌ 데이터베이스 파일이 없습니다: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # 모든 TODO의 source_message 분석
        cur.execute("SELECT id, title, source_message, project FROM todos WHERE status != 'done'")
        todos = cur.fetchall()
        
        updated_count = 0
        
        print('=== 프로젝트 매칭 분석 및 수정 ===')
        
        for todo_id, title, source_message, current_project in todos:
            if source_message:
                try:
                    # JSON 파싱
                    if source_message.startswith('{'):
                        message_data = json.loads(source_message)
                        subject = message_data.get('subject', '')
                        content = message_data.get('content', '')
                        
                        # 프로젝트 매칭 로직
                        new_project = None
                        
                        # Care Connect 관련
                        if any(keyword in (subject + content).lower() for keyword in ['care connect', 'careconnect']):
                            new_project = 'CARE'
                        
                        # Health Link 관련 (실제로는 없어야 함 - Care Connect로 통합)
                        elif any(keyword in (subject + content).lower() for keyword in ['health link', 'healthlink']):
                            new_project = 'CARE'  # Health Link도 Care Connect로 통합
                        
                        # WellCare 관련
                        elif any(keyword in (subject + content).lower() for keyword in ['wellcare', 'well care']):
                            new_project = 'WC'
                        
                        # WellData 관련
                        elif any(keyword in (subject + content).lower() for keyword in ['welldata', 'well data']):
                            new_project = 'WD'
                        
                        # CareBridge 관련
                        elif any(keyword in (subject + content).lower() for keyword in ['carebridge', 'care bridge']):
                            new_project = 'BRIDGE'
                        
                        # WellLink 관련
                        elif any(keyword in (subject + content).lower() for keyword in ['welllink', 'well link']):
                            new_project = 'LINK'
                        
                        # 프로젝트가 변경되어야 하는 경우
                        if new_project and new_project != current_project:
                            cur.execute('UPDATE todos SET project = ? WHERE id = ?', (new_project, todo_id))
                            updated_count += 1
                            
                            print(f'📝 {title[:30]}...')
                            print(f'   제목/내용: {(subject + " " + content)[:60]}...')
                            print(f'   {current_project} → {new_project}')
                            print()
                
                except Exception as e:
                    continue
        
        if updated_count > 0:
            conn.commit()
            print(f'✅ {updated_count}개 TODO 프로젝트 매칭 수정 완료')
        else:
            print('⚠️ 수정할 TODO가 없습니다')
        
        # 최종 프로젝트 분포 확인
        cur.execute('SELECT project, COUNT(*) FROM todos WHERE status != "done" GROUP BY project ORDER BY project')
        stats = cur.fetchall()
        
        print('\n=== 최종 프로젝트 분포 ===')
        for project, count in stats:
            print(f'{project or "미분류"}: {count}개')
        
        conn.close()
        
    except Exception as e:
        print(f'❌ 오류: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix_health_link_matching()