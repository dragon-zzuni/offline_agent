# -*- coding: utf-8 -*-
"""
persona_name이 NULL인 TODO들을 수정
requester 이메일을 기반으로 persona_name 설정
"""
import sqlite3

# VDOS DB에서 이메일-이름 매핑 가져오기
vdos_conn = sqlite3.connect('../virtualoffice/src/virtualoffice/vdos.db')
vdos_cur = vdos_conn.cursor()

vdos_cur.execute('SELECT email_address, name FROM people')
email_to_name = dict(vdos_cur.fetchall())
vdos_conn.close()

print(f"✅ {len(email_to_name)}명의 이메일-이름 매핑 로드")

# TODO 캐시 DB 업데이트
cache_conn = sqlite3.connect('../virtualoffice/src/virtualoffice/todos_cache.db')
cache_cur = cache_conn.cursor()

# persona_name이 NULL인 TODO 조회
cache_cur.execute('''
    SELECT id, requester
    FROM todos
    WHERE persona_name IS NULL
''')
null_todos = cache_cur.fetchall()

print(f"\n📋 persona_name이 NULL인 TODO: {len(null_todos)}개")

updated_count = 0
not_found_count = 0

for todo_id, requester in null_todos:
    if requester in email_to_name:
        persona_name = email_to_name[requester]
        cache_cur.execute('''
            UPDATE todos
            SET persona_name = ?
            WHERE id = ?
        ''', (persona_name, todo_id))
        updated_count += 1
    else:
        not_found_count += 1
        print(f"  ⚠️ 매핑 없음: {requester}")

cache_conn.commit()

print(f"\n✅ 업데이트 완료:")
print(f"  - 성공: {updated_count}개")
print(f"  - 실패: {not_found_count}개")

# 결과 확인
print(f"\n📊 업데이트 후 persona별 TODO 개수:")
cache_cur.execute('''
    SELECT persona_name, COUNT(*) as count
    FROM todos
    GROUP BY persona_name
    ORDER BY count DESC
    LIMIT 15
''')
for name, count in cache_cur.fetchall():
    print(f"  {name}: {count}개")

cache_conn.close()

print("\n✅ 완료!")
