#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
전체 프로젝트 분류 재검토 및 수정 스크립트

LLM 기반 동적 분류 시스템을 사용하여 모든 TODO의 프로젝트 분류를 재검토합니다.
"""
import sys
import os
sys.path.append('.')
sys.path.append('src')

import sqlite3
import json
from src.services.project_tag_service import ProjectTagService

def main():
    print("=== 전체 프로젝트 분류 재검토 및 수정 ===\n")
    
    # 프로젝트 태그 서비스 초기화
    service = ProjectTagService()
    
    # VDOS 데이터베이스 연결
    db_path = '../virtualoffice/src/virtualoffice/todos_cache.db'
    if not os.path.exists(db_path):
        print(f"❌ 데이터베이스 파일을 찾을 수 없음: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # 현재 프로젝트 분포 확인
    cur.execute('SELECT project, COUNT(*) FROM todos GROUP BY project ORDER BY COUNT(*) DESC')
    current_distribution = cur.fetchall()
    print("=== 현재 프로젝트 분포 ===")
    for project, count in current_distribution:
        print(f"- {project}: {count}개")
    
    # 모든 TODO 가져오기 (소스 메시지가 있는 것만)
    cur.execute('''
        SELECT id, title, description, project, source_message
        FROM todos 
        WHERE source_message IS NOT NULL AND source_message != ''
        ORDER BY created_at DESC
        LIMIT 50
    ''')
    
    todos = cur.fetchall()
    print(f"\n=== {len(todos)}개 TODO 재분류 시작 ===")
    
    updated_count = 0
    llm_corrections = 0
    
    for i, todo in enumerate(todos, 1):
        todo_id, title, description, current_project, source_message = todo
        
        if i % 10 == 0:
            print(f"진행률: {i}/{len(todos)} ({i/len(todos)*100:.1f}%)")
        
        try:
            msg_data = json.loads(source_message)
            
            # 새로운 LLM 기반 분류
            new_project = service.extract_project_from_message(msg_data)
            
            if new_project and new_project != current_project:
                print(f"\n수정 필요: {todo_id}")
                print(f"  제목: {title[:50]}...")
                print(f"  현재: {current_project} → 새로운: {new_project}")
                
                # 소스 메시지 제목 확인
                subject = msg_data.get('subject', '')
                if subject:
                    print(f"  소스: {subject[:60]}...")
                
                # 데이터베이스 업데이트
                cur.execute('''
                    UPDATE todos 
                    SET project = ?, updated_at = datetime('now')
                    WHERE id = ?
                ''', (new_project, todo_id))
                
                updated_count += 1
                
                # LLM이 기존 분류를 수정한 경우 카운트
                if current_project != new_project:
                    llm_corrections += 1
                
        except Exception as e:
            print(f"  ❌ TODO {todo_id} 처리 오류: {e}")
    
    # 변경사항 저장
    conn.commit()
    
    # 수정 후 분포 확인
    cur.execute('SELECT project, COUNT(*) FROM todos GROUP BY project ORDER BY COUNT(*) DESC')
    new_distribution = cur.fetchall()
    
    conn.close()
    
    print(f"\n=== 수정 완료 ===")
    print(f"총 {updated_count}개 TODO 프로젝트 분류 수정")
    print(f"LLM 기반 수정: {llm_corrections}개")
    
    print("\n=== 수정 후 프로젝트 분포 ===")
    for project, count in new_distribution:
        print(f"- {project}: {count}개")
    
    # 변화량 계산
    print("\n=== 변화량 ===")
    current_dict = dict(current_distribution)
    new_dict = dict(new_distribution)
    
    all_projects = set(current_dict.keys()) | set(new_dict.keys())
    for project in sorted(all_projects):
        old_count = current_dict.get(project, 0)
        new_count = new_dict.get(project, 0)
        change = new_count - old_count
        if change != 0:
            print(f"- {project}: {old_count} → {new_count} ({change:+d})")

if __name__ == "__main__":
    main()