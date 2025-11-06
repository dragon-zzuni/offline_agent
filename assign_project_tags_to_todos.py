#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
기존 TODO에 프로젝트 태그 일괄 할당
"""
import sys
import sqlite3
import json
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from services.project_tag_service import ProjectTagService

def main():
    print("=" * 80)
    print("기존 TODO에 프로젝트 태그 일괄 할당")
    print("=" * 80)
    
    # ProjectTagService 초기화
    service = ProjectTagService()
    
    if not service.vdos_db_path:
        print("❌ VDOS DB를 찾을 수 없습니다!")
        return
    
    # TODO DB 경로
    vdos_dir = Path(service.vdos_db_path).parent
    todo_db_path = vdos_dir / "todos_cache.db"
    
    if not todo_db_path.exists():
        print(f"❌ TODO DB를 찾을 수 없습니다: {todo_db_path}")
        return
    
    print(f"\n📍 TODO DB: {todo_db_path}")
    print(f"📍 프로젝트 태그 캐시: {service.tag_cache.db_path if service.tag_cache else 'None'}")
    
    # TODO 로드
    conn = sqlite3.connect(str(todo_db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    cur.execute("""
        SELECT id, title, description, requester, source_message, project
        FROM todos
        WHERE project IS NULL OR project = '' OR project = 'Unknown'
    """)
    todos = cur.fetchall()
    
    print(f"\n프로젝트 태그가 없는 TODO: {len(todos)}개")
    
    if len(todos) == 0:
        print("✅ 모든 TODO에 프로젝트 태그가 할당되어 있습니다!")
        conn.close()
        return
    
    # 프로젝트 태그 할당
    updated_count = 0
    failed_count = 0
    tag_distribution = {}
    
    for todo in todos:
        todo_id = todo['id']
        title = todo['title']
        description = todo['description']
        requester = todo['requester']
        
        # source_message 파싱
        try:
            source_msg = json.loads(todo['source_message']) if todo['source_message'] else {}
        except:
            source_msg = {}
        
        # 메시지 객체 구성
        message = {
            'id': todo_id,
            'title': title,
            'content': description,
            'sender': requester,
            **source_msg
        }
        
        # 프로젝트 태그 추출
        try:
            project_tag = service.extract_project_from_message(message, use_cache=False)
            
            if project_tag and project_tag != 'UNKNOWN':
                # TODO 업데이트
                cur.execute(
                    "UPDATE todos SET project = ? WHERE id = ?",
                    (project_tag, todo_id)
                )
                updated_count += 1
                tag_distribution[project_tag] = tag_distribution.get(project_tag, 0) + 1
                print(f"✅ {todo_id[:12]}... → {project_tag}: {title[:50]}")
            else:
                failed_count += 1
                print(f"⚠️ {todo_id[:12]}... → 태그 없음: {title[:50]}")
        
        except Exception as e:
            failed_count += 1
            print(f"❌ {todo_id[:12]}... → 오류: {e}")
    
    # 변경사항 커밋
    conn.commit()
    conn.close()
    
    # 결과 요약
    print(f"\n{'='*80}")
    print("결과 요약")
    print("=" * 80)
    print(f"✅ 성공: {updated_count}개")
    print(f"⚠️ 실패: {failed_count}개")
    
    if tag_distribution:
        print(f"\n프로젝트 태그 분포:")
        for tag, count in sorted(tag_distribution.items(), key=lambda x: x[1], reverse=True):
            project_name = service.project_tags.get(tag, None)
            if project_name:
                print(f"  {tag} ({project_name.name}): {count}개")
            else:
                print(f"  {tag}: {count}개")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()
