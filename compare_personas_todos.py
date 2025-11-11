#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""페르소나별 TODO evidence 비교 스크립트"""
import sqlite3
import os
import json

# DB 경로
db_path = os.path.join(os.path.dirname(__file__), "../virtualoffice/src/virtualoffice/todos_cache.db")

if not os.path.exists(db_path):
    print(f"DB 파일을 찾을 수 없습니다: {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 페르소나별 TODO 조회
personas = ["이정두", "임보연", "김세린", "전형우"]

for persona in personas:
    print(f"\n{'='*100}")
    print(f"페르소나: {persona}")
    print(f"{'='*100}")
    
    query = """
    SELECT 
        id, 
        title, 
        description, 
        priority, 
        requester,
        evidence,
        created_at
    FROM todos 
    WHERE persona_name = ?
    ORDER BY created_at DESC 
    LIMIT 5
    """
    
    cursor.execute(query, (persona,))
    rows = cursor.fetchall()
    
    if not rows:
        print(f"  → TODO 없음")
        continue
    
    print(f"\n최근 TODO 5개:\n")
    
    for i, row in enumerate(rows, 1):
        todo_id, title, description, priority, requester, evidence, created_at = row
        
        print(f"[TODO #{i}]")
        print(f"  ID: {todo_id}")
        print(f"  제목: {title}")
        print(f"  설명: {description[:80] if description else 'N/A'}...")
        print(f"  발신자: {requester}")
        print(f"  우선순위: {priority}")
        print(f"  생성일: {created_at}")
        
        # evidence 파싱
        if evidence:
            try:
                evidence_data = json.loads(evidence)
                if isinstance(evidence_data, list):
                    if len(evidence_data) > 0:
                        print(f"  ✅ Evidence: {len(evidence_data)}개")
                        for j, reason in enumerate(evidence_data[:3], 1):
                            print(f"     {j}. {reason}")
                    else:
                        print(f"  ❌ Evidence: 빈 배열 []")
                else:
                    print(f"  ⚠️ Evidence: 리스트가 아님 - {type(evidence_data)}")
            except Exception as e:
                print(f"  ❌ Evidence 파싱 실패: {e}")
                print(f"     원본: {evidence[:100]}")
        else:
            print(f"  ❌ Evidence: NULL")
        
        print("-" * 100)

conn.close()

print(f"\n{'='*100}")
print("요약")
print(f"{'='*100}")

# 통계 조회
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

for persona in personas:
    # 전체 TODO 개수
    cursor.execute("SELECT COUNT(*) FROM todos WHERE persona_name = ?", (persona,))
    total = cursor.fetchone()[0]
    
    # evidence가 빈 배열인 TODO 개수
    cursor.execute("SELECT COUNT(*) FROM todos WHERE persona_name = ? AND (evidence = '[]' OR evidence IS NULL OR evidence = '')", (persona,))
    empty = cursor.fetchone()[0]
    
    # evidence가 있는 TODO 개수
    has_evidence = total - empty
    
    print(f"\n{persona}:")
    print(f"  - 전체 TODO: {total}개")
    print(f"  - Evidence 있음: {has_evidence}개 ({has_evidence/total*100:.1f}%)" if total > 0 else "  - Evidence 있음: 0개")
    print(f"  - Evidence 없음: {empty}개 ({empty/total*100:.1f}%)" if total > 0 else "  - Evidence 없음: 0개")

conn.close()
