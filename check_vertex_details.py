#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Project VERTEX 상세 정보 확인"""
import sqlite3
import json
from pathlib import Path

VDOS_DB = Path("../virtualoffice/src/virtualoffice/vdos.db")

conn = sqlite3.connect(str(VDOS_DB))
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("=" * 80)
print("📊 Project VERTEX 정보")
print("=" * 80)

# 1. 프로젝트 플랜 확인
cur.execute("""
    SELECT id, project_name, project_summary, generated_by, duration_weeks, start_week
    FROM project_plans
    WHERE project_name LIKE '%VERTEX%'
""")

plans = cur.fetchall()
if plans:
    for plan in plans:
        print(f"\n플랜 ID: {plan['id']}")
        print(f"프로젝트명: {plan['project_name']}")
        print(f"요약: {plan['project_summary']}")
        print(f"생성자 ID: {plan['generated_by']}")
        print(f"기간: {plan['duration_weeks']}주")
        print(f"시작 주: {plan['start_week']}")
        
        # 생성자 정보
        cur.execute("SELECT name, email_address, team_name FROM people WHERE id = ?", (plan['generated_by'],))
        creator = cur.fetchone()
        if creator:
            print(f"생성자: {creator['name']} ({creator['email_address']}) - {creator['team_name']}")
else:
    print("\n❌ VERTEX 프로젝트 플랜을 찾을 수 없습니다")

# 2. 프로젝트 할당 확인
print(f"\n{'=' * 80}")
print("👥 프로젝트 할당")
print("=" * 80)

if plans:
    plan_id = plans[0]['id']
    cur.execute("""
        SELECT pa.id, p.name, p.email_address, p.team_name, p.role
        FROM project_assignments pa
        JOIN people p ON pa.person_id = p.id
        WHERE pa.project_id = ?
    """, (plan_id,))
    
    assignments = cur.fetchall()
    if assignments:
        for assign in assignments:
            print(f"  {assign['name']:15s} ({assign['email_address']:30s}) - {assign['role']:15s} [{assign['team_name']}]")
    else:
        print("  할당 없음")

# 3. 이정두 정보
print(f"\n{'=' * 80}")
print("👤 이정두 정보")
print("=" * 80)

cur.execute("""
    SELECT id, name, email_address, team_name, role
    FROM people
    WHERE name LIKE '%이정두%' OR email_address LIKE '%leejungdu%'
""")

jungdu = cur.fetchone()
if jungdu:
    print(f"ID: {jungdu['id']}")
    print(f"이름: {jungdu['name']}")
    print(f"이메일: {jungdu['email_address']}")
    print(f"팀: {jungdu['team_name']}")
    print(f"역할: {jungdu['role']}")
    
    # 이정두가 할당된 프로젝트
    print(f"\n이정두가 할당된 프로젝트:")
    cur.execute("""
        SELECT pp.project_name
        FROM project_assignments pa
        JOIN project_plans pp ON pa.project_id = pp.id
        WHERE pa.person_id = ?
    """, (jungdu['id'],))
    
    jungdu_projects = cur.fetchall()
    for proj in jungdu_projects:
        print(f"  - {proj['project_name']}")

# 4. VERTEX 관련 이메일 확인 (이정두가 TO로 받은 것)
print(f"\n{'=' * 80}")
print("📧 이정두가 TO로 받은 VERTEX 관련 이메일 (최근 5개)")
print("=" * 80)

cur.execute("""
    SELECT e.id, e.subject, e.sender, e.sent_at,
           GROUP_CONCAT(CASE WHEN er.kind = 'to' THEN er.address END) as to_emails,
           GROUP_CONCAT(CASE WHEN er.kind = 'cc' THEN er.address END) as cc_emails
    FROM emails e
    LEFT JOIN email_recipients er ON e.id = er.email_id
    WHERE (e.subject LIKE '%VERTEX%' OR e.body LIKE '%VERTEX%')
    GROUP BY e.id
    HAVING to_emails LIKE '%leejungdu@example.com%'
    ORDER BY e.sent_at DESC
    LIMIT 5
""")

to_emails = cur.fetchall()
if to_emails:
    for email in to_emails:
        print(f"\nID: {email['id']}")
        print(f"  제목: {email['subject']}")
        print(f"  발신자: {email['sender']}")
        print(f"  TO: {email['to_emails']}")
        print(f"  CC: {email['cc_emails']}")
        print(f"  시간: {email['sent_at']}")
else:
    print("  없음")

# 5. VERTEX 관련 이메일 확인 (이정두가 CC로 받은 것)
print(f"\n{'=' * 80}")
print("📧 이정두가 CC로 받은 VERTEX 관련 이메일 (최근 5개)")
print("=" * 80)

cur.execute("""
    SELECT e.id, e.subject, e.sender, e.sent_at,
           GROUP_CONCAT(CASE WHEN er.kind = 'to' THEN er.address END) as to_emails,
           GROUP_CONCAT(CASE WHEN er.kind = 'cc' THEN er.address END) as cc_emails
    FROM emails e
    LEFT JOIN email_recipients er ON e.id = er.email_id
    WHERE (e.subject LIKE '%VERTEX%' OR e.body LIKE '%VERTEX%')
    GROUP BY e.id
    HAVING cc_emails LIKE '%leejungdu@example.com%'
    ORDER BY e.sent_at DESC
    LIMIT 5
""")

cc_emails = cur.fetchall()
if cc_emails:
    for email in cc_emails:
        print(f"\nID: {email['id']}")
        print(f"  제목: {email['subject']}")
        print(f"  발신자: {email['sender']}")
        print(f"  TO: {email['to_emails']}")
        print(f"  CC: {email['cc_emails']}")
        print(f"  시간: {email['sent_at']}")
else:
    print("  없음")

conn.close()
