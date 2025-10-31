#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WellLink 프로젝트 분류 수정 스크립트

CC로 잘못 분류된 WellLink 관련 TODO들을 WELL 프로젝트로 재분류합니다.
"""
import sys
import os
sys.path.append('.')
sys.path.append('src')

import sqlite3
import json
from src.services.project_tag_service import ProjectTagService

def main():
    print("=== WellLink 프로젝트 분류 수정 ===\n")
    
    # 프로젝트 태그 서비스 초기화
    service = ProjectTagService()
    
    # VDOS 데이터베이스 연결
    db_path = '../virtualoffice/src/virtualoffice/todos_cache.db'
    if not os.path.exists(db_path):
        print(f"❌ 데이터베이스 파일을 찾을 수 없음: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # WellLink 관련이지만 잘못 분류된 TODO 찾기
    cur.execute('''
        SELECT id, title, description, project, source_message
        FROM todos 
        WHERE (title LIKE '%WellLink%' OR description LIKE '%WellLink%' OR source_message LIKE '%WellLink%')
        AND project != 'WELL'
    ''')
    
    misclassified_todos = cur.fetchall()
    print(f"잘못 분류된 WellLink TODO: {len(misclassified_todos)}개")
    
    updated_count = 0
    
    for todo in misclassified_todos:
        todo_id, title, description, current_project, source_message = todo
        
        print(f"\n처리 중: {todo_id}")
        print(f"  제목: {title}")
        print(f"  현재 프로젝트: {current_project}")
        
        # 소스 메시지에서 프로젝트 재추출
        if source_message:
            try:
                msg_data = json.loads(source_message)
                
                # 프로젝트 추출
                extracted_project = service.extract_project_from_message(msg_data)
                
                if extracted_project and extracted_project != current_project:
                    print(f"  → 새 프로젝트: {extracted_project}")
                    
                    # 데이터베이스 업데이트
                    cur.execute('''
                        UPDATE todos 
                        SET project = ?, updated_at = datetime('now')
                        WHERE id = ?
                    ''', (extracted_project, todo_id))
                    
                    updated_count += 1
                    print(f"  ✅ 업데이트 완료")
                else:
                    print(f"  ⚠️ 프로젝트 추출 실패 또는 동일: {extracted_project}")
                    
            except Exception as e:
                print(f"  ❌ 소스 메시지 처리 오류: {e}")
        else:
            print("  ⚠️ 소스 메시지 없음")
    
    # 변경사항 저장
    conn.commit()
    conn.close()
    
    print(f"\n=== 수정 완료 ===")
    print(f"총 {updated_count}개 TODO 프로젝트 분류 수정")

if __name__ == "__main__":
    main()