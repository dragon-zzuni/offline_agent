"""
기존 TODO에 페르소나 이름 할당
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.ui.todo.repository import TodoRepository
import json

def main():
    print("=" * 80)
    print("🔧 기존 TODO에 페르소나 이름 할당")
    print("=" * 80)
    
    repo = TodoRepository()
    
    # 전체 TODO 조회
    all_todos = repo.fetch_active(persona_name=None)
    print(f"\n📊 전체 TODO: {len(all_todos)}개")
    
    # persona_name이 없는 TODO 찾기
    todos_without_persona = [t for t in all_todos if not t.get('persona_name')]
    print(f"❌ 페르소나 없는 TODO: {len(todos_without_persona)}개")
    
    if not todos_without_persona:
        print("\n✅ 모든 TODO에 페르소나가 할당되어 있습니다!")
        return
    
    # 기본 페르소나 이름 (현재 선택된 페르소나 또는 기본값)
    default_persona = "김연중"  # VirtualOffice의 기본 페르소나
    
    print(f"\n🔄 {len(todos_without_persona)}개 TODO에 '{default_persona}' 할당 중...")
    
    updated = 0
    for todo in todos_without_persona:
        todo_id = todo.get('id')
        if not todo_id:
            continue
        
        # source_message에서 수신자 정보 확인
        source_msg = todo.get('source_message', '{}')
        if isinstance(source_msg, str):
            try:
                source_msg = json.loads(source_msg)
            except:
                source_msg = {}
        
        # 수신자 정보로 페르소나 추정 (이메일 주소 또는 채팅 핸들)
        # 여기서는 간단하게 기본 페르소나 할당
        persona_name = default_persona
        
        # DB 업데이트
        try:
            with repo._transaction() as cur:
                cur.execute(
                    "UPDATE todos SET persona_name = ? WHERE id = ?",
                    (persona_name, todo_id)
                )
            updated += 1
            print(f"  ✓ {todo.get('title', 'NO TITLE')[:50]} → {persona_name}")
        except Exception as e:
            print(f"  ✗ 오류: {e}")
    
    print(f"\n✅ {updated}개 TODO 업데이트 완료!")
    
    # 결과 확인
    print(f"\n{'='*80}")
    print("📊 업데이트 후 통계")
    print(f"{'='*80}")
    
    all_todos = repo.fetch_active(persona_name=None)
    by_persona = {}
    for todo in all_todos:
        persona = todo.get('persona_name') or 'UNKNOWN'
        if persona not in by_persona:
            by_persona[persona] = []
        by_persona[persona].append(todo)
    
    for persona, todos in sorted(by_persona.items()):
        print(f"  {persona}: {len(todos)}개")

if __name__ == "__main__":
    main()
