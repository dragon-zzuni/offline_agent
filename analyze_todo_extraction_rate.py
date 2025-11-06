#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TODO 추출률 분석"""

import sqlite3
from pathlib import Path
import json

def analyze_extraction_rate():
    """TODO 추출률 분석"""
    
    print("=" * 80)
    print("TODO 추출률 분석")
    print("=" * 80)
    
    # VDOS DB
    vdos_db = Path("virtualoffice/src/virtualoffice/vdos.db")
    todos_db = Path("virtualoffice/src/virtualoffice/todos_cache.db")
    
    if not vdos_db.exists():
        print(f"\n❌ VDOS DB 없음: {vdos_db}")
        return
    
    if not todos_db.exists():
        print(f"\n❌ TODO DB 없음: {todos_db}")
        return
    
    # VDOS DB 연결
    vdos_conn = sqlite3.connect(vdos_db)
    vdos_cursor = vdos_conn.cursor()
    
    # TODO DB 연결
    todos_conn = sqlite3.connect(todos_db)
    todos_cursor = todos_conn.cursor()
    
    # 1. 이정두가 받은 메시지 수
    print("\n[1] 이정두가 받은 메시지:")
    
    vdos_cursor.execute("""
        SELECT COUNT(*)
        FROM email_recipients
        WHERE address = 'leejungdu@example.com'
    """)
    email_count = vdos_cursor.fetchone()[0]
    print(f"  이메일: {email_count:,}개")
    
    vdos_cursor.execute("""
        SELECT COUNT(*)
        FROM chat_messages
        WHERE sender != 'lee_jd'
    """)
    chat_count = vdos_cursor.fetchone()[0]
    print(f"  채팅 (이정두 제외): {chat_count:,}개")
    
    total_messages = email_count + chat_count
    print(f"  총 메시지: {total_messages:,}개")
    
    # 2. 생성된 TODO 수
    print("\n[2] 생성된 TODO:")
    
    todos_cursor.execute("""
        SELECT COUNT(*)
        FROM todos
        WHERE requester = 'jungjiwon@koreaitcompany.com'
    """)
    todo_count = todos_cursor.fetchone()[0]
    print(f"  총 TODO: {todo_count}개")
    
    if total_messages > 0:
        extraction_rate = (todo_count / total_messages) * 100
        print(f"  추출률: {extraction_rate:.2f}%")
        print(f"  ⚠️ 매우 낮은 추출률! (정상: 5-10%)")
    
    # 3. TODO 유형별 분포
    print("\n[3] TODO 유형별 분포:")
    todos_cursor.execute("""
        SELECT type, COUNT(*) as count
        FROM todos
        WHERE requester = 'jungjiwon@koreaitcompany.com'
        GROUP BY type
        ORDER BY count DESC
    """)
    
    type_dist = todos_cursor.fetchall()
    for todo_type, count in type_dist:
        print(f"  {todo_type if todo_type else '(NULL)'}: {count}개")
    
    # 4. TODO 생성 시간 분포
    print("\n[4] TODO 생성 시간:")
    todos_cursor.execute("""
        SELECT MIN(created_at) as first, MAX(created_at) as last
        FROM todos
        WHERE requester = 'jungjiwon@koreaitcompany.com'
    """)
    
    time_range = todos_cursor.fetchone()
    if time_range[0]:
        print(f"  최초 생성: {time_range[0]}")
        print(f"  최근 생성: {time_range[1]}")
    
    # 5. source_message 분석
    print("\n[5] TODO 원본 메시지 분석:")
    todos_cursor.execute("""
        SELECT source_message
        FROM todos
        WHERE requester = 'jungjiwon@koreaitcompany.com'
        LIMIT 5
    """)
    
    sources = todos_cursor.fetchall()
    print(f"  샘플 (5개):")
    for i, (source,) in enumerate(sources, 1):
        if source:
            try:
                source_data = json.loads(source)
                print(f"    {i}. {source_data.get('id', 'N/A')}")
            except:
                print(f"    {i}. {source[:50]}...")
        else:
            print(f"    {i}. (NULL)")
    
    # 6. 이메일 샘플 확인
    print("\n[6] 이메일 샘플 (최근 10개):")
    vdos_cursor.execute("""
        SELECT e.id, e.subject, e.body, e.sent_at
        FROM emails e
        JOIN email_recipients er ON e.id = er.email_id
        WHERE er.address = 'leejungdu@example.com'
        ORDER BY e.sent_at DESC
        LIMIT 10
    """)
    
    emails = vdos_cursor.fetchall()
    for i, (email_id, subject, body, sent_at) in enumerate(emails, 1):
        print(f"\n  {i}. [{email_id}] {subject}")
        print(f"     시간: {sent_at}")
        print(f"     내용: {body[:100] if body else 'N/A'}...")
        
        # 이 이메일로 TODO가 생성되었는지 확인
        todos_cursor.execute("""
            SELECT COUNT(*)
            FROM todos
            WHERE source_message LIKE ?
        """, (f'%"id": "{email_id}"%',))
        
        has_todo = todos_cursor.fetchone()[0]
        print(f"     TODO 생성: {'✅' if has_todo > 0 else '❌'}")
    
    # 7. 가능한 원인 분석
    print("\n[7] 가능한 원인:")
    
    # requester 필드 확인
    todos_cursor.execute("""
        SELECT DISTINCT requester
        FROM todos
    """)
    
    requesters = todos_cursor.fetchall()
    print(f"\n  A. DB의 requester 목록:")
    for (requester,) in requesters:
        todos_cursor.execute("""
            SELECT COUNT(*)
            FROM todos
            WHERE requester = ?
        """, (requester,))
        count = todos_cursor.fetchone()[0]
        print(f"     - {requester if requester else '(NULL)'}: {count}개")
    
    # 이정두 관련 TODO 확인
    todos_cursor.execute("""
        SELECT COUNT(*)
        FROM todos
        WHERE requester LIKE '%이정두%' OR requester LIKE '%leejungdu%' OR requester LIKE '%lee_jd%'
    """)
    jeongdu_count = todos_cursor.fetchone()[0]
    print(f"\n  B. 이정두 관련 TODO: {jeongdu_count}개")
    
    if jeongdu_count == 0:
        print("     ⚠️ 이정두 이름으로 TODO가 하나도 없음!")
        print("     → requester 필드가 발신자 이메일로 저장되고 있을 가능성")
    
    vdos_conn.close()
    todos_conn.close()
    
    print("\n" + "=" * 80)
    print("분석 완료")
    print("=" * 80)
    
    # 결론
    print("\n💡 결론:")
    if todo_count < 100:
        print("  1. TODO 추출률이 비정상적으로 낮음 (0.1% 미만)")
        print("  2. 가능한 원인:")
        print("     - LLM 분석이 실행되지 않음")
        print("     - 분석 중 오류 발생")
        print("     - 필터링 조건이 너무 엄격함")
        print("     - requester 필드 매칭 문제")
        print("  3. 해결 방법:")
        print("     - GUI에서 '분석 시작' 버튼 클릭")
        print("     - 로그에서 오류 메시지 확인")
        print("     - LLM API 키 확인")

if __name__ == "__main__":
    analyze_extraction_rate()
