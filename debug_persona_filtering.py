#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
페르소나 필터링 디버깅
"""
import sys
import os
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from utils.vdos_connector import get_vdos_connector

def debug_persona_filtering():
    """페르소나 필터링 디버깅"""
    
    print("🔍 페르소나 필터링 디버깅")
    print("=" * 60)
    
    connector = get_vdos_connector()
    
    if not connector.is_available:
        print("❌ VDOS 데이터베이스에 연결할 수 없습니다.")
        return
    
    # 테스트할 페르소나
    test_persona = {
        "name": "김용준",
        "email": "yongjun.kim@company.com",
        "handle": "yongjun_kim"
    }
    
    print(f"👤 테스트 페르소나: {test_persona['name']}")
    print(f"   이메일: {test_persona['email']}")
    print(f"   핸들: {test_persona['handle']}")
    print()
    
    # 1. 전체 이메일 확인
    all_emails = connector.get_recent_emails(limit=1000)
    print(f"📧 전체 이메일: {len(all_emails)}개")
    
    # 김용준 관련 이메일 필터링
    persona_emails = []
    for email in all_emails:
        sender = email.get('sender', '')
        recipients = email.get('recipients_list', [])
        
        # 발신자이거나 수신자인 이메일
        if (sender == test_persona['email'] or 
            test_persona['email'] in recipients):
            persona_emails.append(email)
    
    print(f"📧 {test_persona['name']} 관련 이메일: {len(persona_emails)}개")
    
    if persona_emails:
        print("📧 이메일 샘플:")
        for i, email in enumerate(persona_emails[:5]):
            subject = email.get('subject', 'N/A')[:40]
            sender = email.get('sender', 'N/A')
            recipients = email.get('recipients_list', [])
            print(f"  {i+1}. [{sender}] → {recipients}")
            print(f"      제목: {subject}...")
    
    print()
    
    # 2. 전체 채팅 확인
    all_chats = connector.get_recent_chat_messages(limit=1000)
    print(f"💬 전체 채팅: {len(all_chats)}개")
    
    # 김용준 관련 채팅 필터링
    persona_chats = []
    for msg in all_chats:
        sender = msg.get('sender', '')
        room_name = msg.get('room_name', '')
        
        # 발신자이거나 방 이름에 포함된 메시지
        if (sender == test_persona['handle'] or 
            test_persona['handle'] in room_name):
            persona_chats.append(msg)
    
    print(f"💬 {test_persona['name']} 관련 채팅: {len(persona_chats)}개")
    
    if persona_chats:
        print("💬 채팅 샘플:")
        for i, msg in enumerate(persona_chats[:5]):
            body = msg.get('body', 'N/A')[:40]
            sender = msg.get('sender', 'N/A')
            room = msg.get('room_name', 'N/A')
            print(f"  {i+1}. [{sender}] @ {room}")
            print(f"      내용: {body}...")
    
    print()
    
    # 3. 총합
    total_messages = len(persona_emails) + len(persona_chats)
    print(f"📊 {test_persona['name']} 총 메시지: {total_messages}개")
    
    if total_messages == 0:
        print(f"✅ 정상: {test_persona['name']}은 메시지가 없는 비활성 페르소나입니다.")
        print(f"⚠️ 하지만 로그에서는 17개 메시지가 수집되었다고 나왔습니다!")
        print(f"   → 페르소나 필터링이 제대로 작동하지 않고 있습니다.")
    else:
        print(f"⚠️ {test_persona['name']}에게 {total_messages}개의 메시지가 있습니다.")
    
    print()
    print("=" * 60)
    
    # 4. VirtualOffice API 시뮬레이션
    print("🔧 VirtualOffice API 시뮬레이션")
    print("=" * 60)
    
    # VirtualOfficeClient가 어떻게 메시지를 가져오는지 시뮬레이션
    print(f"API 호출: GET /mailboxes/{test_persona['email']}/emails")
    print(f"API 호출: GET /chat/messages?handle={test_persona['handle']}")
    print()
    
    # 실제로 VirtualOffice API가 반환하는 데이터 확인
    # (이 부분은 실제 API 호출이 필요)
    print("⚠️ 실제 API 응답을 확인하려면 VirtualOffice 서버가 실행 중이어야 합니다.")
    print("   서버가 실행 중이라면, 다음 명령으로 확인할 수 있습니다:")
    print(f"   curl http://127.0.0.1:8000/mailboxes/{test_persona['email']}/emails")
    print(f"   curl http://127.0.0.1:8001/chat/messages?handle={test_persona['handle']}")

if __name__ == "__main__":
    debug_persona_filtering()
