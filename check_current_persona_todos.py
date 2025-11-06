# -*- coding: utf-8 -*-
"""
현재 페르소나의 TODO 확인 스크립트

김세린 페르소나의 TODO가 몇 개인지, 프로젝트 태그가 있는지 확인합니다.
"""
import sqlite3
import os

def check_persona_todos():
    """페르소나별 TODO 확인"""
    db_path = "virtualoffice/src/virtualoffice/vdos.db"
    
    if not os.path.exists(db_path):
        print(f"❌ DB 파일을 찾을 수 없습니다: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("=" * 80)
    print("페르소나별 TODO 분석")
    print("=" * 80)
    
    # 1. todos_cache.db 확인
    todos_db_path = "virtualoffice/src/virtualoffice/todos_cache.db"
    if os.path.exists(todos_db_path):
        todos_conn = sqlite3.connect(todos_db_path)
        todos_cursor = todos_conn.cursor()
        
        # 전체 TODO 개수
        todos_cursor.execute("SELECT COUNT(*) FROM todos")
        total_todos = todos_cursor.fetchone()[0]
        print(f"\n📋 전체 TODO: {total_todos}개")
        
        # 페르소나별 TODO 개수
        todos_cursor.execute("""
            SELECT persona_name, COUNT(*) as count
            FROM todos
            WHERE persona_name IS NOT NULL
            GROUP BY persona_name
            ORDER BY count DESC
        """)
        
        print("\n👤 페르소나별 TODO:")
        for row in todos_cursor.fetchall():
            persona_name, count = row
            print(f"  - {persona_name}: {count}개")
        
        # 김세린 TODO 상세 확인
        print("\n" + "=" * 80)
        print("김세린 TODO 상세 분석")
        print("=" * 80)
        
        todos_cursor.execute("""
            SELECT id, title, type, project, requester, created_at
            FROM todos
            WHERE persona_name = '김세린'
            ORDER BY created_at DESC
            LIMIT 10
        """)
        
        serin_todos = todos_cursor.fetchall()
        print(f"\n📋 김세린 TODO (최근 10개): {len(serin_todos)}개")
        
        project_count = 0
        no_project_count = 0
        
        for i, row in enumerate(serin_todos, 1):
            todo_id, title, todo_type, project, requester, created_at = row
            has_project = project and project.strip()
            
            if has_project:
                project_count += 1
                project_tag = f"[{project}]"
            else:
                no_project_count += 1
                project_tag = "[프로젝트 없음]"
            
            print(f"\n  {i}. {project_tag} {title}")
            print(f"     타입: {todo_type}, 요청자: {requester}")
            print(f"     생성: {created_at}")
        
        print(f"\n📊 프로젝트 태그 통계:")
        print(f"  - 프로젝트 태그 있음: {project_count}개")
        print(f"  - 프로젝트 태그 없음: {no_project_count}개")
        print(f"  - 태그 비율: {project_count / len(serin_todos) * 100:.1f}%")
        
        # 프로젝트 태그 캐시 확인
        cache_db_path = "virtualoffice/src/virtualoffice/project_tags_cache.db"
        if os.path.exists(cache_db_path):
            print(f"\n💾 프로젝트 태그 캐시 DB 발견: {cache_db_path}")
            cache_conn = sqlite3.connect(cache_db_path)
            cache_cursor = cache_conn.cursor()
            
            cache_cursor.execute("SELECT COUNT(*) FROM project_tag_cache")
            cache_count = cache_cursor.fetchone()[0]
            print(f"  - 캐시된 태그: {cache_count}개")
            
            cache_conn.close()
        else:
            print(f"\n⚠️ 프로젝트 태그 캐시 DB 없음: {cache_db_path}")
        
        todos_conn.close()
    else:
        print(f"\n❌ todos_cache.db를 찾을 수 없습니다: {todos_db_path}")
    
    conn.close()
    print("\n" + "=" * 80)


if __name__ == "__main__":
    check_persona_todos()
