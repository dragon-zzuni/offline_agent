#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""샘플 TODO 확인"""

import sqlite3
import json

# 올바른 DB 경로
DB_PATH = r"C:\Users\USER\Desktop\virtual-office-orchestration\virtualoffice\src\virtualoffice\todos_cache.db"

def check_sample():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 태그 없는 TODO 샘플 5개
    cursor.execute("""
        SELECT id, title, description, requester, type, source_type, project_tag
        FROM todos
        WHERE project_tag IS NULL OR project_tag = ''
        LIMIT 5
    """)
    
    print(f"\n{'='*80}")
    print(f"태그 없는 TODO 샘플 (5개)")
    print(f"{'='*80}\n")
    
    for i, row in enumerate(cursor.fetchall(), 1):
        todo_id, title, description, requester, todo_type, source_type, project_tag = row
        
        print(f"[TODO #{i}]")
        print(f"  ID: {todo_id}")
        print(f"  제목: {title}")
        print(f"  설명: {description[:200] if description else '(없음)'}")
        print(f"  요청자: {requester}")
        print(f"  유형: {todo_type}")
        print(f"  수신방법: {source_type}")
        print(f"  프로젝트 태그: {project_tag or '❌ 없음'}")
        print()
    
    # 태그 있는 TODO 샘플
    cursor.execute("""
        SELECT id, title, description, requester, type, source_type, project_tag
        FROM todos
        WHERE project_tag IS NOT NULL AND project_tag != ''
        LIMIT 5
    """)
    
    print(f"{'='*80}")
    print(f"태그 있는 TODO 샘플 (5개)")
    print(f"{'='*80}\n")
    
    for i, row in enumerate(cursor.fetchall(), 1):
        todo_id, title, description, requester, todo_type, source_type, project_tag = row
        
        print(f"[TODO #{i}]")
        print(f"  ID: {todo_id}")
        print(f"  제목: {title}")
        print(f"  설명: {description[:200] if description else '(없음)'}")
        print(f"  요청자: {requester}")
        print(f"  유형: {todo_type}")
        print(f"  수신방법: {source_type}")
        print(f"  프로젝트 태그: {project_tag}")
        print()
    
    conn.close()

if __name__ == "__main__":
    check_sample()
