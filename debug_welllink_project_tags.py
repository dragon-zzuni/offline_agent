#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WellLink 프로젝트 태그 디버깅 스크립트

실제 TODO 데이터에서 WellLink 관련 항목들의 프로젝트 태그가 
올바르게 설정되어 있는지 확인합니다.
"""
import sys
import os
sys.path.append('.')
sys.path.append('src')

import sqlite3
import json
from src.services.project_tag_service import ProjectTagService

def main():
    print("=== WellLink 프로젝트 태그 디버깅 ===\n")
    
    # 1. 프로젝트 태그 서비스 확인
    print("1. 프로젝트 태그 서비스 초기화...")
    service = ProjectTagService()
    
    print("   로드된 프로젝트:")
    for code, tag in service.project_tags.items():
        print(f"   - {code}: {tag.name}")
    
    # 2. TODO 데이터베이스 확인
    print("\n2. TODO 데이터베이스 확인...")
    db_path = 'data/multi_project_8week_ko/todos_cache.db'
    
    if not os.path.exists(db_path):
        print(f"   ❌ 데이터베이스 파일을 찾을 수 없음: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # 전체 TODO 개수 확인
    cur.execute('SELECT COUNT(*) FROM todos')
    total_count = cur.fetchone()[0]
    print(f"   전체 TODO 개수: {total_count}")
    
    # 프로젝트 태그별 분포 확인
    cur.execute('SELECT project_tag, COUNT(*) FROM todos GROUP BY project_tag ORDER BY COUNT(*) DESC')
    project_distribution = cur.fetchall()
    print("   프로젝트 태그 분포:")
    for project, count in project_distribution:
        print(f"   - {project}: {count}개")
    
    # 3. WellLink 관련 TODO 찾기
    print("\n3. WellLink 관련 TODO 검색...")
    
    # 제목에서 WellLink 검색
    cur.execute('''
        SELECT id, title, project_tag, recipient_type, source_message 
        FROM todos 
        WHERE title LIKE '%WellLink%' OR title LIKE '%welllink%' OR title LIKE '%WELLLINK%'
        LIMIT 10
    ''')
    
    welllink_todos = cur.fetchall()
    if welllink_todos:
        print(f"   제목에 WellLink가 포함된 TODO: {len(welllink_todos)}개")
        for todo in welllink_todos:
            print(f"   - ID: {todo[0]}")
            print(f"     제목: {todo[1][:60]}...")
            print(f"     프로젝트 태그: {todo[2]}")
            print(f"     수신 타입: {todo[3]}")
    else:
        print("   제목에 WellLink가 포함된 TODO 없음")
    
    # 설명에서 WellLink 검색
    cur.execute('''
        SELECT id, title, description, project_tag, recipient_type 
        FROM todos 
        WHERE description LIKE '%WellLink%' OR description LIKE '%welllink%' OR description LIKE '%WELLLINK%'
        LIMIT 10
    ''')
    
    desc_todos = cur.fetchall()
    if desc_todos:
        print(f"\n   설명에 WellLink가 포함된 TODO: {len(desc_todos)}개")
        for todo in desc_todos:
            print(f"   - ID: {todo[0]}")
            print(f"     제목: {todo[1][:60]}...")
            print(f"     설명: {todo[2][:60]}...")
            print(f"     프로젝트 태그: {todo[3]}")
            print(f"     수신 타입: {todo[4]}")
    else:
        print("   설명에 WellLink가 포함된 TODO 없음")
    
    # 소스 메시지에서 WellLink 검색
    cur.execute('''
        SELECT id, title, project_tag, recipient_type, source_message 
        FROM todos 
        WHERE source_message LIKE '%WellLink%' OR source_message LIKE '%welllink%' OR source_message LIKE '%WELLLINK%'
        LIMIT 10
    ''')
    
    source_todos = cur.fetchall()
    if source_todos:
        print(f"\n   소스 메시지에 WellLink가 포함된 TODO: {len(source_todos)}개")
        for todo in source_todos:
            print(f"   - ID: {todo[0]}")
            print(f"     제목: {todo[1][:60]}...")
            print(f"     프로젝트 태그: {todo[2]}")
            print(f"     수신 타입: {todo[3]}")
            
            # 소스 메시지 분석
            source_message = todo[4]
            if source_message:
                try:
                    if source_message.startswith('{'):
                        msg_data = json.loads(source_message)
                        print(f"     소스 메시지 제목: {msg_data.get('subject', 'N/A')[:50]}...")
                        
                        # 프로젝트 추출 테스트
                        extracted_project = service.extract_project_from_message(msg_data)
                        print(f"     추출된 프로젝트: {extracted_project}")
                    else:
                        print(f"     소스 메시지: {source_message[:50]}...")
                        
                        # 간단한 메시지로 프로젝트 추출 테스트
                        test_msg = {'content': source_message, 'subject': todo[1]}
                        extracted_project = service.extract_project_from_message(test_msg)
                        print(f"     추출된 프로젝트: {extracted_project}")
                        
                except Exception as e:
                    print(f"     소스 메시지 파싱 오류: {e}")
    else:
        print("   소스 메시지에 WellLink가 포함된 TODO 없음")
    
    # 4. WELL 프로젝트 태그가 설정된 TODO 확인
    print("\n4. WELL 프로젝트 태그가 설정된 TODO 확인...")
    cur.execute('''
        SELECT id, title, description, recipient_type, source_message 
        FROM todos 
        WHERE project_tag = 'WELL'
        LIMIT 10
    ''')
    
    well_todos = cur.fetchall()
    if well_todos:
        print(f"   WELL 프로젝트 태그가 설정된 TODO: {len(well_todos)}개")
        for todo in well_todos:
            print(f"   - ID: {todo[0]}")
            print(f"     제목: {todo[1][:60]}...")
            print(f"     수신 타입: {todo[3]}")
    else:
        print("   WELL 프로젝트 태그가 설정된 TODO 없음")
    
    # 5. CC 수신 타입 TODO 확인
    print("\n5. CC 수신 타입 TODO 확인...")
    cur.execute('''
        SELECT id, title, project_tag, source_message 
        FROM todos 
        WHERE recipient_type = 'cc'
        LIMIT 10
    ''')
    
    cc_todos = cur.fetchall()
    if cc_todos:
        print(f"   CC 수신 타입 TODO: {len(cc_todos)}개")
        for todo in cc_todos:
            print(f"   - ID: {todo[0]}")
            print(f"     제목: {todo[1][:60]}...")
            print(f"     프로젝트 태그: {todo[2]}")
    else:
        print("   CC 수신 타입 TODO 없음")
    
    conn.close()
    
    print("\n=== 디버깅 완료 ===")

if __name__ == "__main__":
    main()