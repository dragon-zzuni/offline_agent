# -*- coding: utf-8 -*-
"""
정보 공유 필터링 분석 - VDOS DB에서 직접 읽기
"""
import sqlite3
import json
from pathlib import Path

# VDOS DB 경로
VDOS_DB = Path("virtualoffice/src/virtualoffice/vdos.db")

def analyze_filtered_messages():
    """정보 공유 필터링으로 제외된 메시지 분석"""
    
    if not VDOS_DB.exists():
        print(f"❌ VDOS DB를 찾을 수 없습니다: {VDOS_DB}")
        return
    
    conn = sqlite3.connect(VDOS_DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # PM이 받은 이메일 조회
    cursor.execute("""
        SELECT DISTINCT e.id, e.sender, e.subject, e.body, e.sent_at, e.thread_id
        FROM emails e
        JOIN email_recipients er ON e.id = er.email_id
        WHERE er.address = 'pm.1@quickchat.dev'
        ORDER BY e.sent_at DESC
    """)
    emails = cursor.fetchall()
    
    # PM이 받은 채팅 조회
    cursor.execute("""
        SELECT cm.id, cm.sender, cm.body, cm.sent_at, cr.slug as room_slug
        FROM chat_messages cm
        JOIN chat_rooms cr ON cm.room_id = cr.id
        JOIN chat_members cmem ON cr.id = cmem.room_id
        WHERE cmem.handle = 'pm'
        ORDER BY cm.sent_at DESC
    """)
    chats = cursor.fetchall()
    
    conn.close()
    
    print(f"\n📊 전체 메시지")
    print(f"  이메일: {len(emails)}개")
    print(f"  채팅: {len(chats)}개")
    print(f"  합계: {len(emails) + len(chats)}개")
    
    # 정보 공유 키워드
    info_sharing_keywords = [
        "오늘의 일정", "오늘의 계획", "오늘의 주요", "오늘의 목표",
        "일정을 공유", "계획을 공유", "일정에 따라", "계획에 따라",
        "다음과 같이 진행", "아래와 같이 진행", "다음과 같이 업무",
        "현재 집중 작업", "현재 작업", "진행 상황 공유",
        "작업 계획", "업무 계획", "일정 정리", "계획 정리",
        "공유드립니다", "안내드립니다", "업데이트드립니다"
    ]
    
    # 요청 키워드 (TODO가 될 가능성)
    request_keywords = [
        "부탁", "주세요", "요청", "확인", "검토", "피드백",
        "참석", "회의", "미팅", "제출", "승인", "결재",
        "준비", "작성", "수정", "변경", "추가", "삭제",
        "please", "check", "review", "attend", "submit"
    ]
    
    # 필터링 분석
    filtered_emails = []
    filtered_with_requests_emails = []
    
    for email in emails:
        subject = (email['subject'] or "").lower()
        body = (email['body'] or "").lower()
        combined = f"{subject} {body}"
        
        # 정보 공유 패턴 체크
        is_info_sharing = any(keyword in combined for keyword in info_sharing_keywords)
        
        if is_info_sharing:
            filtered_emails.append(email)
            
            # 요청 키워드도 있는지 체크
            has_request = any(keyword in combined for keyword in request_keywords)
            if has_request:
                filtered_with_requests_emails.append(email)
    
    filtered_chats = []
    filtered_with_requests_chats = []
    
    for chat in chats:
        body = (chat['body'] or "").lower()
        
        # 정보 공유 패턴 체크
        is_info_sharing = any(keyword in body for keyword in info_sharing_keywords)
        
        if is_info_sharing:
            filtered_chats.append(chat)
            
            # 요청 키워드도 있는지 체크
            has_request = any(keyword in body for keyword in request_keywords)
            if has_request:
                filtered_with_requests_chats.append(chat)
    
    total_filtered = len(filtered_emails) + len(filtered_chats)
    total_with_requests = len(filtered_with_requests_emails) + len(filtered_with_requests_chats)
    
    print(f"\n🔍 정보 공유로 필터링된 메시지")
    print(f"  이메일: {len(filtered_emails)}개")
    print(f"  채팅: {len(filtered_chats)}개")
    print(f"  합계: {total_filtered}개")
    
    print(f"\n⚠️  그 중 요청 키워드 포함 (TODO 누락 가능성)")
    print(f"  이메일: {len(filtered_with_requests_emails)}개")
    print(f"  채팅: {len(filtered_with_requests_chats)}개")
    print(f"  합계: {total_with_requests}개")
    
    # 요청 키워드가 있는 필터링된 메시지 상세 분석
    if total_with_requests > 0:
        print(f"\n{'='*80}")
        print(f"⚠️  정보 공유 + 요청 키워드 메시지 분석 (TODO 누락 가능성)")
        print(f"{'='*80}\n")
        
        # 이메일 분석
        for i, email in enumerate(filtered_with_requests_emails[:10], 1):
            sender = email['sender']
            subject = email['subject'] or ""
            body = email['body'] or ""
            date = email['sent_at'][:10]
            
            print(f"\n[{i}] EMAIL | {sender} | {date}")
            if subject:
                print(f"제목: {subject}")
            print(f"내용 (앞 300자):")
            print(f"{body[:300]}...")
            
            # 어떤 키워드가 매칭되었는지 표시
            combined = f"{subject} {body}".lower()
            matched_info = [k for k in info_sharing_keywords if k in combined]
            matched_req = [k for k in request_keywords if k in combined]
            
            print(f"📌 정보공유 키워드: {', '.join(matched_info[:3])}")
            print(f"🎯 요청 키워드: {', '.join(matched_req[:5])}")
            print(f"{'-'*80}")
        
        # 채팅 분석
        for i, chat in enumerate(filtered_with_requests_chats[:10], len(filtered_with_requests_emails)+1):
            sender = chat['sender']
            body = chat['body'] or ""
            date = chat['sent_at'][:10]
            room = chat['room_slug']
            
            print(f"\n[{i}] CHAT | {sender} | {room} | {date}")
            print(f"내용 (앞 300자):")
            print(f"{body[:300]}...")
            
            # 어떤 키워드가 매칭되었는지 표시
            matched_info = [k for k in info_sharing_keywords if k in body.lower()]
            matched_req = [k for k in request_keywords if k in body.lower()]
            
            print(f"📌 정보공유 키워드: {', '.join(matched_info[:3])}")
            print(f"🎯 요청 키워드: {', '.join(matched_req[:5])}")
            print(f"{'-'*80}")
    
    # 통계
    total_messages = len(emails) + len(chats)
    print(f"\n{'='*80}")
    print(f"📊 필터링 통계")
    print(f"{'='*80}")
    print(f"전체 메시지: {total_messages}개")
    print(f"정보 공유 필터링: {total_filtered}개 ({total_filtered/total_messages*100:.1f}%)")
    print(f"필터링 중 요청 포함: {total_with_requests}개 ({total_with_requests/total_filtered*100:.1f}% of filtered)")
    print(f"\n⚠️  잠재적 TODO 누락: {total_with_requests}개 메시지")
    
    if total_with_requests > 0:
        print(f"\n💡 권장 사항:")
        print(f"   정보 공유 필터링 로직을 개선하여 요청 키워드가 있는 메시지는")
        print(f"   LLM 분석에 포함시키는 것이 좋습니다.")

if __name__ == "__main__":
    analyze_filtered_messages()
