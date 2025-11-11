#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""특정 TODO 상세 분석 스크립트"""
import sqlite3
import os
import json

# DB 경로
db_path = os.path.join(os.path.dirname(__file__), "../virtualoffice/src/virtualoffice/todos_cache.db")

if not os.path.exists(db_path):
    print(f"DB 파일을 찾을 수 없습니다: {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 임보연의 HIGH 우선순위 TODO 중 "확인했습니다" 포함된 것 찾기
query = """
SELECT 
    id, 
    title, 
    description, 
    priority, 
    requester,
    evidence,
    source_message,
    type,
    recipient_type,
    source_type
FROM todos 
WHERE persona_name = '임보연'
  AND priority = 'high'
  AND (description LIKE '%확인했습니다%' OR description LIKE '%안녕하세요%')
ORDER BY created_at DESC 
LIMIT 5
"""

cursor.execute(query)
rows = cursor.fetchall()

print(f"\n임보연 HIGH 우선순위 TODO (인사/확인 메시지):\n")
print("=" * 120)

for i, row in enumerate(rows, 1):
    todo_id, title, description, priority, requester, evidence, source_msg, todo_type, recipient_type, source_type = row
    
    print(f"\n[TODO #{i}] ⚠️ 문제 사례")
    print(f"ID: {todo_id}")
    print(f"제목: {title}")
    print(f"설명: {description[:200]}")
    print(f"발신자: {requester}")
    print(f"유형: {todo_type}")
    print(f"우선순위: {priority} ⚠️")
    print(f"수신 타입: {recipient_type}")
    print(f"소스 타입: {source_type}")
    
    # evidence 파싱
    if evidence:
        try:
            evidence_data = json.loads(evidence)
            if isinstance(evidence_data, list) and len(evidence_data) > 0:
                print(f"\nEvidence ({len(evidence_data)}개):")
                for j, reason in enumerate(evidence_data, 1):
                    print(f"  {j}. {reason}")
            else:
                print(f"\nEvidence: 빈 배열")
        except Exception as e:
            print(f"\nEvidence 파싱 실패: {e}")
    
    # 원본 메시지 파싱
    if source_msg:
        try:
            msg_data = json.loads(source_msg)
            print(f"\n원본 메시지:")
            print(f"  - ID: {msg_data.get('id')}")
            print(f"  - 발신자: {msg_data.get('sender')}")
            print(f"  - 제목: {msg_data.get('subject')}")
            print(f"  - 플랫폼: {msg_data.get('platform')}")
        except:
            pass
    
    print("-" * 120)

# VDOS DB에서 원본 메시지 내용 확인
print("\n\n" + "=" * 120)
print("VDOS DB에서 원본 메시지 전체 내용 확인")
print("=" * 120)

vdos_db_path = os.path.join(os.path.dirname(__file__), "../virtualoffice/src/virtualoffice/vdos.db")

if os.path.exists(vdos_db_path):
    vdos_conn = sqlite3.connect(vdos_db_path)
    vdos_cursor = vdos_conn.cursor()
    
    # 임보연이 받은 메시지 중 "확인했습니다" 포함된 것
    vdos_query = """
    SELECT 
        id,
        sender,
        body,
        created_at
    FROM chat_messages 
    WHERE recipient = 'imboyeon_koreait'
      AND body LIKE '%확인했습니다%'
    ORDER BY created_at DESC 
    LIMIT 3
    """
    
    try:
        vdos_cursor.execute(vdos_query)
        vdos_rows = vdos_cursor.fetchall()
        
        for i, row in enumerate(vdos_rows, 1):
            msg_id, sender, body, created_at = row
            print(f"\n[원본 메시지 #{i}]")
            print(f"ID: {msg_id}")
            print(f"발신자: {sender}")
            print(f"시간: {created_at}")
            print(f"전체 내용:\n{body}")
            print("-" * 100)
    except Exception as e:
        print(f"VDOS 쿼리 실패: {e}")
    
    vdos_conn.close()

conn.close()

# 통계
print("\n\n" + "=" * 120)
print("통계 분석")
print("=" * 120)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 임보연의 우선순위별 TODO 개수
cursor.execute("""
    SELECT priority, COUNT(*) 
    FROM todos 
    WHERE persona_name = '임보연' 
    GROUP BY priority
""")
priority_stats = cursor.fetchall()

print("\n임보연 TODO 우선순위 분포:")
for priority, count in priority_stats:
    print(f"  - {priority}: {count}개")

# HIGH 우선순위 중 단순 메시지 비율
cursor.execute("""
    SELECT COUNT(*) 
    FROM todos 
    WHERE persona_name = '임보연' 
      AND priority = 'high'
      AND (description LIKE '%확인했습니다%' 
           OR description LIKE '%안녕하세요%'
           OR description LIKE '%작업 중입니다%')
""")
simple_high = cursor.fetchone()[0]

cursor.execute("""
    SELECT COUNT(*) 
    FROM todos 
    WHERE persona_name = '임보연' 
      AND priority = 'high'
""")
total_high = cursor.fetchone()[0]

if total_high > 0:
    print(f"\nHIGH 우선순위 중 단순 메시지:")
    print(f"  - 단순 메시지: {simple_high}개")
    print(f"  - 전체 HIGH: {total_high}개")
    print(f"  - 비율: {simple_high/total_high*100:.1f}%")

conn.close()
