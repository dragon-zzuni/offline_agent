# -*- coding: utf-8 -*-
"""
TODO 추출 디버깅 스크립트

ActionExtractor가 실제로 어떻게 작동하는지 확인합니다.
"""
import sys
import os
import asyncio

# 경로 설정
offline_agent_root = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(offline_agent_root, "src"))

from nlp.action_extractor import ActionExtractor
import sqlite3


def get_sample_messages():
    """VDOS DB에서 샘플 메시지 가져오기"""
    db_path = "virtualoffice/src/virtualoffice/vdos.db"
    
    if not os.path.exists(db_path):
        print(f"❌ DB 파일을 찾을 수 없습니다: {db_path}")
        return []
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 이정두가 받은 최근 이메일 10개
    cursor.execute("""
        SELECT 
            id,
            sender,
            subject,
            body,
            to_recipients
        FROM emails
        WHERE to_recipients LIKE '%leejungdu@example.com%'
        ORDER BY id DESC
        LIMIT 10
    """)
    
    emails = []
    for row in cursor.fetchall():
        email_id, sender, subject, body, recipients = row
        emails.append({
            "msg_id": f"email_{email_id}",
            "sender": sender,
            "sender_email": sender,
            "subject": subject,
            "body": body,
            "content": body,
            "type": "email"
        })
    
    conn.close()
    return emails


async def test_extraction():
    """추출 테스트"""
    print("=" * 80)
    print("TODO 추출 디버깅")
    print("=" * 80)
    
    # 샘플 메시지 가져오기
    messages = get_sample_messages()
    
    if not messages:
        print("❌ 샘플 메시지를 가져올 수 없습니다.")
        return
    
    print(f"\n📨 샘플 메시지: {len(messages)}개\n")
    
    # ActionExtractor 초기화
    extractor = ActionExtractor()
    
    # 각 메시지별로 추출 테스트
    total_actions = 0
    
    for i, message in enumerate(messages, 1):
        print(f"\n{'='*80}")
        print(f"메시지 #{i}")
        print(f"{'='*80}")
        print(f"발신자: {message.get('sender')}")
        print(f"제목: {message.get('subject')}")
        print(f"본문 (처음 200자):")
        print(f"{message.get('body', '')[:200]}...")
        print()
        
        # 추출 (user_email 없이 - 모든 메시지 처리)
        actions = extractor.extract_actions(message, user_email=None)
        
        if actions:
            print(f"✅ {len(actions)}개의 액션 추출됨:")
            for j, action in enumerate(actions, 1):
                print(f"\n  액션 #{j}:")
                print(f"    타입: {action.action_type}")
                print(f"    제목: {action.title}")
                print(f"    설명: {action.description[:100]}...")
                print(f"    우선순위: {action.priority}")
                print(f"    요청자: {action.requester}")
            total_actions += len(actions)
        else:
            print("❌ 액션 추출 실패")
            
            # 디버깅: 키워드 체크
            text = f"{message.get('subject', '')} {message.get('body', '')}".lower()
            print("\n  🔍 키워드 체크:")
            
            keywords_found = []
            for action_type, config in extractor.action_patterns.items():
                for keyword in config["keywords"]:
                    if keyword in text:
                        keywords_found.append(f"{action_type}: {keyword}")
            
            if keywords_found:
                print(f"    발견된 키워드: {', '.join(keywords_found)}")
                print("    ⚠️ 키워드는 있지만 액션이 생성되지 않음!")
            else:
                print("    키워드 없음")
    
    print(f"\n{'='*80}")
    print(f"총 추출된 액션: {total_actions}개")
    print(f"추출률: {total_actions / len(messages) * 100:.1f}%")
    print(f"{'='*80}")


if __name__ == "__main__":
    asyncio.run(test_extraction())
