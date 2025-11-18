# -*- coding: utf-8 -*-
"""
임보연 페르소나 캐시 디버깅 스크립트

캐시 키 생성 로직과 저장된 캐시를 확인합니다.
"""
import sys
import os
import sqlite3
from datetime import datetime, timezone

# 프로젝트 루트를 sys.path에 추가
project_root = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(project_root, "src")
if project_root not in sys.path:
    sys.path.insert(0, project_root)
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from src.integrations.virtualoffice_client import VirtualOfficeClient


def check_boyeon_cache():
    """임보연 캐시 확인"""
    
    print("="*80)
    print("임보연 페르소나 캐시 디버깅")
    print("="*80)
    
    # 1. VirtualOffice에서 페르소나 정보 조회
    print("\n1. VirtualOffice API에서 페르소나 조회...")
    client = VirtualOfficeClient(
        email_url="http://127.0.0.1:8002",
        chat_url="http://127.0.0.1:8001",
        sim_url="http://127.0.0.1:8015"
    )
    
    personas = client.get_personas()
    print(f"   총 {len(personas)}명 조회")
    
    # 임보연 찾기
    boyeon = None
    for persona in personas:
        persona_dict = persona.to_dict() if hasattr(persona, 'to_dict') else {
            "name": persona.name,
            "email_address": persona.email_address,
            "chat_handle": persona.chat_handle
        }
        
        if "보연" in persona_dict.get("name", ""):
            boyeon = persona_dict
            print(f"\n   ✅ 임보연 페르소나 발견:")
            print(f"      이름: {boyeon['name']}")
            print(f"      이메일: {boyeon['email_address']}")
            print(f"      핸들: {boyeon['chat_handle']}")
            break
    
    if not boyeon:
        print("   ❌ 임보연 페르소나를 찾을 수 없습니다!")
        return
    
    # 2. 캐시 키 생성 로직 확인
    print("\n2. 캐시 키 생성 로직 확인...")
    
    # MainWindow의 _generate_cache_key 로직 재현
    email = boyeon['email_address']
    handle = boyeon['chat_handle']
    cache_key = f"{email}_{handle}"
    
    print(f"   생성된 캐시 키: '{cache_key}'")
    
    # 3. todos_cache.db 확인
    print("\n3. todos_cache.db 확인...")
    
    # DB 파일 위치 (virtualoffice 폴더)
    db_path = r"C:\Users\USER\Desktop\virtual-office-orchestration\virtualoffice\src\virtualoffice\todos_cache.db"
    
    if not os.path.exists(db_path):
        print(f"   ❌ DB 파일이 없습니다: {db_path}")
        return
    
    print(f"   DB 경로: {db_path}")
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 3-1. 모든 캐시 키 조회
    print("\n   3-1. 저장된 모든 캐시 키:")
    cursor.execute("SELECT DISTINCT cache_key FROM analysis_cache")
    cache_keys = cursor.fetchall()
    
    if not cache_keys:
        print("      ⚠️ 저장된 캐시가 없습니다!")
    else:
        for row in cache_keys:
            key = row['cache_key']
            print(f"      - '{key}'")
            
            # 임보연 캐시 키와 비교
            if key == cache_key:
                print(f"        ✅ 일치! (정확히 같음)")
            elif "보연" in key or "boyeon" in key.lower():
                print(f"        ⚠️ 유사하지만 다름!")
                print(f"           기대: '{cache_key}'")
                print(f"           실제: '{key}'")
    
    # 3-2. 임보연 캐시 상세 정보
    print(f"\n   3-2. 임보연 캐시 상세 정보 (cache_key='{cache_key}'):")
    cursor.execute("""
        SELECT cache_key, last_updated, message_count, todo_count
        FROM analysis_cache
        WHERE cache_key = ?
    """, (cache_key,))
    
    cache_row = cursor.fetchone()
    
    if cache_row:
        print(f"      ✅ 캐시 발견!")
        print(f"         마지막 업데이트: {cache_row['last_updated']}")
        print(f"         메시지 수: {cache_row['message_count']}")
        print(f"         TODO 수: {cache_row['todo_count']}")
        
        # 캐시 유효성 확인 (14일)
        last_updated = datetime.fromisoformat(cache_row['last_updated'])
        now = datetime.now(timezone.utc)
        age_days = (now - last_updated).days
        
        print(f"         캐시 나이: {age_days}일")
        
        if age_days > 14:
            print(f"         ⚠️ 캐시 만료됨 (14일 초과)")
        else:
            print(f"         ✅ 캐시 유효함 ({14 - age_days}일 남음)")
    else:
        print(f"      ❌ 캐시 없음!")
        
        # 유사한 키 검색
        print(f"\n      유사한 캐시 키 검색 중...")
        cursor.execute("""
            SELECT cache_key, last_updated, message_count, todo_count
            FROM analysis_cache
            WHERE cache_key LIKE ?
        """, (f"%{email}%",))
        
        similar_caches = cursor.fetchall()
        
        if similar_caches:
            print(f"      ⚠️ 이메일 주소가 포함된 캐시 발견:")
            for row in similar_caches:
                print(f"         - '{row['cache_key']}'")
                print(f"           업데이트: {row['last_updated']}")
                print(f"           메시지: {row['message_count']}개, TODO: {row['todo_count']}개")
        
        cursor.execute("""
            SELECT cache_key, last_updated, message_count, todo_count
            FROM analysis_cache
            WHERE cache_key LIKE ?
        """, (f"%{handle}%",))
        
        similar_caches = cursor.fetchall()
        
        if similar_caches:
            print(f"      ⚠️ 핸들이 포함된 캐시 발견:")
            for row in similar_caches:
                print(f"         - '{row['cache_key']}'")
                print(f"           업데이트: {row['last_updated']}")
                print(f"           메시지: {row['message_count']}개, TODO: {row['todo_count']}개")
    
    # 4. TODO 테이블 확인
    print(f"\n4. TODO 테이블에서 임보연 TODO 확인...")
    
    cursor.execute("""
        SELECT COUNT(*) as count
        FROM todos
        WHERE persona_name = ? OR persona_email = ? OR persona_handle = ?
    """, (boyeon['name'], boyeon['email_address'], boyeon['chat_handle']))
    
    todo_count = cursor.fetchone()['count']
    print(f"   임보연 TODO 개수: {todo_count}개")
    
    if todo_count > 0:
        cursor.execute("""
            SELECT id, title, priority, created_at
            FROM todos
            WHERE persona_name = ? OR persona_email = ? OR persona_handle = ?
            ORDER BY created_at DESC
            LIMIT 5
        """, (boyeon['name'], boyeon['email_address'], boyeon['chat_handle']))
        
        todos = cursor.fetchall()
        print(f"\n   최근 TODO 5개:")
        for todo in todos:
            print(f"      - [{todo['priority']}] {todo['title']}")
            print(f"        생성: {todo['created_at']}")
    
    # 5. 캐시 키 생성 로직 비교
    print(f"\n5. 캐시 키 생성 로직 검증...")
    print(f"   기대 캐시 키: '{cache_key}'")
    print(f"   이메일: '{email}'")
    print(f"   핸들: '{handle}'")
    print(f"   구분자: '_'")
    
    # 공백이나 특수문자 확인
    if ' ' in cache_key:
        print(f"   ⚠️ 캐시 키에 공백 포함!")
    if '\t' in cache_key:
        print(f"   ⚠️ 캐시 키에 탭 포함!")
    if '\n' in cache_key:
        print(f"   ⚠️ 캐시 키에 개행 포함!")
    
    # 6. 권장 사항
    print(f"\n6. 진단 결과 및 권장 사항:")
    
    if cache_row:
        print(f"   ✅ 임보연 캐시가 정상적으로 저장되어 있습니다.")
        print(f"   ✅ 캐시 키가 올바르게 생성되었습니다.")
        
        if age_days > 14:
            print(f"   ⚠️ 하지만 캐시가 만료되었습니다 (14일 초과).")
            print(f"   → 캐시를 삭제하고 재생성하세요.")
        else:
            print(f"   ✅ 캐시가 유효합니다.")
            print(f"   → 앱에서 임보연 선택 시 캐시 히트되어야 합니다.")
    else:
        print(f"   ❌ 임보연 캐시가 없습니다!")
        print(f"   → 앱에서 임보연을 선택하면 새로 분석이 실행됩니다.")
        
        if similar_caches:
            print(f"   ⚠️ 유사한 캐시 키가 발견되었습니다.")
            print(f"   → 캐시 키 생성 로직에 문제가 있을 수 있습니다.")
    
    conn.close()
    
    print("\n" + "="*80)
    print("디버깅 완료")
    print("="*80)


if __name__ == "__main__":
    check_boyeon_cache()
