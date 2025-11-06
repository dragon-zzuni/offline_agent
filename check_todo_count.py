# -*- coding: utf-8 -*-
"""
TODO 개수 확인 스크립트
DB에 저장된 전체 TODO와 페르소나별 TODO 개수를 확인합니다.
"""
import sqlite3
import sys
from pathlib import Path

# TODO DB 경로
vdos_db_path = Path("virtualoffice/src/virtualoffice/todos_cache.db")

if not vdos_db_path.exists():
    print(f"❌ VDOS DB를 찾을 수 없습니다: {vdos_db_path}")
    sys.exit(1)

print(f"📂 DB 경로: {vdos_db_path}")
print("=" * 60)

conn = sqlite3.connect(str(vdos_db_path))
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# 1. 전체 TODO 개수
cur.execute("SELECT COUNT(*) as count FROM todos")
total_count = cur.fetchone()["count"]
print(f"📊 전체 TODO 개수: {total_count}개")

# 2. 상태별 개수
cur.execute("""
    SELECT status, COUNT(*) as count 
    FROM todos 
    GROUP BY status
""")
print("\n📋 상태별 TODO:")
for row in cur.fetchall():
    print(f"  - {row['status']}: {row['count']}개")

# 3. 페르소나별 개수
cur.execute("""
    SELECT persona_name, COUNT(*) as count 
    FROM todos 
    WHERE status != 'done'
    GROUP BY persona_name
    ORDER BY count DESC
""")
print("\n👤 페르소나별 TODO (완료 제외):")
for row in cur.fetchall():
    persona = row['persona_name'] or '(페르소나 없음)'
    print(f"  - {persona}: {row['count']}개")

# 4. 현재 페르소나(leejungdu@example.com)의 TODO
cur.execute("""
    SELECT COUNT(*) as count 
    FROM todos 
    WHERE status != 'done' AND persona_name = 'leejungdu@example.com'
""")
lee_count = cur.fetchone()["count"]
print(f"\n🎯 leejungdu@example.com의 활성 TODO: {lee_count}개")

# 5. Top-3 개수
cur.execute("""
    SELECT COUNT(*) as count 
    FROM todos 
    WHERE status != 'done' AND is_top3 = 1
""")
top3_count = cur.fetchone()["count"]
print(f"⭐ Top-3 TODO: {top3_count}개")

# 6. 프로젝트별 개수
cur.execute("""
    SELECT project_tag, COUNT(*) as count 
    FROM todos 
    WHERE status != 'done' AND project_tag IS NOT NULL AND project_tag != ''
    GROUP BY project_tag
    ORDER BY count DESC
""")
print("\n📁 프로젝트별 TODO (완료 제외):")
for row in cur.fetchall():
    print(f"  - {row['project_tag']}: {row['count']}개")

conn.close()

print("\n" + "=" * 60)
print("✅ 분석 완료")
