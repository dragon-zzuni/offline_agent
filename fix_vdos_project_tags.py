#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VDOS TODO 프로젝트 태그 수정 스크립트
"""
import sqlite3
import json
import re
from typing import Optional

def extract_project_from_text(text: str) -> Optional[str]:
    """텍스트에서 프로젝트 코드 추출"""
    if not text:
        return None
    
    text_lower = text.lower()
    
    # 명시적 패턴 매칭 (정확한 순서로)
    if "care connect" in text_lower or "careconnect" in text_lower:
        return "CARE"
    elif "healthcore" in text_lower or "health core" in text_lower:
        return "HA"
    elif "bridge" in text_lower or "carebridge" in text_lower:
        return "BRIDGE"
    elif "insight dashboard" in text_lower or "welllink insight" in text_lower:
        return "WD"
    elif "welllink" in text_lower and ("브랜드" in text or "brand" in text_lower or "런칭" in text or "launch" in text_lower):
        return "LINK"
    elif "welllink" in text_lower:
        return "LINK"  # 기본적으로 LINK로 분류
    
    # 추가 패턴들
    elif "kpi 대시보드" in text_lower or "kpi dashboard" in text_lower:
        return "WD"
    elif "프로토타입" in text_lower and ("대시보드" in text_lower or "dashboard" in text_lower):
        return "WD"
    elif "api 리팩토링" in text_lower or "api refactoring" in text_lower:
        return "HA"
    elif "백엔드" in text_lower and ("성능" in text_lower or "performance" in text_lower):
        return "HA"
    
    # 사람 이름 기반 추정 (VDOS 페르소나 매핑)
    elif "김연정" in text or "yeonjung" in text_lower:
        return "BRIDGE"  # 김연정은 CareBridge 담당
    elif "유준영" in text or "junyoung" in text_lower:
        return "WD"      # 유준영은 WellLink Insight Dashboard 담당
    elif "정지원" in text or "jiwon" in text_lower:
        return "CARE"    # 정지원은 Care Connect 담당
    elif "전형우" in text or "hyungwoo" in text_lower:
        return "HA"      # 전형우는 HealthCore API 담당
    
    return None

def fix_vdos_project_tags():
    """VDOS TODO 프로젝트 태그 수정"""
    db_path = '../virtualoffice/src/virtualoffice/todos_cache.db'
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # 프로젝트가 없는 TODO들 조회
    cur.execute("""
        SELECT id, title, description, source_message 
        FROM todos 
        WHERE project IS NULL OR project = ''
    """)
    
    todos_to_update = cur.fetchall()
    print(f"프로젝트 없는 TODO: {len(todos_to_update)}개")
    
    updated_count = 0
    
    for todo_id, title, description, source_message in todos_to_update:
        project_code = None
        
        # 1. 제목에서 추출 시도
        if title:
            project_code = extract_project_from_text(title)
        
        # 2. 설명에서 추출 시도
        if not project_code and description:
            project_code = extract_project_from_text(description)
        
        # 3. 소스 메시지에서 추출 시도
        if not project_code and source_message:
            try:
                # JSON 파싱 시도
                msg_data = json.loads(source_message)
                
                # 제목/내용 확인
                for key in ['subject', 'title', 'content', 'body']:
                    if key in msg_data and msg_data[key]:
                        project_code = extract_project_from_text(str(msg_data[key]))
                        if project_code:
                            break
                            
            except:
                # JSON이 아닌 경우 텍스트로 처리
                project_code = extract_project_from_text(source_message)
        
        # 프로젝트 코드가 발견되면 업데이트
        if project_code:
            cur.execute(
                "UPDATE todos SET project = ? WHERE id = ?",
                (project_code, todo_id)
            )
            updated_count += 1
            print(f"  {todo_id}: {project_code} - {title[:50]}...")
    
    conn.commit()
    
    # 결과 확인
    cur.execute('SELECT project, COUNT(*) FROM todos WHERE project IS NOT NULL GROUP BY project ORDER BY COUNT(*) DESC')
    results = cur.fetchall()
    
    print(f"\n✅ {updated_count}개 TODO 업데이트 완료")
    print("\n=== 최종 프로젝트 분포 ===")
    for project, count in results:
        print(f"{project}: {count}개")
    
    # 여전히 프로젝트가 없는 TODO 개수
    cur.execute('SELECT COUNT(*) FROM todos WHERE project IS NULL OR project = ""')
    remaining = cur.fetchone()[0]
    print(f"\n미분류 TODO: {remaining}개")
    
    conn.close()

if __name__ == "__main__":
    fix_vdos_project_tags()