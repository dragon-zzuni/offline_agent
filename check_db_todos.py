#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DB TODO 확인"""
import sqlite3

def check_db_todos():
    """DB TODO 확인"""
    print("=" * 60)
    print("DB TODO 확인")
    print("=" * 60)
    
    try:
        conn = sqlite3.connect('../virtualoffice/src/virtualoffice/vdos.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, title, description, project_tag, requester 
            FROM todos 
            WHERE assignee = "yongjun_kim"
            LIMIT 20
        ''')
        
        todos = cursor.fetchall()
        
        print(f"총 {len(todos)}개 TODO\n")
        
        unknown_count = 0
        for i, todo in enumerate(todos, 1):
            todo_id, title, description, project_tag, requester = todo
            
            tag = project_tag if project_tag else "UNKNOWN"
            
            if not project_tag:
                unknown_count += 1
                print(f"\n{i}. [UNKNOWN] {title[:60]}")
                print(f"   ID: {todo_id}")
                print(f"   요청자: {requester}")
                print(f"   내용: {description[:150] if description else 'N/A'}")
                print(f"   ---")
        
        print(f"\n\n📊 통계:")
        print(f"   전체 TODO: {len(todos)}개")
        print(f"   UNKNOWN (NULL): {unknown_count}개")
        print(f"   분류됨: {len(todos) - unknown_count}개")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 오류: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    check_db_todos()
