#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Project VERTEX 관련 정보 확인"""
import sqlite3
from pathlib import Path

VDOS_DB = Path("../virtualoffice/src/virtualoffice/vdos.db")

if not VDOS_DB.exists():
    print(f"❌ VDOS DB 파일이 없습니다: {VDOS_DB}")
    exit(1)

conn = sqlite3.connect(str(VDOS_DB))
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("=" * 80)
print("📊 Project VERTEX 정보")
print("=" * 80)

# 1. 프로젝트 기본 정보
cur.execute("""
    SELECT id, code, name, description, owner_email
    FROM projects
    WHERE code = 'PV' OR name LIKE '%VERTEX%'
""")
project = cur.fetchone()

if project:
    print(f"\n프로젝트 ID: {project['id']}")
    print(f"코드: {project['code']}")
    print(f"이름: {project['name']}")
    print(f"설명: {project['description']}")
    print(f"오너: {project['owner_email']}")
else:
    print("\n❌ Project VERTEX를 찾을 수 없습니다")
    conn.close()
    exit(1)

project_id = project['id']

# 2. 프로젝트 플랜 정보
print(f"\n{'=' * 80}")
print("📋 프로젝트 플랜")
print("=" * 80)

cur.execute("""
    SELECT pp.id, pp.title, pp.description, pp.requester_email, pp.assignee_email,
           pp.status, pp.created_at
    FROM project_plans pp
    WHERE pp.project_id = ?
    ORDER BY pp.created_at DESC
    LIMIT 5
""", (project_id,))

plans = cur.fetchall()
if plans:
    for plan in plans:
        print(f"\n플랜 ID: {plan['id']}")
        print(f"  제목: {plan['title']}")
        print(f"  요청자: {plan['requester_email']}")
        print(f"  담당자: {plan['assignee_email']}")
        print(f"  상태: {plan['status']}")
        print(f"  생성일: {plan['created_at']}")
else:
    print("  플랜 없음")

# 3. 프로젝트 팀 멤버
print(f"\n{'=' * 80}")
print("👥 프로젝트 팀 멤버")
print("=" * 80)

cur.execute("""
    SELECT p.name, p.email_address, p.team_name, pm.role
    FROM project_members pm
    JOIN people p ON pm.person_email = p.email_address
    WHERE pm.project_id = ?
""", (project_id,))

members = cur.fetchall()
if members:
    for member in members:
        print(f"  {member['name']:15s} ({member['email_address']:30s}) - {member['role']:10s} [{member['team_name']}]")
else:
    print("  멤버 없음")

# 4. 이정두가 받은 VERTEX 관련 이메일 확인
print(f"\n{'=' * 80}")
print("📧 이정두가 받은 VERTEX 관련 이메일 (최근 10개)")
print("=" * 80)

cur.execute("""
    SELECT e.id, e.subject, e.sender_email, e.to_emails, e.cc_emails, e.sent_at
    FROM emails e
    WHERE (e.to_emails LIKE '%leejungdu@example.com%' OR e.cc_emails LIKE '%leejungdu@example.com%')
      AND (e.subject LIKE '%VERTEX%' OR e.body LIKE '%VERTEX%')
    ORDER BY e.sent_at DESC
    LIMIT 10
""")

emails = cur.fetchall()
if emails:
    for email in emails:
        print(f"\nID: {email['id']}")
        print(f"  제목: {email['subject']}")
        print(f"  발신자: {email['sender_email']}")
        print(f"  TO: {email['to_emails']}")
        print(f"  CC: {email['cc_emails']}")
        print(f"  시간: {email['sent_at']}")
        
        # 이정두가 TO인지 CC인지 확인
        is_to = 'leejungdu@example.com' in (email['to_emails'] or '')
        is_cc = 'leejungdu@example.com' in (email['cc_emails'] or '')
        print(f"  이정두: {'TO' if is_to else ''} {'CC' if is_cc else ''}")
else:
    print("  이메일 없음")

# 5. 이도윤 정보 확인
print(f"\n{'=' * 80}")
print("👤 이도윤 정보")
print("=" * 80)

cur.execute("""
    SELECT name, email_address, team_name, chat_handle
    FROM people
    WHERE name LIKE '%이도윤%' OR name LIKE '%도윤%'
""")

doyoon = cur.fetchone()
if doyoon:
    print(f"이름: {doyoon['name']}")
    print(f"이메일: {doyoon['email_address']}")
    print(f"팀: {doyoon['team_name']}")
    print(f"핸들: {doyoon['chat_handle']}")
    
    # 이도윤이 보낸 VERTEX 관련 이메일
    print(f"\n이도윤이 보낸 VERTEX 관련 이메일 (최근 5개):")
    cur.execute("""
        SELECT id, subject, to_emails, cc_emails, sent_at
        FROM emails
        WHERE sender_email = ?
          AND (subject LIKE '%VERTEX%' OR body LIKE '%VERTEX%')
        ORDER BY sent_at DESC
        LIMIT 5
    """, (doyoon['email_address'],))
    
    doyoon_emails = cur.fetchall()
    for email in doyoon_emails:
        print(f"\n  ID: {email['id']}")
        print(f"    제목: {email['subject']}")
        print(f"    TO: {email['to_emails']}")
        print(f"    CC: {email['cc_emails']}")
        print(f"    시간: {email['sent_at']}")
else:
    print("  이도윤을 찾을 수 없습니다")

conn.close()
