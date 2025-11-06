# -*- coding: utf-8 -*-
"""
project_tag가 None인 TODO 상세 분석
"""
import sqlite3
import json

conn = sqlite3.connect('../virtualoffice/src/virtualoffice/todos_cache.db')
cur = conn.cursor()

# project_tag가 None인 TODO 중 최근 것들
cur.execute('''
    SELECT id, title, persona_name, source_message
    FROM todos
    WHERE project_tag IS NULL
    ORDER BY updated_at DESC
    LIMIT 10
''')

print('=' * 80)
print('project_tag가 None인 TODO 상세 분석')
print('=' * 80)

todos = cur.fetchall()
print(f'\n총 {len(todos)}개 TODO 분석\n')

for i, (todo_id, title, persona, source_msg) in enumerate(todos, 1):
    print(f'[{i}] TODO: {todo_id}')
    print(f'    제목: {title}')
    print(f'    Persona: {persona}')
    
    if source_msg:
        try:
            msg = json.loads(source_msg)
            print(f'\n    📧 원본 메시지:')
            print(f'       발신자: {msg.get("sender", "N/A")}')
            print(f'       제목: {msg.get("subject", "N/A")}')
            
            content = msg.get('content', '') or msg.get('body', '')
            if content:
                print(f'       내용:')
                print(f'       {content[:500]}')
                if len(content) > 500:
                    print(f'       ... (총 {len(content)}자)')
            else:
                print(f'       내용: 없음')
        except Exception as e:
            print(f'    메시지 파싱 오류: {e}')
    
    print('\n' + '='*80 + '\n')

conn.close()
