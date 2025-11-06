# -*- coding: utf-8 -*-
"""
project_tag가 None인 TODO 재분류
채팅 메시지 처리 포함
"""
import sys
import os
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

import logging
import sqlite3
import json

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)

from services.project_tag_service import ProjectTagService

print("=" * 80)
print("project_tag가 None인 TODO 재분류 (채팅 메시지 처리 포함)")
print("=" * 80)

# ProjectTagService 초기화
tag_service = ProjectTagService()

print(f"\n✅ 로드된 프로젝트: {len(tag_service.project_tags)}개")
print(f"✅ 프로젝트 기간 정보: {len(tag_service.project_periods)}개")

# TODO 캐시 DB 연결
cache_conn = sqlite3.connect('../virtualoffice/src/virtualoffice/todos_cache.db')
cache_cur = cache_conn.cursor()

# project_tag가 None인 TODO 조회
cache_cur.execute('''
    SELECT id, title, description, persona_name, source_message, created_at
    FROM todos
    WHERE project_tag IS NULL
    ORDER BY updated_at DESC
''')

none_todos = cache_cur.fetchall()

print(f"\n📊 통계:")
print(f"  - project_tag가 None인 TODO: {len(none_todos)}개")

if not none_todos:
    print("\n✅ project_tag가 None인 TODO가 없습니다!")
    cache_conn.close()
    sys.exit(0)

print(f"\n🔄 재분류 시작...")
print("-" * 80)

reclassified_count = 0
still_none_count = 0
classification_methods = {}

for i, (todo_id, title, desc, persona, source_msg, created_at) in enumerate(none_todos, 1):
    print(f"\n[{i}/{len(none_todos)}] TODO ID: {todo_id}")
    print(f"  제목: {title}")
    print(f"  Persona: {persona}")
    
    # source_message 파싱
    sender = None
    subject = None
    content = None
    
    if source_msg:
        try:
            msg_data = json.loads(source_msg)
            sender = msg_data.get('sender', '')
            subject = msg_data.get('subject', '')
            content = msg_data.get('content', '') or msg_data.get('body', '')
            
            print(f"  발신자: {sender}")
            if subject:
                print(f"  제목: {subject[:50]}...")
            if content:
                print(f"  내용: {content[:80]}...")
            else:
                print(f"  내용: 비어있음 (채팅 메시지로 추정)")
        except:
            pass
    
    # 메시지 형식으로 변환
    message = {
        'id': todo_id,
        'content': content or desc or '',
        'subject': subject or '',
        'sender': sender or '',
        'sender_email': sender or '',
        'timestamp': created_at,
    }
    
    # 프로젝트 재분류 (캐시 무시하여 강제 재분석)
    new_project = tag_service.extract_project_from_message(message, use_cache=False)
    
    if new_project and new_project != 'UNKNOWN':
        # 캐시에서 분류 근거 가져오기
        if hasattr(tag_service, 'tag_cache') and tag_service.tag_cache:
            cached = tag_service.tag_cache.get_cached_tag(todo_id)
            reason = cached.get('classification_reason', '알 수 없음') if cached else '알 수 없음'
            method = cached.get('confidence', 'unknown') if cached else 'unknown'
        else:
            reason = '알 수 없음'
            method = 'unknown'
        
        # TODO 업데이트
        cache_cur.execute('''
            UPDATE todos
            SET project_tag = ?
            WHERE id = ?
        ''', (new_project, todo_id))
        
        reclassified_count += 1
        classification_methods[method] = classification_methods.get(method, 0) + 1
        
        print(f"  ✅ 재분류 성공: None → {new_project}")
        print(f"     분류 근거: {reason}")
        print(f"     분류 방법: {method}")
    else:
        still_none_count += 1
        print(f"  ⚠️ 재분류 실패: 여전히 None")

cache_conn.commit()
cache_conn.close()

print("\n" + "=" * 80)
print("재분류 완료")
print("=" * 80)
print(f"\n📊 결과:")
print(f"  - 성공: {reclassified_count}개")
print(f"  - 실패: {still_none_count}개")
if len(none_todos) > 0:
    print(f"  - 성공률: {reclassified_count / len(none_todos) * 100:.1f}%")

if classification_methods:
    print(f"\n📈 분류 방법별 통계:")
    for method, count in sorted(classification_methods.items(), key=lambda x: x[1], reverse=True):
        print(f"  - {method}: {count}개")

print("=" * 80)
