#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LLM 응답 디버깅"""
import sys
import os
sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('src'))

from dotenv import load_dotenv
load_dotenv()

# VDOS .env도 로드
vdos_env = os.path.join(os.path.dirname(__file__), '../virtualoffice/.env')
if os.path.exists(vdos_env):
    load_dotenv(vdos_env)
    print(f"✅ VDOS .env 로드: {vdos_env}")

def test_llm_response():
    """LLM 응답 디버깅"""
    print("=" * 60)
    print("LLM 응답 디버깅")
    print("=" * 60)
    
    try:
        from src.services.project_tag_service import ProjectTagService
        
        service = ProjectTagService()
        print(f"✅ ProjectTagService 생성 성공")
        print(f"📋 로드된 프로젝트: {list(service.project_tags.keys())}")
        
        # 테스트 메시지
        test_message = {
            "content": "API 리팩토링 작업을 진행하겠습니다.",
            "sender": "yongjun_kim",
            "subject": "API 리팩토링"
        }
        
        print(f"\n--- 테스트 메시지 ---")
        print(f"제목: {test_message['subject']}")
        print(f"내용: {test_message['content']}")
        
        # 프로젝트 컨텍스트 확인
        context = service._build_project_context()
        print(f"\n--- 프로젝트 컨텍스트 ---")
        print(context[:500])
        print("...")
        
        # LLM 호출
        print(f"\n--- LLM 호출 ---")
        response = service._call_existing_llm_service(test_message)
        print(f"LLM 응답: '{response}'")
        print(f"응답 타입: {type(response)}")
        
        if response:
            print(f"응답 길이: {len(response)}")
            print(f"응답 (upper): '{response.strip().upper()}'")
            print(f"프로젝트 태그에 존재? {response.strip().upper() in service.project_tags}")
        
        # 최종 분류 결과
        print(f"\n--- 최종 분류 ---")
        project = service.extract_project_from_message(test_message, use_cache=False)
        print(f"분류 결과: {project}")
        
        return True
        
    except Exception as e:
        print(f"❌ 테스트 실패: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_llm_response()
