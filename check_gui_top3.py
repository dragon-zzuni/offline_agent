#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
GUI에서 Top3 표시 확인

실제 GUI를 실행하지 않고 TODO 패널의 로직을 테스트합니다.
"""
import sys
import os
import sqlite3
from pathlib import Path

# 경로 설정
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
sys.path.insert(0, os.path.dirname(__file__))

def check_todo_display_logic():
    """TODO 표시 로직 확인"""
    print("=" * 60)
    print("TODO 표시 로직 확인")
    print("=" * 60)
    
    # 데이터베이스에서 실제 TODO 로드
    db_path = "../data/multi_project_8week_ko/todos_cache.db"
    if not os.path.exists(db_path):
        print("❌ 데이터베이스 파일을 찾을 수 없습니다")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 모든 TODO 조회
        cursor.execute("SELECT * FROM todos ORDER BY is_top3 DESC, priority DESC")
        todos = [dict(row) for row in cursor.fetchall()]
        
        print(f"✅ 데이터베이스에서 {len(todos)}개 TODO 로드")
        
        # Top3 TODO 확인
        top3_todos = [t for t in todos if t.get('is_top3') == 1]
        print(f"✅ Top3 TODO: {len(top3_todos)}개")
        
        for i, todo in enumerate(top3_todos, 1):
            print(f"  {i}. {todo['title']} (우선순위: {todo['priority']}, 상태: {todo['status']})")
        
        # TODO 패널의 _is_truthy 함수 테스트
        def _is_truthy(v):
            return v in (1, "1", True, "true", "TRUE", "True")
        
        print(f"\n_is_truthy 테스트:")
        for todo in top3_todos:
            is_top3_value = todo.get('is_top3')
            is_truthy_result = _is_truthy(is_top3_value)
            print(f"  - {todo['title']}: is_top3={is_top3_value} → _is_truthy={is_truthy_result}")
        
        conn.close()
        
        # TODO 패널 시뮬레이션
        print(f"\n📋 TODO 패널 시뮬레이션:")
        print(f"Top3 섹션에 표시될 TODO:")
        
        displayed_top3 = []
        for todo in todos:
            if _is_truthy(todo.get("is_top3")) and todo.get("status") != "done":
                displayed_top3.append(todo)
        
        if displayed_top3:
            print(f"✅ {len(displayed_top3)}개 TODO가 Top3 섹션에 표시됩니다:")
            for todo in displayed_top3:
                print(f"  - {todo['title']} (우선순위: {todo['priority']})")
        else:
            print("❌ Top3 섹션에 표시될 TODO가 없습니다")
            
            # 원인 분석
            print("\n🔍 원인 분석:")
            for todo in todos:
                is_top3 = todo.get('is_top3')
                status = todo.get('status')
                print(f"  - {todo['title']}: is_top3={is_top3}, status={status}")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

def simulate_todo_panel_update():
    """TODO 패널 업데이트 시뮬레이션"""
    print("\n" + "=" * 60)
    print("TODO 패널 업데이트 시뮬레이션")
    print("=" * 60)
    
    try:
        # 실제 TODO 패널 코드 시뮬레이션
        db_path = "../data/multi_project_8week_ko/todos_cache.db"
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # TodoPanel.refresh_todo_list() 로직 시뮬레이션
        cursor.execute("SELECT * FROM todos ORDER BY created_at DESC")
        all_todos = [dict(row) for row in cursor.fetchall()]
        
        print(f"전체 TODO: {len(all_todos)}개")
        
        # 필터링 로직
        def _is_truthy(v):
            return v in (1, "1", True, "true", "TRUE", "True")
        
        # Top3 분리
        top3_todos = []
        rest_todos = []
        
        for todo in all_todos:
            if _is_truthy(todo.get("is_top3")):
                top3_todos.append(todo)
            else:
                rest_todos.append(todo)
        
        print(f"Top3 TODO: {len(top3_todos)}개")
        print(f"일반 TODO: {len(rest_todos)}개")
        
        # 상태별 분류
        top3_pending = [t for t in top3_todos if t.get("status") != "done"]
        top3_done = [t for t in top3_todos if t.get("status") == "done"]
        
        print(f"Top3 대기중: {len(top3_pending)}개")
        print(f"Top3 완료: {len(top3_done)}개")
        
        if top3_pending:
            print("\n✅ GUI Top3 섹션에 표시될 TODO:")
            for todo in top3_pending:
                print(f"  - {todo['title']} (상태: {todo['status']})")
        else:
            print("\n❌ GUI Top3 섹션이 비어있을 것입니다")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 시뮬레이션 실패: {e}")

def main():
    """메인 실행"""
    print("GUI Top3 표시 확인")
    
    check_todo_display_logic()
    simulate_todo_panel_update()
    
    print("\n" + "=" * 60)
    print("결론")
    print("=" * 60)
    print("데이터베이스에 Top3 TODO가 있고 로직도 정상이면,")
    print("GUI에서도 Top3가 표시되어야 합니다.")
    print("\n만약 GUI에서 여전히 보이지 않는다면:")
    print("1. GUI 새로고침 (F5 또는 재시작)")
    print("2. TODO 패널의 refresh_todo_list() 호출")
    print("3. 백그라운드 분석 재실행")

if __name__ == "__main__":
    main()