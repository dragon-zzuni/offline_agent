# -*- coding: utf-8 -*-
"""
TODO의 source_message 내용 확인

실제 원본 메시지에 프로젝트 정보가 있는지 확인합니다.
"""
import sqlite3
import os
import json


def check_source_messages():
    """source_message 내용 확인"""
    todos_db_path = "virtualoffice/src/virtualoffice/todos_cache.db"
    
    if not os.path.exists(todos_db_path):
        print(f"❌ todos_cache.db를 찾을 수 없습니다")
        return
    
    conn = sqlite3.connect(todos_db_path)
    cursor = conn.cursor()
    
    # 김세린의 TODO 중 프로젝트 태그가 없는 것 5개 샘플
    cursor.execute("""
        SELECT id, title, description, source_message, requester
        FROM todos
        WHERE persona_name = '김세린'
        AND (project IS NULL OR project = '')
        ORDER BY created_at DESC
        LIMIT 5
    """)
    
    print("=" * 80)
    print("TODO source_message 내용 분석")
    print("=" * 80)
    
    for i, row in enumerate(cursor.fetchall(), 1):
        todo_id, title, description, source_message, requester = row
        
        print(f"\n{'='*80}")
        print(f"TODO #{i}: {title}")
        print(f"{'='*80}")
        print(f"요청자: {requester}")
        print(f"\n📝 Description:")
        print(f"{description[:300] if description else '(없음)'}...")
        
        print(f"\n📨 Source Message:")
        if source_message:
            try:
                if isinstance(source_message, str) and source_message.startswith("{"):
                    msg_data = json.loads(source_message)
                    print(f"  타입: {msg_data.get('type', 'unknown')}")
                    print(f"  발신자: {msg_data.get('sender', 'unknown')}")
                    print(f"  제목: {msg_data.get('subject', '(없음)')}")
                    print(f"  본문 (처음 500자):")
                    body = msg_data.get('body') or msg_data.get('content', '')
                    print(f"  {body[:500]}...")
                    
                    # 프로젝트 키워드 찾기
                    keywords = ['프로젝트', 'project', 'PV', 'PS', 'HA', 'CB', 'WL', 'VC']
                    found_keywords = []
                    full_text = f"{msg_data.get('subject', '')} {body}".lower()
                    for kw in keywords:
                        if kw.lower() in full_text:
                            found_keywords.append(kw)
                    
                    if found_keywords:
                        print(f"\n  🔍 발견된 키워드: {', '.join(found_keywords)}")
                    else:
                        print(f"\n  ⚠️ 프로젝트 키워드 없음")
                else:
                    print(f"  (문자열): {source_message[:200]}...")
            except Exception as e:
                print(f"  ❌ 파싱 오류: {e}")
        else:
            print("  (없음)")
    
    conn.close()
    print("\n" + "=" * 80)


if __name__ == "__main__":
    check_source_messages()
