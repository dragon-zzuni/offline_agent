#!/usr/bin/env python3
"""
Care Connect 프로젝트 분류 최종 수정
"""

import sys
import os
sys.path.append('.')
sys.path.append('src')

import sqlite3
import json

def fix_care_connect_final():
    """Care Connect 관련 TODO를 CARE 프로젝트로 최종 수정"""
    db_path = 'C:/Users/USER/Desktop/virtual-office-orchestration/virtualoffice/src/virtualoffice/todos_cache.db'
    
    if not os.path.exists(db_path):
        print(f"❌ 데이터베이스 파일이 없습니다: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        print('=== Care Connect 프로젝트 분류 최종 수정 ===')
        
        # Care Connect 관련 TODO 찾기 (더 넓은 범위)
        cur.execute("""
            SELECT id, title, source_message, project 
            FROM todos 
            WHERE (
                source_message LIKE '%Care Connect%' OR 
                source_message LIKE '%care connect%' OR
                title LIKE '%Care Connect%'
            )
            AND status != 'done'
        """)
        care_connect_todos = cur.fetchall()
        
        print(f'Care Connect 관련 TODO 발견: {len(care_connect_todos)}개')
        
        updated_count = 0
        for todo_id, title, source_message, current_project in care_connect_todos:
            # CARE 프로젝트로 업데이트
            cur.execute('UPDATE todos SET project = ? WHERE id = ?', ('CARE', todo_id))
            updated_count += 1
            
            print(f'✅ {title} → CARE 프로젝트로 수정')
        
        # 추가로 HEAL 프로젝트로 잘못 분류된 Care Connect TODO 찾기
        cur.execute("""
            SELECT id, title, source_message 
            FROM todos 
            WHERE project = 'HEAL' 
            AND (source_message LIKE '%Care Connect%' OR source_message LIKE '%care connect%')
            AND status != 'done'
        """)
        misclassified_todos = cur.fetchall()
        
        print(f'\nHEAL로 잘못 분류된 Care Connect TODO: {len(misclassified_todos)}개')
        
        for todo_id, title, source_message in misclassified_todos:
            cur.execute('UPDATE todos SET project = ? WHERE id = ?', ('CARE', todo_id))
            updated_count += 1
            print(f'🔄 {title} → HEAL에서 CARE로 수정')
        
        if updated_count > 0:
            conn.commit()
            print(f'\n✅ 총 {updated_count}개 TODO 수정 완료')
        else:
            print('\n⚠️ 수정할 TODO가 없습니다')
        
        # 최종 프로젝트 분포 확인
        cur.execute("""
            SELECT project, COUNT(*) 
            FROM todos 
            WHERE status != 'done' AND project IS NOT NULL 
            GROUP BY project 
            ORDER BY project
        """)
        stats = cur.fetchall()
        
        print('\n=== 최종 프로젝트 분포 ===')
        for project, count in stats:
            print(f'{project}: {count}개')
        
        # Care Connect 관련 TODO 최종 확인
        cur.execute("""
            SELECT COUNT(*) 
            FROM todos 
            WHERE project = 'CARE' AND status != 'done'
        """)
        care_count = cur.fetchone()[0]
        
        print(f'\n🎯 CARE 프로젝트 TODO: {care_count}개')
        
        conn.close()
        
    except Exception as e:
        print(f'❌ 수정 실패: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix_care_connect_final()