#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""UNKNOWN TODO 확인"""
import sys
import os
sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('src'))

def check_unknown_todos():
    """UNKNOWN TODO 확인"""
    print("=" * 60)
    print("UNKNOWN TODO 확인")
    print("=" * 60)
    
    try:
        from utils.vdos_connector import VDOSConnector
        
        conn = VDOSConnector()
        todos = conn.get_todos_for_persona('yongjun_kim')
        
        print(f"총 {len(todos)}개 TODO\n")
        
        unknown_count = 0
        for i, todo in enumerate(todos, 1):
            project_tag = todo.get('project_tag', 'UNKNOWN')
            title = todo.get('title', 'N/A')
            description = todo.get('description', 'N/A')
            requester = todo.get('requester', 'N/A')
            
            if project_tag == 'UNKNOWN':
                unknown_count += 1
                print(f"\n{i}. [UNKNOWN] {title[:60]}")
                print(f"   요청자: {requester}")
                print(f"   내용: {description[:150]}")
                print(f"   ---")
        
        print(f"\n\n📊 통계:")
        print(f"   전체 TODO: {len(todos)}개")
        print(f"   UNKNOWN: {unknown_count}개")
        print(f"   분류됨: {len(todos) - unknown_count}개")
        
        return True
        
    except Exception as e:
        print(f"❌ 오류: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    check_unknown_todos()
