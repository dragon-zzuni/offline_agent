#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
발신자 필드 형식 확인 스크립트
"""

import json
import sys
import os

# 프로젝트 루트를 sys.path에 추가
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 데이터 파일 경로
DATA_DIR = os.path.join(project_root, "data", "multi_project_8week_ko")
EMAIL_FILE = os.path.join(DATA_DIR, "email_communications.json")
CHAT_FILE = os.path.join(DATA_DIR, "chat_communications.json")
PERSONAS_FILE = os.path.join(DATA_DIR, "team_personas.json")

def check_sender_formats():
    """발신자 필드 형식 확인"""
    
    print("=" * 80)
    print("📧 이메일 발신자 형식 확인")
    print("=" * 80)
    
    if os.path.exists(EMAIL_FILE):
        with open(EMAIL_FILE, 'r', encoding='utf-8') as f:
            emails = json.load(f)
        
        senders = set()
        for email in emails[:10]:  # 처음 10개만
            sender = email.get('sender', 'N/A')
            senders.add(sender)
            print(f"Sender: {sender}")
        
        print(f"\n고유 발신자 (처음 10개 메시지): {senders}")
    
    print("\n" + "=" * 80)
    print("💬 채팅 발신자 형식 확인")
    print("=" * 80)
    
    if os.path.exists(CHAT_FILE):
        with open(CHAT_FILE, 'r', encoding='utf-8') as f:
            chats = json.load(f)
        
        senders = set()
        for chat in chats[:10]:  # 처음 10개만
            sender = chat.get('sender', 'N/A')
            senders.add(sender)
            print(f"Sender: {sender}")
        
        print(f"\n고유 발신자 (처음 10개 메시지): {senders}")
    
    print("\n" + "=" * 80)
    print("👤 페르소나 정보")
    print("=" * 80)
    
    if os.path.exists(PERSONAS_FILE):
        with open(PERSONAS_FILE, 'r', encoding='utf-8') as f:
            personas = json.load(f)
        
        for persona in personas:
            name = persona.get('name', 'N/A')
            email = persona.get('email', 'N/A')
            chat_handle = persona.get('chat_handle', 'N/A')
            print(f"이름: {name}")
            print(f"  - 이메일: {email}")
            print(f"  - 채팅 핸들: {chat_handle}")
            print()

if __name__ == "__main__":
    check_sender_formats()
