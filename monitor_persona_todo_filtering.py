"""
페르소나 변경 시 TODO 필터링 모니터링
"""
import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.ui.todo.repository import TodoRepository

def main():
    print("=" * 80)
    print("👁️  페르소나 TODO 필터링 모니터링")
    print("=" * 80)
    print("\nGUI에서 페르소나를 변경하면서 TODO 변화를 관찰합니다...")
    print("Ctrl+C로 종료\n")
    
    repo = TodoRepository()
    prev_state = {}
    
    try:
        while True:
            # 전체 TODO 조회
            all_todos = repo.fetch_active(persona_name=None)
            
            # 페르소나별로 그룹화
            by_persona = {}
            for todo in all_todos:
                persona = todo.get('persona_name') or 'UNKNOWN'
                if persona not in by_persona:
                    by_persona[persona] = []
                by_persona[persona].append(todo)
            
            # 변화 감지
            current_state = {p: len(todos) for p, todos in by_persona.items()}
            
            if current_state != prev_state:
                print(f"\n[{time.strftime('%H:%M:%S')}] 📊 TODO 상태 변화 감지:")
                print(f"  전체: {len(all_todos)}개")
                for persona in sorted(current_state.keys()):
                    count = current_state[persona]
                    prev_count = prev_state.get(persona, 0)
                    change = ""
                    if prev_count != count:
                        diff = count - prev_count
                        change = f" ({'+' if diff > 0 else ''}{diff})"
                    print(f"  - {persona}: {count}개{change}")
                
                prev_state = current_state
            
            time.sleep(2)  # 2초마다 체크
            
    except KeyboardInterrupt:
        print("\n\n✅ 모니터링 종료")

if __name__ == "__main__":
    main()
