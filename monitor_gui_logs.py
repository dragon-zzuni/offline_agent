#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GUI 로그 실시간 모니터링"""

import time
import subprocess
import sys

def monitor_logs():
    """GUI 로그 실시간 모니터링"""
    
    print("=" * 80)
    print("GUI 로그 실시간 모니터링")
    print("=" * 80)
    print("\n로그를 모니터링합니다. Ctrl+C로 종료하세요.\n")
    
    try:
        # 로그 파일이 있다면 tail -f처럼 모니터링
        # 없다면 프로세스 출력 모니터링
        
        while True:
            time.sleep(2)
            
            # 여기서는 간단히 TODO DB 상태만 확인
            import sqlite3
            from pathlib import Path
            
            todos_db = Path("offline_agent/data/multi_project_8week_ko/todos_cache.db")
            if todos_db.exists():
                conn = sqlite3.connect(todos_db)
                cursor = conn.cursor()
                
                cursor.execute("SELECT COUNT(*) FROM todos")
                todo_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM todos WHERE is_top3 = 1")
                top3_count = cursor.fetchone()[0]
                
                print(f"[{time.strftime('%H:%M:%S')}] TODO: {todo_count}개, TOP3: {top3_count}개", end='\r')
                
                conn.close()
            
    except KeyboardInterrupt:
        print("\n\n모니터링 종료")

if __name__ == "__main__":
    monitor_logs()
