# -*- coding: utf-8 -*-
"""
정보 공유 필터링으로 제외된 메시지 분석
"""
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from main import SmartAssistant

async def analyze_filtered_messages():
    """정보 공유 필터링으로 제외된 메시지 분석"""
    
    # SmartAssistant 초기화 (VirtualOffice 연동)
    assistant = SmartAssistant()
    
    # VirtualOffice 데이터 소스 설정
    from data_sources.virtualoffice_source import VirtualOfficeDataSource
    from integrations.virtualoffice_client import VirtualOfficeClient
    from integrations.models import PersonaInfo
    
    # VirtualOffice 클라이언트 생성
    client = VirtualOfficeClient(base_url="http://localhost:8015")
    
    # 페르소나 선택 (PM)
    persona = PersonaInfo(
        mailbox="pm.1@quickchat.dev",
        handle="pm",
        name="PM 1"
    )
    
    vdos_source = VirtualOfficeDataSource(client=client, selected_persona=persona)
    assistant.data_source_manager.set_source(vdos_source)
    
    await assistant.initialize()
    
    # 메시지 수집
    messages = await assistant.collect_messages()
    
    print(f"\n📊 전체 메시지: {len(messages)}개")
    
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
    
    # 필터링된 메시지 분석
    filtered_messages = []
    filtered_with_requests = []
    
    for msg in messages:
        content = (msg.get("content") or msg.get("body") or "").lower()
        subject = (msg.get("subject") or "").lower()
        combined = f"{subject} {content}"
        
        # 정보 공유 패턴 체크
        is_info_sharing = any(keyword in combined for keyword in info_sharing_keywords)
        
        if is_info_sharing:
            filtered_messages.append(msg)
            
            # 요청 키워드도 있는지 체크
            has_request = any(keyword in combined for keyword in request_keywords)
            if has_request:
                filtered_with_requests.append(msg)
    
    print(f"🔍 정보 공유로 필터링된 메시지: {len(filtered_messages)}개")
    print(f"⚠️  그 중 요청 키워드 포함: {len(filtered_with_requests)}개")
    
    # 요청 키워드가 있는 필터링된 메시지 상세 분석
    if filtered_with_requests:
        print(f"\n{'='*80}")
        print(f"⚠️  정보 공유 + 요청 키워드 메시지 분석 (TODO 누락 가능성)")
        print(f"{'='*80}\n")
        
        for i, msg in enumerate(filtered_with_requests[:20], 1):  # 최대 20개만
            sender = msg.get("sender", "Unknown")
            subject = msg.get("subject", "")
            content = msg.get("content") or msg.get("body") or ""
            msg_type = msg.get("type", "unknown")
            date = msg.get("date", "")
            
            print(f"\n[{i}] {msg_type.upper()} | {sender} | {date[:10]}")
            if subject:
                print(f"제목: {subject}")
            print(f"내용 (앞 300자):")
            print(f"{content[:300]}...")
            
            # 어떤 키워드가 매칭되었는지 표시
            matched_info = [k for k in info_sharing_keywords if k in f"{subject} {content}".lower()]
            matched_req = [k for k in request_keywords if k in f"{subject} {content}".lower()]
            
            print(f"📌 정보공유 키워드: {', '.join(matched_info[:3])}")
            print(f"🎯 요청 키워드: {', '.join(matched_req[:5])}")
            print(f"{'-'*80}")
    
    # 통계
    print(f"\n{'='*80}")
    print(f"📊 필터링 통계")
    print(f"{'='*80}")
    print(f"전체 메시지: {len(messages)}개")
    print(f"정보 공유 필터링: {len(filtered_messages)}개 ({len(filtered_messages)/len(messages)*100:.1f}%)")
    print(f"필터링 중 요청 포함: {len(filtered_with_requests)}개 ({len(filtered_with_requests)/len(filtered_messages)*100:.1f}%)")
    print(f"\n⚠️  잠재적 TODO 누락: {len(filtered_with_requests)}개 메시지")

if __name__ == "__main__":
    asyncio.run(analyze_filtered_messages())
