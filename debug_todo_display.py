#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""TODO 표시 문제 디버깅"""
import sys
import sqlite3
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

print("=" * 80)
print("🔍 TODO 표시 문제 디버깅")
print("=" * 80)

# 1. DB 파일 확인
db_path = project_root / "data" / "multi_project_8week_ko" / "todos_cache.db"
print(f"\n📁 DB 파일: {db_path}")
print(f"   존재 여부: {'✅ 있음' if db_path.exists() else '❌ 없음'}")

if not db_path.exists():
    print("\n❌ DB 파일이 없습니다. 앱을 실행하고 분석을 먼저 수행하세요.")
    sys.exit(1)

# 2. DB 연결 및 TODO 개수 확인
try:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # 테이블 존재 확인
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='todos'")
    if not cur.fetchone():
        print("\n❌ 'todos' 테이블이 없습니다.")
        conn.close()
        sys.exit(1)
    
    # TODO 개수 확인
    cur.execute("SELECT COUNT(*) as count FROM todos WHERE status != 'done'")
    active_count = cur.fetchone()['count']
    
    cur.execute("SELECT COUNT(*) as count FROM todos")
    total_count = cur.fetchone()['count']
    
    print(f"\n📊 TODO 통계:")
    print(f"   전체 TODO: {total_count}개")
    print(f"   활성 TODO (완료 제외): {active_count}개")
    
    if active_count == 0:
        print("\n⚠️ 활성 TODO가 없습니다. 완료된 TODO만 있거나 분석이 필요합니다.")
    
    # 최근 TODO 5개 확인
    print(f"\n📋 최근 TODO 5개:")
    cur.execute("""
        SELECT id, title, priority, status, created_at, persona
        FROM todos
        ORDER BY created_at DESC
        LIMIT 5
    """)
    
    todos = cur.fetchall()
    if todos:
        for i, todo in enumerate(todos, 1):
            status_icon = "✅" if todo['status'] == 'done' else "📌"
            priority = todo['priority'] or 'N/A'
            persona = todo['persona'] or 'N/A'
            print(f"   {i}. {status_icon} [{priority}] {todo['title'][:50]}")
            print(f"      페르소나: {persona}, 생성: {todo['created_at']}")
    else:
        print("   TODO가 없습니다.")
    
    conn.close()
    
    print("\n✅ DB 확인 완료")
    
except Exception as e:
    print(f"\n❌ DB 확인 중 오류: {e}")
    import traceback
    traceback.print_exc()

# 3. TodoRepository 테스트
print("\n" + "=" * 80)
print("🧪 TodoRepository 테스트")
print("=" * 80)

try:
    from ui.todo.repository import TodoRepository
    
    repo = TodoRepository(str(db_path))
    
    # get_all() 테스트
    all_todos = repo.get_all()
    print(f"\n📦 repository.get_all() 결과: {len(all_todos)}개")
    
    if all_todos:
        print(f"\n   첫 번째 TODO:")
        first = all_todos[0]
        print(f"   - ID: {first.get('id')}")
        print(f"   - 제목: {first.get('title', 'N/A')[:50]}")
        print(f"   - 우선순위: {first.get('priority', 'N/A')}")
        print(f"   - 상태: {first.get('status', 'N/A')}")
    
    print("\n✅ TodoRepository 정상 작동")
    
except Exception as e:
    print(f"\n❌ TodoRepository 테스트 실패: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("진단 완료")
print("=" * 80)
