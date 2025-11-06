#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
프로젝트 태그 할당 문제 디버깅
"""
import sys
import sqlite3
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from services.project_tag_service import ProjectTagService

def main():
    print("=" * 80)
    print("프로젝트 태그 할당 문제 디버깅")
    print("=" * 80)
    
    # ProjectTagService 초기화
    service = ProjectTagService()
    
    print(f"\n📍 VDOS DB: {service.vdos_db_path}")
    print(f"📍 캐시 DB: {service.tag_cache.db_path if service.tag_cache else 'None'}")
    
    # VDOS DB에서 프로젝트 정보 확인
    print(f"\n{'='*80}")
    print("1. VDOS DB 프로젝트 정보")
    print("=" * 80)
    
    conn = sqlite3.connect(service.vdos_db_path)
    cur = conn.cursor()
    
    # 프로젝트 목록
    cur.execute("""
        SELECT id, project_name, project_summary, duration_weeks, start_week
        FROM project_plans
        ORDER BY id
    """)
    projects = cur.fetchall()
    
    print(f"\n총 {len(projects)}개 프로젝트:")
    for proj in projects:
        print(f"  ID {proj[0]}: {proj[1]}")
        print(f"    요약: {proj[2][:100] if proj[2] else 'N/A'}...")
        print(f"    기간: {proj[3]}주 (시작: Week {proj[4]})")
    
    # 프로젝트-사람 매핑
    print(f"\n{'='*80}")
    print("2. 프로젝트-사람 매핑")
    print("=" * 80)
    
    cur.execute("""
        SELECT pp.id, pp.project_name, p.name, p.email_address
        FROM project_plans pp
        JOIN project_assignments pa ON pp.id = pa.project_id
        JOIN people p ON pa.person_id = p.id
        ORDER BY pp.id, p.name
    """)
    assignments = cur.fetchall()
    
    project_people = {}
    for proj_id, proj_name, person_name, email in assignments:
        if proj_id not in project_people:
            project_people[proj_id] = {'name': proj_name, 'people': []}
        project_people[proj_id]['people'].append(f"{person_name} ({email})")
    
    for proj_id, info in project_people.items():
        print(f"\n프로젝트 {proj_id}: {info['name']}")
        for person in info['people']:
            print(f"  - {person}")
    
    # TODO 캐시 DB 확인
    print(f"\n{'='*80}")
    print("3. TODO 캐시 DB 확인")
    print("=" * 80)
    
    # TODO DB 경로 찾기
    vdos_dir = Path(service.vdos_db_path).parent
    todo_db_path = vdos_dir / "todos_cache.db"
    
    if not todo_db_path.exists():
        print(f"❌ TODO DB를 찾을 수 없습니다: {todo_db_path}")
        return
    
    print(f"📍 TODO DB: {todo_db_path}")
    
    todo_conn = sqlite3.connect(str(todo_db_path))
    todo_cur = todo_conn.cursor()
    
    # TODO 개수 확인
    todo_cur.execute("SELECT COUNT(*) FROM todos")
    todo_count = todo_cur.fetchone()[0]
    print(f"\n총 TODO 개수: {todo_count}")
    
    # 프로젝트 태그 분포
    todo_cur.execute("""
        SELECT project, COUNT(*) as cnt
        FROM todos
        GROUP BY project
        ORDER BY cnt DESC
    """)
    tag_dist = todo_cur.fetchall()
    
    print(f"\n프로젝트 태그 분포:")
    for tag, cnt in tag_dist:
        print(f"  {tag or '(없음)'}: {cnt}개")
    
    # 프로젝트 태그가 없는 TODO 샘플
    todo_cur.execute("""
        SELECT id, title, requester, description
        FROM todos
        WHERE project IS NULL OR project = '' OR project = 'Unknown'
        LIMIT 10
    """)
    untagged = todo_cur.fetchall()
    
    if untagged:
        print(f"\n{'='*80}")
        print("4. 프로젝트 태그가 없는 TODO 샘플 (최대 10개)")
        print("=" * 80)
        
        for todo_id, title, requester, desc in untagged:
            print(f"\nTODO ID: {todo_id}")
            print(f"  제목: {title}")
            print(f"  요청자: {requester}")
            print(f"  설명: {desc[:100]}...")
            
            # 이 TODO에 프로젝트 태그를 할당해보기
            test_message = {
                'title': title,
                'content': desc,
                'sender': requester
            }
            
            try:
                tag = service.extract_project_from_message(test_message)
                print(f"  → 추출된 태그: {tag}")
            except Exception as e:
                print(f"  → 태그 추출 실패: {e}")
    
    # 프로젝트 태그 캐시 확인
    if service.tag_cache:
        print(f"\n{'='*80}")
        print("5. 프로젝트 태그 캐시 확인")
        print("=" * 80)
        
        cache_conn = sqlite3.connect(service.tag_cache.db_path)
        cache_cur = cache_conn.cursor()
        
        cache_cur.execute("SELECT COUNT(*) FROM project_tag_cache")
        cache_count = cache_cur.fetchone()[0]
        print(f"\n캐시된 태그 개수: {cache_count}")
        
        if cache_count > 0:
            cache_cur.execute("""
                SELECT project_tag, COUNT(*) as cnt
                FROM project_tag_cache
                GROUP BY project_tag
                ORDER BY cnt DESC
            """)
            cache_dist = cache_cur.fetchall()
            
            print(f"\n캐시 태그 분포:")
            for tag, cnt in cache_dist:
                print(f"  {tag}: {cnt}개")
        
        cache_conn.close()
    
    # ProjectTagService의 내부 상태 확인
    print(f"\n{'='*80}")
    print("6. ProjectTagService 내부 상태")
    print("=" * 80)
    
    print(f"\n로드된 프로젝트 태그: {len(service.project_tags)}개")
    for code, tag in service.project_tags.items():
        print(f"  {code}: {tag.name} (색상: {tag.color})")
    
    print(f"\n사람-프로젝트 매핑: {len(service.person_project_mapping)}개")
    for person, projects in list(service.person_project_mapping.items())[:10]:
        print(f"  {person}: {projects}")
    
    conn.close()
    todo_conn.close()
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()
