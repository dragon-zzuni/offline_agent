#!/usr/bin/env python3
"""
requester 필드 마이그레이션 스크립트

발신자 이메일 → 페르소나 이름으로 변경
"""

import sys
import os
from pathlib import Path

# 경로 설정
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

def main():
    """메인 마이그레이션 함수"""
    print("=" * 60)
    print("🔄 requester 필드 마이그레이션")
    print("=" * 60)
    
    from ui.todo.repository import TodoRepository
    
    # 1. Repository 초기화
    print("\n1. Repository 초기화")
    repo = TodoRepository()
    print("   ✅ 초기화 완료")
    
    # 2. 페르소나 매핑 생성
    print("\n2. 페르소나 매핑 생성")
    
    # 실제 프로젝트의 페르소나 매핑
    # data/multi_project_8week_ko/people_*.json에서 가져올 수 있음
    persona_mapping = {
        # 예시 매핑 (실제 데이터에 맞게 수정 필요)
        "jeongdu.lee@koreaitcompany.com": "이정두",
        "boyeon.lim@koreaitcompany.com": "임보연",
        "hyujin.hong@koreaitcompany.com": "홍유진",
        "serin.kim@koreaitcompany.com": "김세린",
        
        # 추가 매핑
        "manager@test.com": "매니저",
        "dev@test.com": "개발자",
        "pm@test.com": "PM",
    }
    
    print(f"   페르소나 매핑: {len(persona_mapping)}개")
    for email, name in list(persona_mapping.items())[:3]:
        print(f"     - {email} → {name}")
    print(f"     ... (총 {len(persona_mapping)}개)")
    
    # 3. 마이그레이션 실행
    print("\n3. 마이그레이션 실행")
    
    result = repo.migrate_requester_field(persona_mapping)
    
    print(f"\n   결과:")
    print(f"     업데이트: {result['updated']}개")
    print(f"     스킵: {result['skipped']}개")
    print(f"     오류: {result['errors']}개")
    
    # 4. 인덱스 생성
    print("\n4. 인덱스 생성")
    repo.create_indexes()
    print("   ✅ 인덱스 생성 완료")
    
    # 5. 결과 확인
    print("\n5. 결과 확인")
    
    todos = repo.fetch_active()
    
    if todos:
        print(f"   활성 TODO: {len(todos)}개")
        
        # requester 분포 확인
        requester_counts = {}
        for todo in todos:
            requester = todo.get("requester", "Unknown")
            requester_counts[requester] = requester_counts.get(requester, 0) + 1
        
        print(f"\n   requester 분포:")
        for requester, count in sorted(requester_counts.items(), key=lambda x: -x[1])[:5]:
            print(f"     - {requester}: {count}개")
    else:
        print("   활성 TODO 없음")
    
    repo.close()
    
    print("\n" + "=" * 60)
    print("✅ 마이그레이션 완료!")
    print("=" * 60)
    
    return result

def load_persona_mapping_from_json():
    """JSON 파일에서 페르소나 매핑 로드"""
    import json
    
    # people JSON 파일 찾기
    data_dir = Path(__file__).parent / "data" / "multi_project_8week_ko"
    
    if not data_dir.exists():
        print(f"⚠️ 데이터 디렉토리가 없습니다: {data_dir}")
        return {}
    
    # people_*.json 파일 찾기
    people_files = list(data_dir.glob("people_*.json"))
    
    if not people_files:
        print(f"⚠️ people JSON 파일이 없습니다: {data_dir}")
        return {}
    
    # 가장 최근 파일 사용
    people_file = sorted(people_files)[-1]
    print(f"   페르소나 파일: {people_file.name}")
    
    try:
        with open(people_file, "r", encoding="utf-8") as f:
            people_data = json.load(f)
        
        # 매핑 생성
        mapping = {}
        for person in people_data:
            email = person.get("email_address")
            name = person.get("name")
            
            if email and name:
                mapping[email] = name
        
        print(f"   로드된 페르소나: {len(mapping)}개")
        return mapping
        
    except Exception as e:
        print(f"⚠️ 페르소나 파일 로드 실패: {e}")
        return {}

def main_with_json():
    """JSON 파일에서 매핑을 로드하여 마이그레이션"""
    print("=" * 60)
    print("🔄 requester 필드 마이그레이션 (JSON 기반)")
    print("=" * 60)
    
    from ui.todo.repository import TodoRepository
    
    # 1. Repository 초기화
    print("\n1. Repository 초기화")
    repo = TodoRepository()
    print("   ✅ 초기화 완료")
    
    # 2. JSON에서 페르소나 매핑 로드
    print("\n2. JSON에서 페르소나 매핑 로드")
    persona_mapping = load_persona_mapping_from_json()
    
    if not persona_mapping:
        print("   ⚠️ 페르소나 매핑이 비어있습니다. 기본 매핑 사용")
        persona_mapping = {
            "jeongdu.lee@koreaitcompany.com": "이정두",
            "boyeon.lim@koreaitcompany.com": "임보연",
            "hyujin.hong@koreaitcompany.com": "홍유진",
            "serin.kim@koreaitcompany.com": "김세린",
        }
    
    print(f"   페르소나 매핑: {len(persona_mapping)}개")
    for email, name in list(persona_mapping.items())[:5]:
        print(f"     - {email} → {name}")
    
    # 3. 마이그레이션 실행
    print("\n3. 마이그레이션 실행")
    
    result = repo.migrate_requester_field(persona_mapping)
    
    print(f"\n   결과:")
    print(f"     업데이트: {result['updated']}개")
    print(f"     스킵: {result['skipped']}개")
    print(f"     오류: {result['errors']}개")
    
    # 4. 인덱스 생성
    print("\n4. 인덱스 생성")
    repo.create_indexes()
    print("   ✅ 인덱스 생성 완료")
    
    # 5. 결과 확인
    print("\n5. 결과 확인")
    
    todos = repo.fetch_active()
    
    if todos:
        print(f"   활성 TODO: {len(todos)}개")
        
        # requester 분포 확인
        requester_counts = {}
        for todo in todos:
            requester = todo.get("requester", "Unknown")
            requester_counts[requester] = requester_counts.get(requester, 0) + 1
        
        print(f"\n   requester 분포:")
        for requester, count in sorted(requester_counts.items(), key=lambda x: -x[1])[:10]:
            print(f"     - {requester}: {count}개")
    else:
        print("   활성 TODO 없음")
    
    repo.close()
    
    print("\n" + "=" * 60)
    print("✅ 마이그레이션 완료!")
    print("=" * 60)
    
    return result

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="requester 필드 마이그레이션")
    parser.add_argument(
        "--from-json",
        action="store_true",
        help="JSON 파일에서 페르소나 매핑 로드"
    )
    
    args = parser.parse_args()
    
    try:
        if args.from_json:
            result = main_with_json()
        else:
            result = main()
        
        # 성공 여부 확인
        if result["errors"] > 0:
            print(f"\n⚠️ {result['errors']}개 오류 발생")
            sys.exit(1)
        else:
            print("\n✅ 모든 작업 성공!")
            sys.exit(0)
            
    except Exception as e:
        print(f"\n❌ 마이그레이션 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
