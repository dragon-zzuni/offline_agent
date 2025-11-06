# -*- coding: utf-8 -*-
"""
이정두 vs 정지원 TODO 개수 비교
실제 데이터 분석
"""
import sys
import os
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

import sqlite3
from collections import defaultdict

print("=" * 80)
print("이정두 vs 정지원 TODO 개수 비교")
print("=" * 80)

# VDOS DB 연결
vdos_db_path = "../virtualoffice/src/virtualoffice/vdos.db"
conn = sqlite3.connect(vdos_db_path)
cur = conn.cursor()

# 1. 이정두와 정지원의 기본 정보
print("\n📋 기본 정보:")
cur.execute("""
    SELECT id, name, email_address, role
    FROM people
    WHERE name IN ('이정두', '정지원')
""")
people = cur.fetchall()
for pid, name, email, role in people:
    print(f"  {name} (ID: {pid}, {email}, {role})")

# 2. 프로젝트 참여 현황
print("\n📊 프로젝트 참여 현황:")
for pid, name, email, role in people:
    cur.execute("""
        SELECT pp.project_name
        FROM project_assignments pa
        JOIN project_plans pp ON pa.project_id = pp.id
        WHERE pa.person_id = ?
    """, (pid,))
    projects = [row[0] for row in cur.fetchall()]
    print(f"\n  {name}:")
    for proj in projects:
        print(f"    - {proj}")

# 3. 메시지 발신 통계 (이메일)
print("\n📧 이메일 발신 통계:")
for pid, name, email, role in people:
    cur.execute("""
        SELECT COUNT(*) as count
        FROM emails
        WHERE sender = ?
    """, (email,))
    count = cur.fetchone()[0]
    print(f"  {name}: {count}개")

# 4. 메시지 발신 통계 (채팅)
print("\n💬 채팅 메시지 발신 통계:")
for pid, name, email, role in people:
    cur.execute("""
        SELECT COUNT(*) as count
        FROM chat_messages
        WHERE sender = ?
    """, (email,))
    count = cur.fetchone()[0]
    print(f"  {name}: {count}개")

# 5. 메시지 수신 통계 (이메일 - TO/CC/BCC)
print("\n📨 이메일 수신 통계:")
for pid, name, email, role in people:
    # TO
    cur.execute("""
        SELECT COUNT(DISTINCT email_id)
        FROM email_recipients
        WHERE address = ? AND kind = 'to'
    """, (email,))
    to_count = cur.fetchone()[0]
    
    # CC
    cur.execute("""
        SELECT COUNT(DISTINCT email_id)
        FROM email_recipients
        WHERE address = ? AND kind = 'cc'
    """, (email,))
    cc_count = cur.fetchone()[0]
    
    # BCC
    cur.execute("""
        SELECT COUNT(DISTINCT email_id)
        FROM email_recipients
        WHERE address = ? AND kind = 'bcc'
    """, (email,))
    bcc_count = cur.fetchone()[0]
    
    print(f"  {name}:")
    print(f"    - TO: {to_count}개")
    print(f"    - CC: {cc_count}개")
    print(f"    - BCC: {bcc_count}개")
    print(f"    - 합계: {to_count + cc_count + bcc_count}개")

# 6. TODO 캐시 DB에서 실제 TODO 개수 확인
print("\n✅ TODO 캐시 DB 분석:")
cache_db_path = "../virtualoffice/src/virtualoffice/todos_cache.db"
if Path(cache_db_path).exists():
    cache_conn = sqlite3.connect(cache_db_path)
    cache_cur = cache_conn.cursor()
    
    # 테이블 존재 확인
    cache_cur.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='todos'
    """)
    if cache_cur.fetchone():
        # 이정두와 정지원의 TODO 개수
        for pid, name, email, role in people:
            cache_cur.execute("""
                SELECT COUNT(*)
                FROM todos
                WHERE persona_name = ?
            """, (name,))
            todo_count = cache_cur.fetchone()[0]
            
            # 우선순위별 분포
            cache_cur.execute("""
                SELECT priority, COUNT(*) as count
                FROM todos
                WHERE persona_name = ?
                GROUP BY priority
                ORDER BY 
                    CASE priority
                        WHEN 'high' THEN 1
                        WHEN 'medium' THEN 2
                        WHEN 'low' THEN 3
                        ELSE 4
                    END
            """, (name,))
            priority_dist = cache_cur.fetchall()
            
            print(f"\n  {name}: 총 {todo_count}개")
            for priority, count in priority_dist:
                print(f"    - {priority}: {count}개")
            
            # Top3 여부
            cache_cur.execute("""
                SELECT COUNT(*)
                FROM todos
                WHERE persona_name = ? AND is_top3 = 1
            """, (name,))
            top3_count = cache_cur.fetchone()[0]
            print(f"    - Top3: {top3_count}개")
    else:
        print("  ⚠️ todos 테이블이 없습니다")
    
    cache_conn.close()
else:
    print("  ⚠️ TODO 캐시 DB를 찾을 수 없습니다")

# 7. 액션 아이템 추출 가능성 분석
print("\n🔍 액션 아이템 키워드 분석:")
action_keywords = [
    '확인', '검토', '작성', '수정', '완료', '제출', '공유', '준비',
    '회의', '미팅', '논의', '결정', '승인', '요청', '부탁'
]

for pid, name, email, role in people:
    print(f"\n  {name}:")
    
    # 이메일에서 액션 키워드 포함 메시지 수
    cur.execute("""
        SELECT COUNT(DISTINCT e.id)
        FROM emails e
        JOIN email_recipients er ON e.id = er.email_id
        WHERE er.address = ?
        AND (e.subject LIKE '%확인%' OR e.subject LIKE '%검토%' OR e.subject LIKE '%작성%'
             OR e.subject LIKE '%회의%' OR e.subject LIKE '%요청%'
             OR e.body LIKE '%확인%' OR e.body LIKE '%검토%' OR e.body LIKE '%작성%'
             OR e.body LIKE '%회의%' OR e.body LIKE '%요청%')
    """, (email,))
    action_email_count = cur.fetchone()[0]
    
    print(f"    - 액션 키워드 포함 이메일: {action_email_count}개")

conn.close()

print("\n" + "=" * 80)
print("분석 완료")
print("=" * 80)
