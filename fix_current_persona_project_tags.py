# -*- coding: utf-8 -*-
"""
현재 페르소나의 프로젝트 태그 즉시 수정

김세린 페르소나의 TODO에 프로젝트 태그를 즉시 적용합니다.
"""
import sqlite3
import os
import sys
import json

# 경로 설정
offline_agent_root = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(offline_agent_root, "src"))

from services.project_tag_service import ProjectTagService


def fix_persona_project_tags(persona_name="김세린"):
    """특정 페르소나의 TODO에 프로젝트 태그 적용"""
    
    todos_db_path = "virtualoffice/src/virtualoffice/todos_cache.db"
    cache_db_path = "virtualoffice/src/virtualoffice/project_tags_cache.db"
    
    if not os.path.exists(todos_db_path):
        print(f"❌ todos_cache.db를 찾을 수 없습니다: {todos_db_path}")
        return
    
    print("=" * 80)
    print(f"{persona_name} 페르소나 프로젝트 태그 수정")
    print("=" * 80)
    
    # 프로젝트 서비스 초기화
    project_service = ProjectTagService(cache_db_path=cache_db_path)
    
    # TODO DB 연결
    conn = sqlite3.connect(todos_db_path)
    cursor = conn.cursor()
    
    # 프로젝트 태그가 없는 TODO 조회
    cursor.execute("""
        SELECT id, title, description, source_message, requester
        FROM todos
        WHERE persona_name = ?
        AND (project IS NULL OR project = '')
        ORDER BY created_at DESC
    """, (persona_name,))
    
    todos_without_project = cursor.fetchall()
    print(f"\n📋 프로젝트 태그가 없는 TODO: {len(todos_without_project)}개")
    
    if not todos_without_project:
        print("✅ 모든 TODO에 프로젝트 태그가 있습니다!")
        conn.close()
        return
    
    # 각 TODO에 프로젝트 태그 적용
    updated_count = 0
    failed_count = 0
    
    for i, row in enumerate(todos_without_project, 1):
        todo_id, title, description, source_message, requester = row
        
        print(f"\n[{i}/{len(todos_without_project)}] {title}")
        
        # 메시지 데이터 구성
        message = {
            "content": f"{title}\n\n{description}" if description else title,
            "subject": title,
            "sender": requester or "Unknown"
        }
        
        # 소스 메시지에서 추가 정보 추출
        if source_message:
            try:
                if isinstance(source_message, str) and source_message.startswith("{"):
                    msg_data = json.loads(source_message)
                    message["subject"] = msg_data.get("subject", title)
                    message["sender"] = msg_data.get("sender", requester)
                    message["body"] = msg_data.get("body", description)
            except:
                pass
        
        # 프로젝트 태그 추출
        project = project_service.extract_project_from_message(message, use_cache=True)
        
        if project:
            # DB 업데이트
            cursor.execute("""
                UPDATE todos
                SET project = ?, updated_at = datetime('now')
                WHERE id = ?
            """, (project, todo_id))
            
            print(f"  ✅ 프로젝트 태그 적용: {project}")
            updated_count += 1
        else:
            print(f"  ⚠️ 프로젝트 태그 추출 실패")
            failed_count += 1
    
    # 변경사항 커밋
    conn.commit()
    conn.close()
    
    print("\n" + "=" * 80)
    print(f"✅ 프로젝트 태그 수정 완료")
    print(f"  - 성공: {updated_count}개")
    print(f"  - 실패: {failed_count}개")
    print("=" * 80)


if __name__ == "__main__":
    import sys
    persona_name = sys.argv[1] if len(sys.argv) > 1 else "김세린"
    fix_persona_project_tags(persona_name)
