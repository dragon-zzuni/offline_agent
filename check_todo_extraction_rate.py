# -*- coding: utf-8 -*-
"""TODO 추출률 분석 스크립트"""
import sys
import os
import sqlite3

# DB 경로
vdos_db_path = "virtualoffice/src/virtualoffice/vdos.db"
todos_db_path = "virtualoffice/src/virtualoffice/todos_cache.db"

print("=" * 80)
print("TODO 추출률 분석")
print("=" * 80)

# 1. VDOS DB에서 메시지 수 확인
print("\n📊 VDOS DB 분석:")
conn = sqlite3.connect(vdos_db_path)
cursor = conn.cursor()

# 이메일 수
cursor.execute("SELECT COUNT(*) FROM emails")
email_count = cursor.fetchone()[0]
print(f"  - 전체 이메일: {email_count:,}개")

# 특정 페르소나가 받은 이메일 (leejungdu@example.com)
cursor.execute("""
    SELECT COUNT(DISTINCT e.id) 
    FROM emails e
    JOIN email_recipients er ON e.id = er.email_id
    WHERE er.address = 'leejungdu@example.com'
""")
received_emails = cursor.fetchone()[0]
print(f"  - 이정두가 받은 이메일: {received_emails:,}개")

# 채팅 메시지 수
cursor.execute("SELECT COUNT(*) FROM chat_messages")
chat_count = cursor.fetchone()[0]
print(f"  - 전체 채팅 메시지: {chat_count:,}개")

# 이정두가 받은 DM (lee_jd)
cursor.execute("""
    SELECT COUNT(*) 
    FROM chat_messages cm
    JOIN chat_rooms cr ON cm.room_id = cr.id
    WHERE cr.slug LIKE '%lee_jd%'
    AND cm.sender != 'lee_jd'
""")
received_chats = cursor.fetchone()[0]
print(f"  - 이정두가 받은 DM: {received_chats:,}개")

total_received = received_emails + received_chats
print(f"\n  ✅ 총 수신 메시지: {total_received:,}개")

conn.close()

# 2. TODO DB 분석
print("\n📋 TODO DB 분석:")
if not os.path.exists(todos_db_path):
    print(f"  ❌ TODO DB를 찾을 수 없습니다: {todos_db_path}")
else:
    conn = sqlite3.connect(todos_db_path)
    cursor = conn.cursor()
    
    # 전체 TODO 수
    cursor.execute("SELECT COUNT(*) FROM todos")
    todo_count = cursor.fetchone()[0]
    print(f"  - 전체 TODO: {todo_count}개")
    
    # 상태별 TODO 수
    cursor.execute("""
        SELECT status, COUNT(*) 
        FROM todos 
        GROUP BY status
    """)
    status_counts = cursor.fetchall()
    for status, count in status_counts:
        print(f"    • {status}: {count}개")
    
    # 유형별 TODO 수
    cursor.execute("""
        SELECT type, COUNT(*) 
        FROM todos 
        GROUP BY type
        ORDER BY COUNT(*) DESC
    """)
    type_counts = cursor.fetchall()
    print(f"\n  유형별 분포:")
    for todo_type, count in type_counts:
        print(f"    • {todo_type}: {count}개")
    
    # 요청자별 TODO 수 (상위 10명)
    cursor.execute("""
        SELECT requester, COUNT(*) 
        FROM todos 
        GROUP BY requester
        ORDER BY COUNT(*) DESC
        LIMIT 10
    """)
    requester_counts = cursor.fetchall()
    print(f"\n  요청자별 분포 (상위 10명):")
    for requester, count in requester_counts:
        print(f"    • {requester}: {count}개")
    
    conn.close()

# 3. 추출률 계산
print("\n" + "=" * 80)
print("📈 추출률 분석:")
print("=" * 80)

if total_received > 0 and todo_count > 0:
    extraction_rate = (todo_count / total_received) * 100
    print(f"\n  총 수신 메시지: {total_received:,}개")
    print(f"  생성된 TODO: {todo_count}개")
    print(f"  추출률: {extraction_rate:.2f}%")
    
    if extraction_rate < 1.0:
        print(f"\n  ⚠️ 추출률이 매우 낮습니다! ({extraction_rate:.2f}%)")
        print(f"  예상 원인:")
        print(f"    1. ActionExtractor가 너무 보수적으로 TODO 추출")
        print(f"    2. 대부분의 메시지가 정보 공유용 (액션 없음)")
        print(f"    3. 중복 제거로 인한 감소")
        print(f"    4. PM이 보낸 메시지 제외 (정상)")
    elif extraction_rate < 5.0:
        print(f"\n  ⚠️ 추출률이 낮습니다 ({extraction_rate:.2f}%)")
        print(f"  일반적으로 5-10% 정도가 적정합니다.")
    elif extraction_rate < 15.0:
        print(f"\n  ✅ 추출률이 적정합니다 ({extraction_rate:.2f}%)")
    else:
        print(f"\n  ⚠️ 추출률이 높습니다 ({extraction_rate:.2f}%)")
        print(f"  너무 많은 TODO가 생성되고 있을 수 있습니다.")

print("\n" + "=" * 80)

# 4. 샘플 메시지 확인 (TODO가 생성되지 않은 메시지)
print("\n🔍 샘플 분석 (TODO가 없는 메시지 확인):")
print("=" * 80)

conn = sqlite3.connect(vdos_db_path)
cursor = conn.cursor()

# 이정두가 받은 최근 이메일 5개 샘플
cursor.execute("""
    SELECT e.id, e.sender, e.subject, e.body
    FROM emails e
    JOIN email_recipients er ON e.id = er.email_id
    WHERE er.address = 'leejungdu@example.com'
    ORDER BY e.sent_at DESC
    LIMIT 5
""")
sample_emails = cursor.fetchall()

print("\n최근 이메일 샘플 (5개):")
for email_id, sender, subject, body in sample_emails:
    print(f"\n  📧 Email ID: {email_id}")
    print(f"     발신자: {sender}")
    print(f"     제목: {subject}")
    print(f"     본문: {body[:100]}...")
    
    # 이 이메일에서 TODO가 생성되었는지 확인
    conn2 = sqlite3.connect(todos_db_path)
    cursor2 = conn2.cursor()
    cursor2.execute("""
        SELECT COUNT(*) FROM todos 
        WHERE source_message LIKE ?
    """, (f'%"id": "email_{email_id}"%',))
    todo_exists = cursor2.fetchone()[0] > 0
    conn2.close()
    
    if todo_exists:
        print(f"     ✅ TODO 생성됨")
    else:
        print(f"     ❌ TODO 없음")

conn.close()

print("\n" + "=" * 80)
