#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
페르소나 변경 모니터링 스크립트
GUI를 백그라운드로 실행하고 로그를 추적합니다.
"""
import subprocess
import time
import sqlite3
from pathlib import Path
from datetime import datetime

def check_todos():
    """현재 TODO 상태 확인"""
    todo_db_path = Path("virtualoffice/src/virtualoffice/todos_cache.db")
    
    if not todo_db_path.exists():
        return "DB 없음", []
    
    conn = sqlite3.connect(str(todo_db_path))
    cur = conn.cursor()
    
    cur.execute("SELECT COUNT(*) FROM todos")
    total = cur.fetchone()[0]
    
    cur.execute("""
        SELECT requester, COUNT(*) as cnt
        FROM todos
        GROUP BY requester
        ORDER BY cnt DESC
        LIMIT 5
    """)
    top_requesters = cur.fetchall()
    
    conn.close()
    
    return total, top_requesters

def main():
    print("=" * 80)
    print("페르소나 변경 모니터링")
    print("=" * 80)
    print("\n📝 GUI를 실행하고 페르소나를 변경해보세요.")
    print("   이 스크립트는 5초마다 TODO 상태를 확인합니다.\n")
    print("   Ctrl+C로 종료하세요.\n")
    print("=" * 80)
    
    last_total = None
    last_requesters = None
    
    try:
        while True:
            total, requesters = check_todos()
            
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # 변경 감지
            if total != last_total or requesters != last_requesters:
                print(f"\n[{timestamp}] 🔄 TODO 변경 감지!")
                print(f"  총 TODO: {total}개")
                
                if requesters:
                    print(f"  요청자 Top 5:")
                    for requester, cnt in requesters:
                        print(f"    - {requester}: {cnt}개")
                else:
                    print(f"  (TODO 없음)")
                
                last_total = total
                last_requesters = requesters
            else:
                print(f"[{timestamp}] ✓ 변경 없음 (총 {total}개)", end="\r")
            
            time.sleep(5)
    
    except KeyboardInterrupt:
        print("\n\n모니터링 종료")
        print("=" * 80)

if __name__ == "__main__":
    main()
