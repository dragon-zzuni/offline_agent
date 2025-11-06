# -*- coding: utf-8 -*-
"""
임보연 페르소나의 Top-3 TODO 확인 스크립트
"""
import sqlite3
import json
from pathlib import Path

# TODO DB 경로
todo_db_path = Path("virtualoffice/src/virtualoffice/todos_cache.db")

if not todo_db_path.exists():
    print(f"❌ TODO DB를 찾을 수 없습니다: {todo_db_path}")
    exit(1)

print(f"📂 DB 경로: {todo_db_path}")
print("=" * 80)

conn = sqlite3.connect(str(todo_db_path))
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# 1. 임보연 페르소나 정보 확인
print("\n👤 임보연 페르소나 정보:")
print("  - 이름: 임보연")
print("  - 이메일: imboyeon@koreatcompany.com")
print("  - 채팅 핸들: imboyeon_joreait")

# 2. 임보연 관련 TODO 조회 (이메일, 이름, 핸들로 검색)
print("\n📋 임보연 관련 TODO 조회:")
cur.execute("""
    SELECT id, title, persona_name, requester, is_top3, priority
    FROM todos
    WHERE status != 'done'
    AND (
        persona_name = '임보연'
        OR persona_name = 'imboyeon@koreatcompany.com'
        OR persona_name = 'imboyeon_joreait'
    )
    ORDER BY is_top3 DESC, priority DESC
""")

boyeon_todos = cur.fetchall()
print(f"  총 {len(boyeon_todos)}개 TODO 발견")

# 3. Top-3 TODO 상세 정보
print("\n⭐ Top-3 TODO:")
top3_count = 0
for row in boyeon_todos:
    if row['is_top3'] == 1:
        top3_count += 1
        print(f"\n  [{top3_count}] {row['title']}")
        print(f"      - persona_name: {row['persona_name']}")
        print(f"      - requester: {row['requester']}")
        print(f"      - priority: {row['priority']}")
        print(f"      - is_top3: {row['is_top3']}")

if top3_count == 0:
    print("  (Top-3 TODO 없음)")

# 4. 전체 Top-3 TODO 조회 (다른 페르소나 포함)
print("\n\n🔍 전체 Top-3 TODO 조회:")
cur.execute("""
    SELECT id, title, persona_name, requester, priority
    FROM todos
    WHERE status != 'done' AND is_top3 = 1
    ORDER BY priority DESC
""")

all_top3 = cur.fetchall()
print(f"  총 {len(all_top3)}개 Top-3 TODO")

for idx, row in enumerate(all_top3, 1):
    print(f"\n  [{idx}] {row['title']}")
    print(f"      - persona_name: {row['persona_name']}")
    print(f"      - requester: {row['requester']}")
    print(f"      - priority: {row['priority']}")

# 5. 정지원 관련 TODO 확인
print("\n\n🔍 정지원 관련 TODO 확인:")
cur.execute("""
    SELECT id, title, persona_name, requester, is_top3, priority
    FROM todos
    WHERE status != 'done'
    AND (
        persona_name LIKE '%정지원%'
        OR persona_name LIKE '%jungjiwon%'
        OR requester LIKE '%정지원%'
        OR requester LIKE '%jungjiwon%'
    )
    ORDER BY is_top3 DESC, priority DESC
    LIMIT 5
""")

jiwon_todos = cur.fetchall()
print(f"  총 {len(jiwon_todos)}개 TODO 발견")

for idx, row in enumerate(jiwon_todos, 1):
    print(f"\n  [{idx}] {row['title']}")
    print(f"      - persona_name: {row['persona_name']}")
    print(f"      - requester: {row['requester']}")
    print(f"      - is_top3: {row['is_top3']}")
    print(f"      - priority: {row['priority']}")

conn.close()

print("\n" + "=" * 80)
print("✅ 분석 완료")
