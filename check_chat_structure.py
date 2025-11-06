# -*- coding: utf-8 -*-
"""
채팅 구조 분석 - 프로젝트 매칭 가능성 확인
"""
import sqlite3

conn = sqlite3.connect('../virtualoffice/src/virtualoffice/vdos.db')
cur = conn.cursor()

print('=' * 80)
print('채팅 구조 분석')
print('=' * 80)

# chat_members 샘플
print('\n📊 chat_members (샘플 10개):')
cur.execute('''
    SELECT cm.room_id, cr.name, cm.handle
    FROM chat_members cm
    JOIN chat_rooms cr ON cm.room_id = cr.id
    LIMIT 10
''')
for room_id, room_name, handle in cur.fetchall():
    print(f'  방 {room_id} ({room_name}): {handle}')

# 프로젝트 관련 채팅방 검색
print('\n🔍 프로젝트 관련 채팅방:')
cur.execute('''
    SELECT id, name, is_dm
    FROM chat_rooms 
    WHERE name LIKE '%Project%' OR name LIKE '%LUMINA%' OR name LIKE '%VERTEX%'
       OR name LIKE '%NOVA%' OR name LIKE '%SYNAPSE%' OR name LIKE '%OMEGA%'
''')
project_rooms = cur.fetchall()
if project_rooms:
    for room_id, name, is_dm in project_rooms:
        print(f'  {room_id}: {name} (DM: {is_dm})')
        
        # 채팅방 멤버 확인
        cur.execute('SELECT handle FROM chat_members WHERE room_id = ?', (room_id,))
        members = [row[0] for row in cur.fetchall()]
        print(f'      멤버: {", ".join(members)}')
else:
    print('  프로젝트명이 포함된 채팅방 없음')

# DM이 아닌 그룹 채팅방 확인
print('\n👥 그룹 채팅방 (DM 제외):')
cur.execute('''
    SELECT id, name, slug
    FROM chat_rooms 
    WHERE is_dm = 0
    LIMIT 10
''')
group_rooms = cur.fetchall()
if group_rooms:
    for room_id, name, slug in group_rooms:
        print(f'  {room_id}: {name} (slug: {slug})')
        
        # 멤버 확인
        cur.execute('SELECT handle FROM chat_members WHERE room_id = ?', (room_id,))
        members = [row[0] for row in cur.fetchall()]
        print(f'      멤버: {", ".join(members[:5])}{"..." if len(members) > 5 else ""}')
else:
    print('  그룹 채팅방 없음')

# 채팅 메시지에서 프로젝트 언급 확인
print('\n💬 최근 채팅 메시지 중 프로젝트 언급:')
cur.execute('''
    SELECT cm.id, cm.sender, cm.body, cr.name
    FROM chat_messages cm
    JOIN chat_rooms cr ON cm.room_id = cr.id
    WHERE cm.body LIKE '%Project%' OR cm.body LIKE '%LUMINA%' OR cm.body LIKE '%VERTEX%'
       OR cm.body LIKE '%NOVA%' OR cm.body LIKE '%SYNAPSE%' OR cm.body LIKE '%OMEGA%'
    ORDER BY cm.id DESC
    LIMIT 5
''')
for msg_id, sender, body, room_name in cur.fetchall():
    print(f'\n  메시지 {msg_id} (방: {room_name})')
    print(f'    발신자: {sender}')
    print(f'    내용: {body[:100]}...')

conn.close()

print('\n' + '=' * 80)
print('분석 완료')
print('=' * 80)
