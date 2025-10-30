#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
이메일 TODO 누락 문제 디버깅 스크립트
"""
import sys
import os
import asyncio
import json
from pathlib import Path

# 프로젝트 루트 경로 설정
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from main import SmartAssistant

async def debug_email_todo_issue():
    """이메일 TODO 누락 문제 디버깅"""
    
    print("🔍 이메일 TODO 누락 문제 디버깅 시작")
    
    # SmartAssistant 초기화
    assistant = SmartAssistant()
    
    # 기본 데이터셋 설정
    dataset_config = {
        "dataset_root": "data/multi_project_8week_ko",
        "persona_name": "김민수"  # 기본 페르소나
    }
    
    try:
        # 1. 시스템 초기화
        print("📋 시스템 초기화 중...")
        await assistant.initialize(dataset_config)
        
        # 2. 메시지 수집
        print("📨 메시지 수집 중...")
        collect_options = {
            "email_limit": None,
            "messenger_limit": None,
            "overall_limit": None,
            "force_reload": True
        }
        
        messages = await assistant.collect_messages(**collect_options)
        print(f"✅ 메시지 수집 완료: 총 {len(messages)}개")
        
        # 3. 메시지 타입 분석
        email_count = len([m for m in messages if m.get("type") == "email" or m.get("platform") == "email"])
        messenger_count = len([m for m in messages if m.get("type") == "messenger" or m.get("platform") == "messenger"])
        other_count = len(messages) - email_count - messenger_count
        
        print(f"📊 메시지 타입 분석:")
        print(f"   - 이메일: {email_count}개")
        print(f"   - 메신저: {messenger_count}개")
        print(f"   - 기타: {other_count}개")
        
        # 4. 샘플 메시지 확인
        if messages:
            print(f"\n🔍 첫 번째 메시지 샘플:")
            sample = messages[0]
            print(f"   - type: {sample.get('type')}")
            print(f"   - platform: {sample.get('platform')}")
            print(f"   - sender: {sample.get('sender')}")
            print(f"   - subject: {sample.get('subject', 'N/A')[:50]}...")
        
        # 5. 분석 실행
        print(f"\n🔍 메시지 분석 시작...")
        analysis_results = await assistant.analyze_messages()
        print(f"✅ 분석 완료: {len(analysis_results)}개 결과")
        
        # 6. 분석 결과에서 이메일/메신저 비율 확인
        email_analysis_count = 0
        messenger_analysis_count = 0
        
        for result in analysis_results:
            message = result.get("message", {})
            msg_type = message.get("type") or message.get("platform")
            if msg_type == "email":
                email_analysis_count += 1
            elif msg_type == "messenger":
                messenger_analysis_count += 1
        
        print(f"📊 분석 결과 타입 분석:")
        print(f"   - 이메일 분석: {email_analysis_count}개")
        print(f"   - 메신저 분석: {messenger_analysis_count}개")
        
        # 7. TODO 생성
        print(f"\n📋 TODO 생성 시작...")
        todo_list = await assistant.generate_todo_list(analysis_results)
        
        # 8. TODO에서 이메일/메신저 비율 확인
        if isinstance(todo_list, dict):
            todos = []
            for todo_id, todo_data in todo_list.items():
                if isinstance(todo_data, dict):
                    todos.append(todo_data)
        elif isinstance(todo_list, list):
            todos = todo_list
        else:
            todos = []
        
        email_todo_count = 0
        messenger_todo_count = 0
        
        for todo in todos:
            source_type = todo.get("source_type", "")
            if "메일" in source_type:
                email_todo_count += 1
            elif "메시지" in source_type:
                messenger_todo_count += 1
        
        print(f"✅ TODO 생성 완료: 총 {len(todos)}개")
        print(f"📊 TODO 소스 타입 분석:")
        print(f"   - 이메일 기반 TODO: {email_todo_count}개")
        print(f"   - 메신저 기반 TODO: {messenger_todo_count}개")
        
        # 9. 결과 요약
        print(f"\n📈 결과 요약:")
        print(f"   수집: 이메일 {email_count}개, 메신저 {messenger_count}개")
        print(f"   분석: 이메일 {email_analysis_count}개, 메신저 {messenger_analysis_count}개")
        print(f"   TODO: 이메일 {email_todo_count}개, 메신저 {messenger_todo_count}개")
        
        # 10. 문제 진단
        if email_count > 0 and email_todo_count == 0:
            print(f"\n⚠️ 문제 발견: 이메일이 수집되었지만 TODO가 생성되지 않음")
            print(f"   - 가능한 원인: 이메일 우선순위가 낮아서 상위 50개에 포함되지 않음")
            print(f"   - 해결책: TOP_N 값을 늘리거나 이메일 우선순위 가중치 조정")
        elif email_analysis_count == 0 and email_count > 0:
            print(f"\n⚠️ 문제 발견: 이메일이 수집되었지만 분석되지 않음")
            print(f"   - 가능한 원인: 우선순위 랭킹에서 이메일이 제외됨")
        else:
            print(f"\n✅ 정상: 이메일과 메신저가 모두 TODO로 변환됨")
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_email_todo_issue())