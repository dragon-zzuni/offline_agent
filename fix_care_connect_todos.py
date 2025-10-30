#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Care Connect TODO 프로젝트 할당 수정 스크립트
"""
import sqlite3
import re

def fix_care_connect_todos():
    """Care Connect 관련 TODO에 CARE 프로젝트 할당"""
    
    db_path = '../virtualoffice/src/virtualoffice/todos_cache.db'
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    print("🔍 Care Connect 관련 TODO 수정 시작")
    
    # Care Connect 관련 TODO 찾기 (제목 또는 설명에 포함)
    cur.execute('''
        SELECT id, title, description, project 
        FROM todos 
        WHERE (title LIKE '%Care Connect%' OR description LIKE '%Care Connect%')
        AND (project IS NULL OR project != 'CARE')
    ''')
    
    care_todos = cur.fetchall()
    print(f"수정 대상 TODO: {len(care_todos)}개")
    
    updated_count = 0
    
    for todo_id, title, desc, current_project in care_todos:
        print(f"  {todo_id}: {title} (현재: {current_project}) → CARE")
        
        # CARE 프로젝트로 업데이트
        cur.execute('UPDATE todos SET project = ? WHERE id = ?', ('CARE', todo_id))
        updated_count += 1
    
    # 다른 명확한 패턴들도 수정
    patterns = [
        ('%HealthCore%', 'HA'),
        ('%WellLink%브랜드%', 'LINK'),
        ('%WellLink%런칭%', 'LINK'),
        ('%Insight Dashboard%', 'WD'),
        ('%CareBridge%', 'BRIDGE'),
        ('%Bridge Integration%', 'BRIDGE')
    ]
    
    for pattern, project_code in patterns:
        cur.execute('''
            UPDATE todos 
            SET project = ? 
            WHERE (title LIKE ? OR description LIKE ?) 
            AND (project IS NULL OR project != ?)
        ''', (project_code, pattern, pattern, project_code))
        
        affected = cur.rowcount
        if affected > 0:
            print(f"  {pattern} → {project_code}: {affected}개 업데이트")
            updated_count += affected
    
    conn.commit()
    
    # 결과 확인
    cur.execute('SELECT project, COUNT(*) FROM todos WHERE project IS NOT NULL GROUP BY project ORDER BY COUNT(*) DESC')
    results = cur.fetchall()
    
    print(f"\n✅ {updated_count}개 TODO 업데이트 완료")
    print("\n=== 최종 프로젝트 분포 ===")
    for project, count in results:
        print(f"{project}: {count}개")
    
    # 미분류 TODO 개수
    cur.execute('SELECT COUNT(*) FROM todos WHERE project IS NULL')
    no_project = cur.fetchone()[0]
    print(f"\n미분류 TODO: {no_project}개")
    
    conn.close()

if __name__ == "__main__":
    fix_care_connect_todos()