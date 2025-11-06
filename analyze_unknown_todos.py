# -*- coding: utf-8 -*-
"""
UNKNOWN 프로젝트 태그를 가진 TODO 분석
실제 메시지 내용 확인
"""
import sqlite3
import json

print("=" * 80)
print("UNKNOWN 프로젝트 태그 TODO 분석")
print("=" * 80)

# TODO 캐시 DB 연결
cache_conn = sqlite3.connect('../virtualoffice/src/virtualoffice/todos_cache.db')
cache_cur = cache_conn.cursor()

# UNKNOWN 태그를 가진 TODO 조회
cache_cur.execute('''
    SELECT id, title, description, requester, persona_name, 
           source_message, project_tag, evidence
    FROM todos
    WHERE project_tag = 'UNKNOWN' OR project_tag IS NULL
    LIMIT 20
''')

unknown_todos = cache_cur.fetchall()

print(f"\n📋 UNKNOWN 태그 TODO: {len(unknown_todos)}개 (최대 20개 표시)\n")

for i, (todo_id, title, desc, requester, persona, source_msg, proj_tag, evidence) in enumerate(unknown_todos, 1):
    print(f"\n{'='*80}")
    print(f"[{i}] TODO ID: {todo_id}")
    print(f"{'='*80}")
    print(f"제목: {title}")
    print(f"설명: {desc[:200] if desc else '없음'}...")
    print(f"요청자: {requester}")
    print(f"Persona: {persona}")
    print(f"프로젝트 태그: {proj_tag}")
    
    # source_message 파싱
    if source_msg:
        try:
            msg_data = json.loads(source_msg)
            print(f"\n📧 원본 메시지:")
            print(f"  발신자: {msg_data.get('sender', 'N/A')}")
            print(f"  제목: {msg_data.get('subject', 'N/A')}")
            
            content = msg_data.get('content', '') or msg_data.get('body', '')
            if content:
                print(f"  내용 (처음 300자):")
                print(f"    {content[:300]}...")
            else:
                print(f"  내용: 없음")
                
        except:
            print(f"  원본 메시지 파싱 실패")
    
    # evidence 확인
    if evidence:
        print(f"\n🔍 Evidence (처음 200자):")
        print(f"  {evidence[:200]}...")

cache_conn.close()

print(f"\n{'='*80}")
print("분석 완료")
print("="*80)
