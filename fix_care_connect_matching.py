#!/usr/bin/env python3
"""
Care Connect 프로젝트 매칭 수정
"""

import sys
import os
sys.path.append('.')
sys.path.append('src')

import sqlite3

def fix_care_connect_matching():
    """Care Connect 관련 TODO를 CARE 프로젝트로 수정"""
    db_path = 'C:/Users/USER/Desktop/virtual-office-orchestration/virtualoffice/src/virtualoffice/todos_cache.db'
    
    if not os.path.exists(db_path):
        print(f"❌ 데이터베이스 파일이 없습니다: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # Care Connect 관련 TODO 찾기
        cur.execute("SELECT id, title, source_message FROM todos WHERE source_message LIKE '%Care Connect%' OR title LIKE '%Care Connect%'")
        rows = cur.fetchall()
        
        print('=== Care Connect 관련 TODO ===')
        for row in rows:
            print(f'ID: {row[0]}')
            print(f'제목: {row[1]}')
            print(f'메시지: {row[2][:100]}...')
            print('---')
        
        if rows:
            # Care Connect TODO들을 CARE 프로젝트로 업데이트
            care_ids = [row[0] for row in rows]
            for todo_id in care_ids:
                cur.execute('UPDATE todos SET project = ? WHERE id = ?', ('CARE', todo_id))
            
            conn.commit()
            print(f'✅ {len(care_ids)}개 Care Connect TODO를 CARE 프로젝트로 업데이트')
        else:
            print('Care Connect 관련 TODO를 찾을 수 없습니다')
            
            # 대신 현재 프로젝트 분포 확인
            cur.execute('SELECT project, COUNT(*) FROM todos WHERE status != "done" GROUP BY project')
            stats = cur.fetchall()
            
            print('\n=== 현재 프로젝트 분포 ===')
            for project, count in stats:
                print(f'{project or "미분류"}: {count}개')
        
        conn.close()
        
    except Exception as e:
        print(f'❌ 오류: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix_care_connect_matching()