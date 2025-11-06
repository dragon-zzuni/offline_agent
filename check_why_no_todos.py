#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TODO가 생성되지 않는 이유 확인"""

import sqlite3
from pathlib import Path

def check_why_no_todos():
    """TODO가 생성되지 않는 이유 확인"""
    
    print("=" * 80)
    print("TODO 생성 문제 진단")
    print("=" * 80)
    
    # 1. TODO DB 확인
    print("\n[1] TODO DB 상태:")
    todos_db = Path("offline_agent/data/multi_project_8week_ko/todos_cache.db")
    
    if not todos_db.exists():
        print(f"  ❌ TODO DB 없음: {todos_db}")
        print("  → GUI를 실행하면 자동으로 생성됩니다")
        return
    
    print(f"  ✅ TODO DB 존재: {todos_db}")
    print(f"  파일 크기: {todos_db.stat().st_size:,} bytes")
    
    conn = sqlite3.connect(todos_db)
    cursor = conn.cursor()
    
    # TODO 개수
    cursor.execute("SELECT COUNT(*) FROM todos")
    todo_count = cursor.fetchone()[0]
    print(f"  TODO 개수: {todo_count}개")
    
    if todo_count == 0:
        print("  ⚠️ TODO가 하나도 없습니다!")
        print("  → 분석이 실행되지 않았거나 실패했을 가능성이 높습니다")
    
    conn.close()
    
    # 2. VDOS DB 확인
    print("\n[2] VDOS DB 상태:")
    vdos_db = Path("virtualoffice/src/virtualoffice/vdos.db")
    
    if not vdos_db.exists():
        print(f"  ❌ VDOS DB 없음: {vdos_db}")
        print("  → VirtualOffice 시뮬레이션을 먼저 실행해야 합니다")
        return
    
    print(f"  ✅ VDOS DB 존재: {vdos_db}")
    print(f"  파일 크기: {vdos_db.stat().st_size:,} bytes")
    
    conn = sqlite3.connect(vdos_db)
    cursor = conn.cursor()
    
    # 페르소나 개수
    cursor.execute("SELECT COUNT(*) FROM people")
    people_count = cursor.fetchone()[0]
    print(f"  페르소나 개수: {people_count}명")
    
    # 이메일 개수
    cursor.execute("SELECT COUNT(*) FROM emails")
    email_count = cursor.fetchone()[0]
    print(f"  이메일 개수: {email_count:,}개")
    
    # 채팅 개수
    cursor.execute("SELECT COUNT(*) FROM chat_messages")
    chat_count = cursor.fetchone()[0]
    print(f"  채팅 개수: {chat_count:,}개")
    
    # 이정두가 받은 메시지
    print("\n[3] 이정두가 받은 메시지:")
    
    cursor.execute("""
        SELECT COUNT(*)
        FROM email_recipients
        WHERE address = 'leejungdu@example.com'
    """)
    jeongdu_emails = cursor.fetchone()[0]
    print(f"  이메일: {jeongdu_emails:,}개")
    
    cursor.execute("""
        SELECT COUNT(*)
        FROM chat_messages
        WHERE sender != 'lee_jd'
    """)
    jeongdu_chats = cursor.fetchone()[0]
    print(f"  채팅 (이정두 제외): {jeongdu_chats:,}개")
    
    conn.close()
    
    # 4. 진단 결과
    print("\n[4] 진단 결과:")
    
    if todo_count == 0 and jeongdu_emails > 0:
        print("  ⚠️ 메시지는 있지만 TODO가 없습니다")
        print("\n  가능한 원인:")
        print("    1. GUI에서 '분석 시작' 버튼을 누르지 않았음")
        print("    2. 페르소나가 '이정두'로 선택되지 않았음")
        print("    3. 분석 중 오류 발생")
        print("    4. LLM API 키가 설정되지 않았음")
        print("\n  해결 방법:")
        print("    1. GUI를 실행하고 페르소나를 '이정두'로 선택")
        print("    2. '분석 시작' 버튼 클릭")
        print("    3. 로그에서 오류 메시지 확인")
    elif todo_count > 0:
        print("  ✅ TODO가 정상적으로 생성되어 있습니다")
    else:
        print("  ❌ VDOS DB에 메시지가 없습니다")
        print("  → VirtualOffice 시뮬레이션을 먼저 실행하세요")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    check_why_no_todos()
