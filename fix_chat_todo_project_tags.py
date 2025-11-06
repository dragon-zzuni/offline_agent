# -*- coding: utf-8 -*-
"""
채팅에서 생성된 TODO의 프로젝트 태그 수정
source_message가 비어있는 TODO들을 VDOS DB 채팅 내용으로 복구하여 재분류
"""
import sys
import os
from pathlib import Path
import sqlite3
import json

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from services.project_tag_service import ProjectTagService

print("=" * 80)
print("채팅 TODO 프로젝트 태그 수정")
print("=" * 80)

# TODO 캐시 DB 연결
cache_conn = sqlite3.connect('../virtualoffice/src/virtualoffice/todos_cache.db')
cache_cur = cache_conn.cursor()

# VDOS DB 연결
vdos_conn = sqlite3.connect('../virtualoffice/src/virtualoffice/vdos.db')
vdos_cur = vdos_conn.cursor()

# project_tag가 None인 TODO 조회
cache_cur.execute('''
    SELECT id, title, persona_name, source_message, created_at
    FROM todos
    WHERE project_tag IS NULL
    ORDER BY created_at DESC
''')

none_todos = cache_cur.fetchall()

print(f"\n📋 project_tag가 None인 TODO: {len(none_todos)}개\n")

# ProjectTagService 초기화
tag_service = ProjectTagService()

fixed_count = 0
still_none_count = 0

for todo_id, title, persona, source_msg, created_at in none_todos:
    print(f"\n처리 중: {todo_id} ({title})")
    
    # source_message 파싱
    try:
        msg_data = json.loads(source_msg) if source_msg else {}
    except:
        msg_data = {}
    
    sender = msg_data.get('sender', '')
    
    # 채팅 핸들인지 확인 (이메일 형식이 아님)
    if not sender or '@' in sender:
        print(f"  ⏭️ 이메일 메시지 또는 발신자 없음")
        still_none_count += 1
        continue
    
    # VDOS DB에서 해당 발신자의 최근 채팅 메시지 검색
    vdos_cur.execute('''
        SELECT cm.id, cm.body, cm.sent_at, cr.name
        FROM chat_messages cm
        JOIN chat_rooms cr ON cm.room_id = cr.id
        WHERE cm.sender = ?
        ORDER BY cm.id DESC
        LIMIT 5
    ''', (sender,))
    
    recent_chats = vdos_cur.fetchall()
    
    if not recent_chats:
        print(f"  ⚠️ 채팅 메시지 없음")
        still_none_count += 1
        continue
    
    # 가장 최근 메시지로 복구
    chat_id, chat_body, chat_time, room_name = recent_chats[0]
    
    print(f"  📧 채팅 복구: {chat_body[:60]}...")
    
    # 복구된 메시지로 프로젝트 분류
    recovered_message = {
        'id': todo_id,
        'sender': sender,
        'sender_email': sender,
        'subject': f"채팅: {room_name}",
        'content': chat_body,
        'body': chat_body,
        'timestamp': chat_time
    }
    
    # 프로젝트 분류
    project_code = tag_service.extract_project_from_message(recovered_message, use_cache=False)
    
    if project_code and project_code != 'UNKNOWN':
        # TODO 업데이트
        cache_cur.execute('''
            UPDATE todos
            SET project_tag = ?
            WHERE id = ?
        ''', (project_code, todo_id))
        
        fixed_count += 1
        print(f"  ✅ 프로젝트 태그 설정: {project_code}")
    else:
        still_none_count += 1
        print(f"  ❌ 프로젝트 특정 실패")

cache_conn.commit()
cache_conn.close()
vdos_conn.close()

print(f"\n{'='*80}")
print(f"수정 완료:")
print(f"  - 성공: {fixed_count}개")
print(f"  - 실패: {still_none_count}개")
print(f"  - 성공률: {fixed_count / len(none_todos) * 100:.1f}%")
print("="*80)
