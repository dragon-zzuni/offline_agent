#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Top3 통합 디버깅 스크립트

현재 시스템에서 Top3가 표시되지 않는 문제를 진단합니다.
"""
import sys
import os
import logging
from pathlib import Path

# 경로 설정
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
sys.path.insert(0, os.path.dirname(__file__))

# 로깅 설정
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def check_current_system():
    """현재 시스템 상태 확인"""
    print("=" * 80)
    print("1. 현재 시스템 상태 확인")
    print("=" * 80)
    
    # 기존 Top3Service 확인
    try:
        from src.services.top3_service import Top3Service
        print("✅ 기존 Top3Service 로드 성공")
        
        # 인스턴스 생성 테스트
        service = Top3Service()
        print(f"✅ Top3Service 인스턴스 생성 성공")
        print(f"   - 규칙: {service.get_rules()}")
        print(f"   - 마지막 지시사항: '{service.get_last_instruction()}'")
        
    except Exception as e:
        print(f"❌ 기존 Top3Service 로드 실패: {e}")
        import traceback
        traceback.print_exc()
    
    # 새로운 리팩토링 서비스 확인
    try:
        from src.services.top3_service_refactored import Top3ServiceRefactored
        print("✅ 리팩토링된 Top3Service 로드 성공")
        
        service = Top3ServiceRefactored()
        print(f"✅ Top3ServiceRefactored 인스턴스 생성 성공")
        print(f"   - LLM 사용 가능: {service.llm_client.is_available()}")
        print(f"   - 제공자: {service.llm_client.get_available_providers()}")
        
    except Exception as e:
        print(f"❌ 리팩토링된 Top3Service 로드 실패: {e}")
        import traceback
        traceback.print_exc()
    
    print()

def check_main_window_integration():
    """메인 윈도우에서 Top3Service 사용 확인"""
    print("=" * 80)
    print("2. 메인 윈도우 Top3Service 통합 확인")
    print("=" * 80)
    
    try:
        # main.py에서 SmartAssistant 클래스 확인
        from main import SmartAssistant
        print("✅ SmartAssistant 클래스 로드 성공")
        
        # Top3Service 초기화 부분 확인
        assistant = SmartAssistant()
        
        if hasattr(assistant, 'top3_service'):
            print("✅ SmartAssistant에 top3_service 속성 존재")
            print(f"   - 타입: {type(assistant.top3_service)}")
            
            # Top3 선정 테스트
            test_todos = [
                {
                    "id": "test_001",
                    "title": "테스트 TODO 1",
                    "priority": "high",
                    "status": "pending"
                },
                {
                    "id": "test_002", 
                    "title": "테스트 TODO 2",
                    "priority": "medium",
                    "status": "pending"
                }
            ]
            
            top3_ids = assistant.top3_service.pick_top3(test_todos)
            print(f"✅ Top3 선정 테스트 성공: {top3_ids}")
            
        else:
            print("❌ SmartAssistant에 top3_service 속성 없음")
            print(f"   - 사용 가능한 속성: {[attr for attr in dir(assistant) if not attr.startswith('_')]}")
            
    except Exception as e:
        print(f"❌ 메인 윈도우 통합 확인 실패: {e}")
        import traceback
        traceback.print_exc()
    
    print()

def check_todo_panel():
    """TODO 패널에서 Top3 표시 확인"""
    print("=" * 80)
    print("3. TODO 패널 Top3 표시 확인")
    print("=" * 80)
    
    try:
        # TODO 패널 코드 확인
        from src.ui.todo_panel import TodoPanel
        print("✅ TodoPanel 클래스 로드 성공")
        
        # Top3 관련 메서드 확인
        methods = [method for method in dir(TodoPanel) if 'top3' in method.lower()]
        print(f"Top3 관련 메서드: {methods}")
        
        # _update_todo_display 메서드 확인
        if hasattr(TodoPanel, '_update_todo_display'):
            print("✅ _update_todo_display 메서드 존재")
        else:
            print("❌ _update_todo_display 메서드 없음")
            
    except Exception as e:
        print(f"❌ TODO 패널 확인 실패: {e}")
        import traceback
        traceback.print_exc()
    
    print()

def check_database_top3():
    """데이터베이스에서 Top3 정보 확인"""
    print("=" * 80)
    print("4. 데이터베이스 Top3 정보 확인")
    print("=" * 80)
    
    try:
        import sqlite3
        
        # 데이터베이스 파일 찾기
        db_paths = [
            "data/multi_project_8week_ko/todos_cache.db",
            "offline_agent/data/multi_project_8week_ko/todos_cache.db",
            "../data/multi_project_8week_ko/todos_cache.db"
        ]
        
        db_path = None
        for path in db_paths:
            if os.path.exists(path):
                db_path = path
                break
        
        if not db_path:
            print("❌ todos_cache.db 파일을 찾을 수 없습니다")
            print(f"   - 확인한 경로: {db_paths}")
            return
        
        print(f"✅ 데이터베이스 파일 발견: {db_path}")
        
        # 데이터베이스 연결
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 테이블 구조 확인
        cursor.execute("PRAGMA table_info(todos)")
        columns = cursor.fetchall()
        print(f"✅ todos 테이블 컬럼: {[col[1] for col in columns]}")
        
        # is_top3 컬럼 확인
        has_is_top3 = any(col[1] == 'is_top3' for col in columns)
        print(f"is_top3 컬럼 존재: {has_is_top3}")
        
        # TODO 개수 확인
        cursor.execute("SELECT COUNT(*) FROM todos")
        total_count = cursor.fetchone()[0]
        print(f"✅ 총 TODO 개수: {total_count}")
        
        if has_is_top3:
            cursor.execute("SELECT COUNT(*) FROM todos WHERE is_top3 = 1")
            top3_count = cursor.fetchone()[0]
            print(f"✅ Top3 TODO 개수: {top3_count}")
            
            if top3_count > 0:
                cursor.execute("SELECT id, title, is_top3 FROM todos WHERE is_top3 = 1 LIMIT 5")
                top3_todos = cursor.fetchall()
                print("Top3 TODO 목록:")
                for todo in top3_todos:
                    print(f"  - {todo[0]}: {todo[1]} (is_top3: {todo[2]})")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 데이터베이스 확인 실패: {e}")
        import traceback
        traceback.print_exc()
    
    print()

def check_analysis_pipeline():
    """분석 파이프라인에서 Top3 자동 선정 확인"""
    print("=" * 80)
    print("5. 분석 파이프라인 Top3 자동 선정 확인")
    print("=" * 80)
    
    try:
        from src.services.analysis_pipeline_service import AnalysisPipelineService
        print("✅ AnalysisPipelineService 로드 성공")
        
        # analyze_messages 메서드에서 Top3 관련 코드 확인
        import inspect
        source = inspect.getsource(AnalysisPipelineService.analyze_messages)
        
        if 'top3_service' in source:
            print("✅ analyze_messages에 top3_service 코드 존재")
        else:
            print("❌ analyze_messages에 top3_service 코드 없음")
        
        if 'is_top3' in source:
            print("✅ analyze_messages에 is_top3 플래그 설정 코드 존재")
        else:
            print("❌ analyze_messages에 is_top3 플래그 설정 코드 없음")
            
    except Exception as e:
        print(f"❌ 분석 파이프라인 확인 실패: {e}")
        import traceback
        traceback.print_exc()
    
    print()

def run_integration_test():
    """통합 테스트 실행"""
    print("=" * 80)
    print("6. 통합 테스트 실행")
    print("=" * 80)
    
    try:
        # 환경 변수 확인
        llm_provider = os.getenv("LLM_PROVIDER", "auto")
        openai_key = os.getenv("OPENAI_API_KEY", "")
        azure_key = os.getenv("AZURE_OPENAI_KEY", "")
        
        print(f"LLM_PROVIDER: {llm_provider}")
        print(f"OPENAI_API_KEY: {'설정됨' if openai_key else '없음'}")
        print(f"AZURE_OPENAI_KEY: {'설정됨' if azure_key else '없음'}")
        
        # 리팩토링된 서비스로 테스트
        from src.services.top3_service_refactored import Top3ServiceRefactored
        
        service = Top3ServiceRefactored()
        
        # 자연어 규칙 설정
        natural_rule = "Care Connect 프로젝트 관련 TODO를 최우선으로"
        result_msg, rule_desc = service.apply_natural_language_rules(natural_rule)
        
        print(f"자연어 규칙 설정 결과: {result_msg}")
        print(f"규칙 설명:\n{rule_desc}")
        
        # 테스트 TODO로 선정 테스트
        test_todos = [
            {
                "id": "todo_001",
                "title": "Care Connect 로그인 버그 수정",
                "project": "CARE",
                "requester": "유준영",
                "priority": "high",
                "status": "pending"
            },
            {
                "id": "todo_002", 
                "title": "WellLink UI 개선",
                "project": "LINK",
                "requester": "김세린",
                "priority": "medium",
                "status": "pending"
            }
        ]
        
        print(f"\n테스트 TODO 개수: {len(test_todos)}")
        
        top3_ids = service.pick_top3(test_todos)
        print(f"선정된 Top3: {top3_ids}")
        
        if top3_ids:
            print("✅ Top3 선정 성공!")
            for todo_id in top3_ids:
                todo = next((t for t in test_todos if t["id"] == todo_id), None)
                if todo:
                    print(f"  - {todo_id}: {todo['title']}")
        else:
            print("⚠️ Top3 선정 결과가 비어있습니다")
            
    except Exception as e:
        print(f"❌ 통합 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
    
    print()

def main():
    """메인 디버깅 실행"""
    print("\n" + "=" * 80)
    print("Top3 통합 디버깅 시작")
    print("=" * 80 + "\n")
    
    check_current_system()
    check_main_window_integration()
    check_todo_panel()
    check_database_top3()
    check_analysis_pipeline()
    run_integration_test()
    
    print("=" * 80)
    print("디버깅 완료")
    print("=" * 80)

if __name__ == "__main__":
    main()