# -*- coding: utf-8 -*-
"""
정보 공유 필터링으로 제외된 메시지 분석 및 DB 저장
"""
import sqlite3
import json
from pathlib import Path
from datetime import datetime

# VDOS DB 경로
VDOS_DB = Path("virtualoffice/src/virtualoffice/vdos.db")
OUTPUT_DB = Path("virtualoffice/src/virtualoffice/filtered_todos_analysis.db")

def init_output_db(conn):
    """출력 DB 초기화"""
    cursor = conn.cursor()
    
    # 필터링된 메시지 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS filtered_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            msg_type TEXT NOT NULL,
            sender TEXT,
            subject TEXT,
            body TEXT,
            sent_at TEXT,
            is_info_sharing INTEGER DEFAULT 0,
            has_request INTEGER DEFAULT 0,
            matched_info_keywords TEXT,
            matched_request_keywords TEXT,
            should_analyze INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 통계 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS analysis_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            total_messages INTEGER,
            filtered_count INTEGER,
            filtered_with_requests INTEGER,
            potential_todo_loss INTEGER,
            analysis_date TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()

def analyze_filtered_messages():
    """정보 공유 필터링으로 제외된 메시지 분석"""
    
    if not VDOS_DB.exists():
        print(f"❌ VDOS DB를 찾을 수 없습니다: {VDOS_DB}")
        return
    
    # VDOS DB 연결
    vdos_conn = sqlite3.connect(VDOS_DB)
    vdos_conn.row_factory = sqlite3.Row
    vdos_cursor = vdos_conn.cursor()
    
    # 출력 DB 연결
    output_conn = sqlite3.connect(OUTPUT_DB)
    init_output_db(output_conn)
    output_cursor = output_conn.cursor()
    
    # 기존 데이터 삭제
    output_cursor.execute("DELETE FROM filtered_messages")
    output_cursor.execute("DELETE FROM analysis_stats")
    output_conn.commit()
    
    print(f"\n📊 VDOS DB 분석 시작: {VDOS_DB}")
    print(f"📁 결과 저장 위치: {OUTPUT_DB}")
    
    # PM (이정두) 이 받은 이메일 조회
    vdos_cursor.execute("""
        SELECT DISTINCT e.id, e.sender, e.subject, e.body, e.sent_at, e.thread_id,
               er.kind as recipient_type
        FROM emails e
        JOIN email_recipients er ON e.id = er.email_id
        WHERE er.address = 'leejungdu@example.com'
        ORDER BY e.sent_at DESC
    """)
    emails = vdos_cursor.fetchall()
    
    # PM (이정두) 이 참여한 채팅 조회
    vdos_cursor.execute("""
        SELECT cm.id, cm.sender, cm.body, cm.sent_at, cr.slug as room_slug
        FROM chat_messages cm
        JOIN chat_rooms cr ON cm.room_id = cr.id
        JOIN chat_members cmem ON cr.id = cmem.room_id
        WHERE cmem.handle = 'leejungdu'
        ORDER BY cm.sent_at DESC
    """)
    chats = vdos_cursor.fetchall()
    
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
    
    # 요청 키워드 (TODO가 될 가능성) - 구체적인 요청만
    request_keywords = [
        "부탁드립니다", "부탁드려요", "요청드립니다", "요청드려요",
        "확인 부탁", "검토 부탁", "피드백 부탁", "리뷰 부탁",
        "참석 부탁", "참석해 주세요", "참석 요청",
        "제출 부탁", "제출해 주세요", "제출 요청",
        "승인 부탁", "승인 요청", "결재 부탁", "결재 요청",
        "준비 부탁", "준비해 주세요", "작성 부탁", "작성해 주세요",
        "수정 부탁", "수정해 주세요", "변경 부탁", "변경해 주세요",
        "please review", "please check", "please attend", "please submit",
        "need your", "require your", "request your"
    ]
    
    # 제외할 형식적 표현 (요청이 아님)
    formal_expressions = [
        "필요하시면", "궁금하시면", "언제든", "편하신 시간",
        "if you need", "if you want", "anytime", "feel free"
    ]
    
    # 필터링 분석 - 이메일
    filtered_count = 0
    filtered_with_requests = 0
    
    for email in emails:
        subject = (email['subject'] or "").lower()
        body = (email['body'] or "").lower()
        combined = f"{subject} {body}"
        
        # 정보 공유 패턴 체크
        matched_info = [k for k in info_sharing_keywords if k in combined]
        is_info_sharing = len(matched_info) > 0
        
        # 요청 키워드 체크
        matched_req = [k for k in request_keywords if k in combined]
        has_request = len(matched_req) > 0
        
        # 형식적 표현만 있으면 요청이 아님
        has_formal_only = any(expr in combined for expr in formal_expressions)
        if has_formal_only and not has_request:
            has_request = False
        
        # 정보 공유 메시지만 저장
        if is_info_sharing:
            filtered_count += 1
            should_analyze = 1 if has_request else 0
            
            if has_request:
                filtered_with_requests += 1
            
            output_cursor.execute("""
                INSERT INTO filtered_messages 
                (msg_type, sender, subject, body, sent_at, is_info_sharing, has_request,
                 matched_info_keywords, matched_request_keywords, should_analyze)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                'email',
                email['sender'],
                email['subject'],
                email['body'],
                email['sent_at'],
                1,
                1 if has_request else 0,
                json.dumps(matched_info[:5], ensure_ascii=False),
                json.dumps(matched_req[:5], ensure_ascii=False),
                should_analyze
            ))
    
    # 필터링 분석 - 채팅
    for chat in chats:
        body = (chat['body'] or "").lower()
        
        # 정보 공유 패턴 체크
        matched_info = [k for k in info_sharing_keywords if k in body]
        is_info_sharing = len(matched_info) > 0
        
        # 요청 키워드 체크
        matched_req = [k for k in request_keywords if k in body]
        has_request = len(matched_req) > 0
        
        # 정보 공유 메시지만 저장
        if is_info_sharing:
            filtered_count += 1
            should_analyze = 1 if has_request else 0
            
            if has_request:
                filtered_with_requests += 1
            
            output_cursor.execute("""
                INSERT INTO filtered_messages 
                (msg_type, sender, subject, body, sent_at, is_info_sharing, has_request,
                 matched_info_keywords, matched_request_keywords, should_analyze)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                'chat',
                chat['sender'],
                chat.get('room_slug', ''),
                chat['body'],
                chat['sent_at'],
                1,
                1 if has_request else 0,
                json.dumps(matched_info[:5], ensure_ascii=False),
                json.dumps(matched_req[:5], ensure_ascii=False),
                should_analyze
            ))
    
    # 통계 저장
    total_messages = len(emails) + len(chats)
    output_cursor.execute("""
        INSERT INTO analysis_stats 
        (total_messages, filtered_count, filtered_with_requests, potential_todo_loss)
        VALUES (?, ?, ?, ?)
    """, (total_messages, filtered_count, filtered_with_requests, filtered_with_requests))
    
    output_conn.commit()
    
    print(f"\n🔍 정보 공유로 필터링된 메시지: {filtered_count}개")
    print(f"⚠️  그 중 요청 키워드 포함 (TODO 누락 가능성): {filtered_with_requests}개")
    
    # 상세 결과 출력
    if filtered_with_requests > 0:
        print(f"\n{'='*80}")
        print(f"⚠️  정보 공유 + 요청 키워드 메시지 (TODO 누락 가능성)")
        print(f"{'='*80}\n")
        
        output_cursor.execute("""
            SELECT msg_type, sender, subject, body, sent_at,
                   matched_info_keywords, matched_request_keywords
            FROM filtered_messages
            WHERE should_analyze = 1
            ORDER BY sent_at DESC
            LIMIT 20
        """)
        
        results = output_cursor.fetchall()
        for i, row in enumerate(results, 1):
            msg_type, sender, subject, body, sent_at, info_kw, req_kw = row
            
            print(f"\n[{i}] {msg_type.upper()} | {sender} | {sent_at[:10]}")
            if subject:
                print(f"제목: {subject}")
            print(f"내용 (앞 300자):")
            print(f"{body[:300]}...")
            
            info_list = json.loads(info_kw)
            req_list = json.loads(req_kw)
            
            print(f"📌 정보공유 키워드: {', '.join(info_list)}")
            print(f"🎯 요청 키워드: {', '.join(req_list)}")
            print(f"{'-'*80}")
    
    # 통계 출력
    print(f"\n{'='*80}")
    print(f"📊 필터링 통계")
    print(f"{'='*80}")
    print(f"전체 메시지: {total_messages}개")
    if total_messages > 0:
        print(f"정보 공유 필터링: {filtered_count}개 ({filtered_count/total_messages*100:.1f}%)")
        if filtered_count > 0:
            print(f"필터링 중 요청 포함: {filtered_with_requests}개 ({filtered_with_requests/filtered_count*100:.1f}% of filtered)")
    print(f"\n⚠️  잠재적 TODO 누락: {filtered_with_requests}개 메시지")
    
    if filtered_with_requests > 0:
        print(f"\n💡 권장 사항:")
        print(f"   정보 공유 필터링 로직을 개선하여 요청 키워드가 있는 메시지는")
        print(f"   LLM 분석에 포함시키는 것이 좋습니다.")
        print(f"\n✅ 개선 완료: analysis_pipeline_service.py에 이미 적용됨")
    
    print(f"\n✅ 분석 결과 저장 완료: {OUTPUT_DB}")
    print(f"\n📋 DB 조회 방법:")
    print(f"   sqlite3 {OUTPUT_DB}")
    print(f"   SELECT * FROM filtered_messages WHERE should_analyze = 1;")
    print(f"   SELECT * FROM analysis_stats;")
    
    # 연결 종료
    vdos_conn.close()
    output_conn.close()

if __name__ == "__main__":
    analyze_filtered_messages()
