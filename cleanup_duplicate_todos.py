# -*- coding: utf-8 -*-
"""기존 DB의 중복 TODO 정리 스크립트"""
import sys
import os

# 경로 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, "src")
sys.path.insert(0, current_dir)
sys.path.insert(0, src_dir)

# 직접 import
import sqlite3
from services.todo_deduplication_service import TodoDeduplicationService

print("=" * 60)
print("중복 TODO 정리 스크립트")
print("=" * 60)

# DB 경로 찾기
vdos_db_path = os.path.join(current_dir, "..", "virtualoffice", "src", "virtualoffice", "todos_cache.db")
if not os.path.exists(vdos_db_path):
    print(f"❌ DB 파일을 찾을 수 없습니다: {vdos_db_path}")
    sys.exit(1)

print(f"DB 경로: {vdos_db_path}")

# DB 연결
conn = sqlite3.connect(vdos_db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# 전체 TODO 조회
cursor.execute("SELECT * FROM todos")
rows = cursor.fetchall()
all_todos = [dict(row) for row in rows]
print(f"\n현재 DB의 TODO: {len(all_todos)}개")

# source_message별로 그룹화
from collections import defaultdict
source_groups = defaultdict(list)

for todo in all_todos:
    source_msg = todo.get("source_message")
    if source_msg:
        source_groups[source_msg].append(todo)

# 중복 그룹 찾기
duplicate_groups = {k: v for k, v in source_groups.items() if len(v) > 1}

if not duplicate_groups:
    print("\n✅ 중복 TODO가 없습니다!")
else:
    print(f"\n⚠️ 중복 그룹 발견: {len(duplicate_groups)}개")
    
    # 중복 제거 서비스 초기화
    dedup_service = TodoDeduplicationService()
    
    removed_count = 0
    kept_count = 0
    
    for source_msg, todos in duplicate_groups.items():
        print(f"\n📌 source_message: {source_msg}")
        print(f"   중복 TODO: {len(todos)}개")
        
        for todo in todos:
            print(f"     - {todo.get('type'):15s} | {todo.get('requester'):15s} | {todo.get('title', '')[:40]}")
        
        # 최선 TODO 선택
        best_todo = dedup_service.select_best_type(todos)
        print(f"   ✅ 선택: {best_todo.get('type')} (ID: {best_todo.get('id')})")
        
        # 나머지 삭제
        for todo in todos:
            if todo["id"] != best_todo["id"]:
                print(f"   🗑️ 삭제: {todo.get('type')} (ID: {todo.get('id')})")
                cursor.execute("DELETE FROM todos WHERE id = ?", (todo["id"],))
                removed_count += 1
            else:
                kept_count += 1
    
    # 변경사항 커밋
    conn.commit()
    
    print(f"\n" + "=" * 60)
    print(f"정리 완료:")
    print(f"  - 유지: {kept_count}개")
    print(f"  - 삭제: {removed_count}개")
    print(f"  - 최종: {len(all_todos) - removed_count}개")
    print("=" * 60)

# 정리 후 확인
cursor.execute("SELECT COUNT(*) FROM todos")
final_count = cursor.fetchone()[0]
print(f"\n최종 TODO 개수: {final_count}개")

# 연결 종료
conn.close()
