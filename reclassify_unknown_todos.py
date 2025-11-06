# -*- coding: utf-8 -*-
"""
UNKNOWN 프로젝트 태그를 가진 TODO 재분류
고급 분석 기능 포함: 프로젝트 기간, 설명, 발신자 종합 분석
"""
import sys
import os
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)

from services.project_tag_service import ProjectTagService
from ui.todo.repository import TodoRepository

print("=" * 80)
print("UNKNOWN 프로젝트 태그 재분류 (고급 분석 포함)")
print("=" * 80)

# 서비스 초기화
tag_service = ProjectTagService()
todo_repo = TodoRepository()

print(f"\n✅ 로드된 프로젝트: {len(tag_service.project_tags)}개")
print(f"✅ 프로젝트 기간 정보: {len(tag_service.project_periods)}개")

# UNKNOWN 태그를 가진 TODO 조회
todos = todo_repo.get_all_todos()
unknown_todos = [t for t in todos if t.get('project_tag') == 'UNKNOWN']

print(f"\n📊 통계:")
print(f"  - 총 TODO 수: {len(todos)}")
print(f"  - UNKNOWN 태그 TODO 수: {len(unknown_todos)}")

if not unknown_todos:
    print("\n✅ UNKNOWN 태그를 가진 TODO가 없습니다!")
    sys.exit(0)

print(f"\n🔄 재분류 시작...")
print("-" * 80)

reclassified_count = 0
still_unknown_count = 0
classification_methods = {}

for i, todo in enumerate(unknown_todos, 1):
    todo_id = todo.get('id')
    content = todo.get('content', '')
    subject = todo.get('subject', '')
    requester = todo.get('requester', '')
    
    print(f"\n[{i}/{len(unknown_todos)}] TODO ID: {todo_id}")
    print(f"  요청자: {requester}")
    print(f"  제목: {subject[:50]}...")
    print(f"  내용: {content[:80]}...")
    
    # 메시지 형식으로 변환
    message = {
        'id': todo_id,
        'content': content,
        'subject': subject,
        'sender': requester,
        'sender_email': todo.get('requester_email', ''),
        'timestamp': todo.get('created_at', ''),
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
        todo_repo.update_todo(todo_id, {'project_tag': new_project})
        reclassified_count += 1
        
        # 분류 방법 통계
        classification_methods[method] = classification_methods.get(method, 0) + 1
        
        print(f"  ✅ 재분류 성공: UNKNOWN → {new_project}")
        print(f"     분류 근거: {reason}")
        print(f"     분류 방법: {method}")
    else:
        still_unknown_count += 1
        print(f"  ⚠️ 재분류 실패: 여전히 UNKNOWN")

print("\n" + "=" * 80)
print("재분류 완료")
print("=" * 80)
print(f"\n📊 결과:")
print(f"  - 성공: {reclassified_count}개")
print(f"  - 실패: {still_unknown_count}개")
print(f"  - 성공률: {reclassified_count / len(unknown_todos) * 100:.1f}%")

if classification_methods:
    print(f"\n📈 분류 방법별 통계:")
    for method, count in sorted(classification_methods.items(), key=lambda x: x[1], reverse=True):
        print(f"  - {method}: {count}개")

print("=" * 80)
