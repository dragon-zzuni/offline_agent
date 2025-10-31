#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
프로젝트 분류 시스템 종합 디버깅 스크립트

1. VDOS DB에서 프로젝트 정보 로드 상태 확인
2. 사람-프로젝트 매핑 정보 확인
3. 명시적 프로젝트 추출 테스트
4. LLM 기반 프로젝트 분류 테스트
"""
import sys
import os
sys.path.append('.')
sys.path.append('src')

import sqlite3
import json
from src.services.project_tag_service import ProjectTagService

def check_vdos_projects():
    """VDOS DB에서 프로젝트 정보 확인"""
    print("=== 1. VDOS DB 프로젝트 정보 확인 ===")
    
    vdos_db_path = '../virtualoffice/src/virtualoffice/vdos.db'
    if not os.path.exists(vdos_db_path):
        print(f"❌ VDOS DB를 찾을 수 없음: {vdos_db_path}")
        return
    
    conn = sqlite3.connect(vdos_db_path)
    cur = conn.cursor()
    
    # 프로젝트 정보 조회
    cur.execute("SELECT id, project_name, project_summary FROM project_plans ORDER BY id")
    projects = cur.fetchall()
    print(f"VDOS DB 프로젝트: {len(projects)}개")
    for project_id, name, summary in projects:
        print(f"- ID {project_id}: {name}")
        print(f"  요약: {summary[:100]}...")
    
    # 프로젝트-사람 매핑 조회
    cur.execute("""
        SELECT pp.project_name, p.name, p.email_address
        FROM project_plans pp
        JOIN project_assignments pa ON pp.id = pa.project_id
        JOIN people p ON pa.person_id = p.id
        ORDER BY pp.project_name, p.name
    """)
    assignments = cur.fetchall()
    print(f"\n프로젝트-사람 매핑: {len(assignments)}개")
    current_project = None
    for project_name, person_name, email in assignments:
        if project_name != current_project:
            print(f"\n📁 {project_name}:")
            current_project = project_name
        print(f"  - {person_name} ({email})")
    
    conn.close()

def check_project_service():
    """프로젝트 태그 서비스 상태 확인"""
    print("\n=== 2. 프로젝트 태그 서비스 상태 확인 ===")
    
    service = ProjectTagService()
    
    print(f"로드된 프로젝트: {len(service.project_tags)}개")
    for code, tag in service.project_tags.items():
        print(f"- {code}: {tag.name}")
    
    print(f"\n사람-프로젝트 매핑: {len(service.person_project_mapping)}개")
    for person, projects in list(service.person_project_mapping.items())[:10]:  # 처음 10개만
        print(f"- {person}: {projects}")

def test_explicit_extraction():
    """명시적 프로젝트 추출 테스트"""
    print("\n=== 3. 명시적 프로젝트 추출 테스트 ===")
    
    service = ProjectTagService()
    
    test_messages = [
        {
            "subject": "[CareBridge Integration] 최종 QA 및 자료 작성 진행 상황",
            "content": "CareBridge Integration 프로젝트 관련 업무입니다.",
            "sender": "leejungdu@example.com"
        },
        {
            "subject": "[WellLink 브랜드 런칭 캠페인] 캠페인 전략 진행 상황",
            "content": "WellLink 브랜드 런칭 캠페인 관련 업무입니다.",
            "sender": "serin.kim@company.com"
        },
        {
            "subject": "[Care Connect 2.0 리디자인] UI/UX 개선 작업",
            "content": "Care Connect 앱 리디자인 관련 업무입니다.",
            "sender": "yeonjung.kim@company.com"
        },
        {
            "subject": "[HealthCore API 리팩토링] 성능 최적화 작업",
            "content": "HealthCore API 리팩토링 관련 업무입니다.",
            "sender": "imboyeon_koreait"
        }
    ]
    
    for i, msg in enumerate(test_messages, 1):
        print(f"\n테스트 {i}: {msg['subject']}")
        
        # 명시적 추출 테스트
        explicit_result = service._extract_explicit_project(msg)
        print(f"  명시적 추출: {explicit_result}")
        
        # 발신자 기반 추출 테스트
        sender_result = service._extract_project_by_sender(msg)
        print(f"  발신자 기반: {sender_result}")
        
        # 전체 추출 테스트
        full_result = service.extract_project_from_message(msg)
        print(f"  전체 추출: {full_result}")

def test_llm_classification():
    """LLM 기반 분류 테스트"""
    print("\n=== 4. LLM 기반 분류 테스트 ===")
    
    service = ProjectTagService()
    
    # LLM 설정 확인
    try:
        from config.llm_config import LLM_CONFIG
        provider = LLM_CONFIG.get("provider", "unknown")
        print(f"LLM 제공자: {provider}")
        
        if provider == "azure":
            endpoint = LLM_CONFIG.get("azure", {}).get("endpoint", "N/A")
            print(f"Azure 엔드포인트: {endpoint}")
        elif provider == "openai":
            model = LLM_CONFIG.get("openai", {}).get("model", "N/A")
            print(f"OpenAI 모델: {model}")
            
    except ImportError:
        print("❌ LLM 설정 파일을 찾을 수 없음")
    
    # 애매한 메시지로 LLM 테스트
    ambiguous_message = {
        "subject": "프로젝트 진행 상황 보고",
        "content": "현재 진행 중인 작업에 대한 상태 업데이트입니다. API 성능 개선 작업을 진행하고 있습니다.",
        "sender": "developer@example.com"
    }
    
    print(f"\n애매한 메시지 테스트:")
    print(f"제목: {ambiguous_message['subject']}")
    print(f"내용: {ambiguous_message['content']}")
    
    try:
        llm_result = service._extract_project_by_llm(ambiguous_message)
        print(f"LLM 분류 결과: {llm_result}")
    except Exception as e:
        print(f"❌ LLM 분류 오류: {e}")

def main():
    print("=== 프로젝트 분류 시스템 종합 디버깅 ===\n")
    
    check_vdos_projects()
    check_project_service()
    test_explicit_extraction()
    test_llm_classification()
    
    print("\n=== 디버깅 완료 ===")

if __name__ == "__main__":
    main()