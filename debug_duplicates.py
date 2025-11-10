"""
중복 제거된 TODO 분석 스크립트
"""
import sqlite3
import json
from datetime import datetime

def analyze_todos():
    db_path = "offline_agent/data/multi_project_8week_ko/todos_cache.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 모든 TODO 가져오기
        cursor.execute("""
            SELECT id, title, description, priority, requester, deadline, 
                   created_at, source_messages
            FROM todos
            ORDER BY created_at DESC
        """)
        
        todos = cursor.fetchall()
        
        print(f"\n{'='*80}")
        print(f"총 {len(todos)}개의 TODO가 DB에 저장되어 있습니다")
        print(f"{'='*80}\n")
        
        # TODO 상세 정보 출력
        for idx, todo in enumerate(todos, 1):
            todo_id, title, description, priority, requester, deadline, created_at, source_msgs = todo
            
            print(f"\n[TODO #{idx}] ID: {todo_id}")
            print(f"제목: {title}")
            print(f"설명: {description[:100] if description else '(없음)'}...")
            print(f"우선순위: {priority}")
            print(f"요청자: {requester}")
            print(f"마감일: {deadline}")
            print(f"생성일: {created_at}")
            
            # source_messages 파싱
            if source_msgs:
                try:
                    msgs = json.loads(source_msgs)
                    print(f"관련 메시지: {len(msgs)}개")
                except:
                    print(f"관련 메시지: 파싱 실패")
            
            print("-" * 80)
        
        conn.close()
        
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analyze_todos()
