# -*- coding: utf-8 -*-
"""
최근 UNKNOWN으로 분류된 메시지 확인
"""
import sqlite3
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from services.project_tag_service import ProjectTagService

print("=" * 80)
print("최근 메시지 프로젝트 분류 테스트")
print("=" * 80)

# VDOS DB에서 최근 이메일 가져오기
vdos_conn = sqlite3.connect('../virtualoffice/src/virtualoffice/vdos.db')
vdos_cur = vdos_conn.cursor()

# 최근 20개 이메일
vdos_cur.execute('''
    SELECT e.id, e.sender, e.subject, e.body, e.sent_at
    FROM emails e
    ORDER BY e.id DESC
    LIMIT 20
''')

recent_emails = vdos_cur.fetchall()
vdos_conn.close()

print(f"\n📧 최근 이메일 {len(recent_emails)}개 분석\n")

# ProjectTagService 초기화
tag_service = ProjectTagService()

unknown_count = 0
classified_count = 0

for email_id, sender, subject, body, sent_at in recent_emails:
    # 메시지 형식으로 변환
    message = {
        'id': f'email_{email_id}',
        'sender': sender,
        'sender_email': sender,
        'subject': subject,
        'content': body,
        'timestamp': sent_at
    }
    
    # 프로젝트 분류 (캐시 무시)
    project_code = tag_service.extract_project_from_message(message, use_cache=False)
    
    if project_code and project_code != 'UNKNOWN':
        classified_count += 1
        print(f"✅ [{project_code}] {subject[:50]}...")
    else:
        unknown_count += 1
        print(f"\n❌ [UNKNOWN] Email ID: {email_id}")
        print(f"   발신자: {sender}")
        print(f"   제목: {subject}")
        print(f"   내용 (처음 200자): {body[:200]}...")
        print(f"   시간: {sent_at}")
        
        # 발신자가 참여한 프로젝트 확인
        if sender in tag_service.person_project_mapping:
            projects = tag_service.person_project_mapping[sender]
            print(f"   발신자 참여 프로젝트: {projects}")
        else:
            print(f"   발신자 참여 프로젝트: 없음")

print(f"\n{'='*80}")
print(f"분석 결과:")
print(f"  - 분류 성공: {classified_count}개")
print(f"  - UNKNOWN: {unknown_count}개")
print(f"  - 성공률: {classified_count / len(recent_emails) * 100:.1f}%")
print("="*80)
