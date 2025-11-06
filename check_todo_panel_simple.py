#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""TODO 패널 간단 체크"""
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

print("=" * 80)
print("🔍 TODO 패널 체크")
print("=" * 80)

# DB 경로
db_path = project_root / "data" / "multi_project_8week_ko" / "todos_cache.db"

if not db_path.exists():
    print(f"\n❌ DB 파일이 없습니다: {db_path}")
    print("   앱을 실행하고 분석을 먼저 수행하세요.")
    sys.exit(1)

# 직접 DB 확인
import sqlite3
conn = sqlite3.connect(str(db_path))
cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM todos")
count = cur.fetchone()[0]

print(f"\n📊 DB의 TODO 개수: {count}개")

if count == 0:
    print("\n⚠️ TODO가 없습니다!")
    print("   해결 방법:")
    print("   1. 앱을 실행하세요")
    print("   2. '실시간 연결 및 메시지 수집' 버튼을 클릭하세요")
    print("   3. VirtualOffice에 연결되고 메시지를 수집하면 TODO가 생성됩니다")
else:
    print(f"\n✅ TODO가 {count}개 있습니다")
    print("\n   최근 TODO 3개:")
    cur.execute("""
        SELECT id, title, priority, status 
        FROM todos 
        ORDER BY created_at DESC 
        LIMIT 3
    """)
    for row in cur.fetchall():
        print(f"   - [{row[2]}] {row[1][:60]}")

conn.close()
