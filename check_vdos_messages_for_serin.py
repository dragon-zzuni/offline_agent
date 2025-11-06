# -*- coding: utf-8 -*-
"""
VDOS DB에서 김세린이 받은 메시지 확인

실제 원본 메시지에 프로젝트 정보가 있는지 확인합니다.
"""
import sqlite3
import os


def check_vdos_messages():
    """VDOS DB에서 김세린 메시지 확인"""
    vdos_db_path = "virtualoffice/src/virtualoffice/vdos.db"
    
    if not os.path.exists(vdos_db_path):
        print(f"❌ VDOS DB를 찾을 수 없습니다")
        return
    
    conn = sqlite3.connect(vdos_db_path)
    cursor = conn.cursor()
    
    print("=" * 80)
    print("김세린이 받은 메시지 분석 (VDOS DB)")
    print("=" * 80)
    
    # 김세린의 이메일 주소 확인
    cursor.execute("""
        SELECT id, name, email_address, chat_handle
        FROM people
        WHERE name LIKE '%세린%' OR email_address LIKE '%serin%'
    """)
    
    personas = cursor.fetchall()
    print(f"\n👤 김세린 페르소나:")
    for row in personas:
        persona_id, name, email, handle = row
        print(f"  - ID: {persona_id}, 이름: {name}, 이메일: {email}, 핸들: {handle}")
    
    if not personas:
        print("  ❌ 김세린 페르소나를 찾을 수 없습니다")
        conn.close()
        return
    
    # 첫 번째 페르소나 사용
    persona_id, persona_name, persona_email, persona_handle = personas[0]
    
    # 김세린이 받은 최근 이메일 5개
    print(f"\n📧 {persona_name}이 받은 최근 이메일 (5개):")
    cursor.execute("""
        SELECT e.id, e.sender, e.subject, e.body
        FROM emails e
        INNER JOIN email_recipients er ON e.id = er.email_id
        WHERE er.address = ?
        ORDER BY e.id DESC
        LIMIT 5
    """, (persona_email,))
    
    for i, row in enumerate(cursor.fetchall(), 1):
        email_id, sender, subject, body = row
        print(f"\n{'='*80}")
        print(f"이메일 #{i} (ID: {email_id})")
        print(f"{'='*80}")
        print(f"발신자: {sender}")
        print(f"제목: {subject}")
        print(f"본문 (처음 500자):")
        print(f"{body[:500] if body else '(없음)'}...")
        
        # 프로젝트 키워드 찾기
        keywords = ['프로젝트', 'project', 'PV', 'PS', 'HA', 'CB', 'WL', 'VC', 
                   'ProjectVertex', 'ProjectSphere', 'HealthAssist', 'CareBridge', 
                   'WellLink', 'VitalCare']
        found_keywords = []
        full_text = f"{subject} {body}".lower() if body else subject.lower()
        for kw in keywords:
            if kw.lower() in full_text:
                found_keywords.append(kw)
        
        if found_keywords:
            print(f"\n🔍 발견된 키워드: {', '.join(found_keywords)}")
        else:
            print(f"\n⚠️ 프로젝트 키워드 없음")
    
    # 김세린이 받은 최근 채팅 메시지 5개
    print(f"\n\n💬 {persona_name}이 받은 최근 채팅 메시지 (5개):")
    cursor.execute("""
        SELECT id, sender_handle, content
        FROM chat_messages
        WHERE recipient_handle = ?
        ORDER BY id DESC
        LIMIT 5
    """, (persona_handle,))
    
    for i, row in enumerate(cursor.fetchall(), 1):
        msg_id, sender, content = row
        print(f"\n{'='*80}")
        print(f"메시지 #{i} (ID: {msg_id})")
        print(f"{'='*80}")
        print(f"발신자: {sender}")
        print(f"내용 (처음 500자):")
        print(f"{content[:500] if content else '(없음)'}...")
        
        # 프로젝트 키워드 찾기
        found_keywords = []
        if content:
            for kw in keywords:
                if kw.lower() in content.lower():
                    found_keywords.append(kw)
        
        if found_keywords:
            print(f"\n🔍 발견된 키워드: {', '.join(found_keywords)}")
        else:
            print(f"\n⚠️ 프로젝트 키워드 없음")
    
    conn.close()
    print("\n" + "=" * 80)


if __name__ == "__main__":
    check_vdos_messages()
