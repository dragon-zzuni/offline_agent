"""
페르소나별 TODO 필터링 확인 스크립트
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.ui.todo.repository import TodoRepository

def main():
    repo = TodoRepository()
    
    print("=" * 80)
    print("📋 전체 TODO 목록 (페르소나별)")
    print("=" * 80)
    
    all_todos = repo.fetch_active(persona_name=None)
    print(f"\n전체 TODO 개수: {len(all_todos)}")
    
    # 페르소나별로 그룹화
    by_persona = {}
    for todo in all_todos:
        persona = todo.get('persona_name', 'UNKNOWN')
        if persona not in by_persona:
            by_persona[persona] = []
        by_persona[persona].append(todo)
    
    print(f"\n페르소나 종류: {list(by_persona.keys())}")
    
    for persona, todos in by_persona.items():
        print(f"\n{'='*80}")
        print(f"👤 페르소나: {persona} ({len(todos)}개)")
        print(f"{'='*80}")
        
        for i, todo in enumerate(todos[:5], 1):  # 각 페르소나당 최대 5개만
            print(f"\n{i}. {todo.get('title', 'NO TITLE')}")
            print(f"   - ID: {todo.get('id')}")
            print(f"   - 요청자: {todo.get('requester', 'N/A')}")
            print(f"   - 프로젝트: {todo.get('project_tag', 'N/A')}")
            print(f"   - 우선순위: {todo.get('priority', 'N/A')}")
        
        if len(todos) > 5:
            print(f"\n   ... 외 {len(todos) - 5}개 더")
    
    # 특정 페르소나로 필터링 테스트
    print(f"\n{'='*80}")
    print("🔍 페르소나별 필터링 테스트")
    print(f"{'='*80}")
    
    test_personas = ['이정두', '김연중', '박보연', '이하은', '최지민']
    
    for persona in test_personas:
        filtered = repo.fetch_active(persona_name=persona)
        print(f"\n{persona}: {len(filtered)}개")
        if filtered:
            print(f"  예시: {filtered[0].get('title', 'NO TITLE')[:50]}...")

if __name__ == "__main__":
    main()
