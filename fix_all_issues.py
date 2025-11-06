#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
모든 TODO 및 프로젝트 태그 문제 해결 스크립트
"""
import sqlite3
import json
import os
from typing import Optional

def check_and_fix_all_issues():
    """모든 문제 확인 및 수정"""
    
    print("🔍 전체 시스템 상태 확인 및 수정 시작")
    print("=" * 60)
    
    # 1. 데이터베이스 경로 확인
    vdos_db = '../virtualoffice/src/virtualoffice/vdos.db'
    todos_db = '../virtualoffice/src/virtualoffice/todos_cache.db'
    
    print(f"1. 데이터베이스 파일 확인")
    print(f"   VDOS DB: {os.path.exists(vdos_db)} ({vdos_db})")
    print(f"   TODO DB: {os.path.exists(todos_db)} ({todos_db})")
    
    if not os.path.exists(vdos_db) or not os.path.exists(todos_db):
        print("❌ 필수 데이터베이스 파일이 없습니다!")
        return False
    
    # 2. VDOS 프로젝트 확인
    print(f"\n2. VDOS 프로젝트 확인")
    vdos_conn = sqlite3.connect(vdos_db)
    vdos_cur = vdos_conn.cursor()
    
    vdos_cur.execute('SELECT id, project_name FROM project_plans ORDER BY id')
    vdos_projects = vdos_cur.fetchall()
    
    print(f"   VDOS 프로젝트: {len(vdos_projects)}개")
    for project_id, name in vdos_projects:
        print(f"     ID {project_id}: {name}")
    
    vdos_conn.close()
    
    # 3. TODO 데이터베이스 상태 확인
    print(f"\n3. TODO 데이터베이스 상태 확인")
    todos_conn = sqlite3.connect(todos_db)
    todos_cur = todos_conn.cursor()
    
    # 전체 TODO 개수
    todos_cur.execute('SELECT COUNT(*) FROM todos')
    total_todos = todos_cur.fetchone()[0]
    print(f"   전체 TODO: {total_todos}개")
    
    # 프로젝트별 분포
    todos_cur.execute('SELECT project, COUNT(*) FROM todos WHERE project IS NOT NULL GROUP BY project ORDER BY COUNT(*) DESC')
    project_dist = todos_cur.fetchall()
    
    print(f"   프로젝트별 분포:")
    for project, count in project_dist:
        print(f"     {project}: {count}개")
    
    # 프로젝트 없는 TODO
    todos_cur.execute('SELECT COUNT(*) FROM todos WHERE project IS NULL OR project = ""')
    no_project = todos_cur.fetchone()[0]
    print(f"   미분류 TODO: {no_project}개")
    
    # 4. TODO 상세 데이터 확인
    print(f"\n4. TODO 상세 데이터 샘플 확인")
    todos_cur.execute('SELECT id, title, description, source_message FROM todos WHERE description IS NOT NULL LIMIT 3')
    samples = todos_cur.fetchall()
    
    for i, (todo_id, title, desc, source) in enumerate(samples, 1):
        print(f"   {i}. {todo_id}: {title}")
        print(f"      설명 길이: {len(desc) if desc else 0}자")
        print(f"      소스 길이: {len(source) if source else 0}자")
        
        # JSON 파싱 테스트
        if source:
            try:
                source_data = json.loads(source)
                print(f"      소스 JSON: ✅ (키: {list(source_data.keys())})")
            except:
                print(f"      소스 JSON: ❌ (텍스트)")
    
    # 5. 프로젝트 태그 서비스 테스트
    print(f"\n5. 프로젝트 태그 서비스 테스트")
    try:
        import sys
        sys.path.append('src')
        from services.project_tag_service import ProjectTagService
        
        service = ProjectTagService()
        print(f"   로드된 프로젝트: {len(service.project_tags)}개")
        for code, tag in service.project_tags.items():
            print(f"     {code}: {tag.name}")
            
        # VDOS 프로젝트와 비교
        vdos_project_count = len(vdos_projects)
        loaded_project_count = len(service.project_tags)
        
        if loaded_project_count == vdos_project_count:
            print(f"   ✅ 프로젝트 개수 일치: {loaded_project_count}개")
        else:
            print(f"   ⚠️ 프로젝트 개수 불일치: VDOS {vdos_project_count}개 vs 로드 {loaded_project_count}개")
            
    except Exception as e:
        print(f"   ❌ 프로젝트 태그 서비스 오류: {e}")
    
    # 6. 권장 수정사항
    print(f"\n6. 권장 수정사항")
    
    if no_project > 0:
        print(f"   - {no_project}개 미분류 TODO 프로젝트 할당 필요")
    
    if loaded_project_count != vdos_project_count:
        print(f"   - 프로젝트 태그 서비스 수정 필요 (기본 프로젝트 제거)")
    
    print(f"\n✅ 전체 시스템 상태 확인 완료")
    
    todos_conn.close()
    return True

if __name__ == "__main__":
    check_and_fix_all_issues()