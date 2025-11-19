# -*- coding: utf-8 -*-
"""
Top3 선정에서 마감일 조건이 제대로 적용되는지 확인
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import logging
from datetime import datetime, timedelta
from src.services.top3_llm_selector import Top3LLMSelector

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

# 테스트 TODO 생성
now = datetime.now()

todos = [
    {
        "id": "todo_1",
        "title": "긴급 버그 수정",
        "project": "PL",
        "project_full_name": "Project LUMINA",
        "requester": "hyungwoo.jeon@example.com",
        "type": "task",
        "source_type": "email",
        "priority": "high",
        "deadline": (now + timedelta(days=1)).isoformat(),  # D-1
        "status": "pending"
    },
    {
        "id": "todo_2",
        "title": "문서 검토",
        "project": "PL",
        "project_full_name": "Project LUMINA",
        "requester": "hyungwoo.jeon@example.com",
        "type": "task",
        "source_type": "email",
        "priority": "medium",
        "deadline": (now + timedelta(days=5)).isoformat(),  # D-5
        "status": "pending"
    },
    {
        "id": "todo_3",
        "title": "장기 프로젝트 계획",
        "project": "PL",
        "project_full_name": "Project LUMINA",
        "requester": "hyungwoo.jeon@example.com",
        "type": "task",
        "source_type": "email",
        "priority": "low",
        "deadline": (now + timedelta(days=20)).isoformat(),  # D-20
        "status": "pending"
    },
    {
        "id": "todo_4",
        "title": "다른 프로젝트 긴급 작업",
        "project": "CI",
        "project_full_name": "CareBridge Integration",
        "requester": "boyeon.kim@example.com",
        "type": "task",
        "source_type": "email",
        "priority": "high",
        "deadline": (now + timedelta(days=2)).isoformat(),  # D-2
        "status": "pending"
    }
]

# 자연어 규칙: 마감이 많이 남은 것 우선
natural_rule = "전형우가 요청한 LUMINA 프로젝트의 업무처리 TODO 중에서 마감이 많이 남은 것을 우선적으로 선정해주세요"

print("=" * 80)
print("테스트: 마감일 조건 적용 확인")
print("=" * 80)
print(f"\n자연어 규칙: {natural_rule}\n")

print("TODO 리스트:")
for todo in todos:
    deadline_str = todo.get("deadline", "")
    if deadline_str:
        deadline_dt = datetime.fromisoformat(deadline_str)
        days_left = (deadline_dt - now).days
        print(f"  - {todo['id']}: {todo['title'][:30]}")
        print(f"    프로젝트: {todo['project']}, 요청자: {todo['requester']}")
        print(f"    마감: D-{days_left}, 우선순위: {todo['priority']}")

print("\n" + "=" * 80)
print("LLM 선정 시작...")
print("=" * 80 + "\n")

selector = Top3LLMSelector()
selected_ids = selector.select_top3(todos, natural_rule)
reasoning = selector.last_reasoning

print("\n" + "=" * 80)
print("선정 결과:")
print("=" * 80)
print(f"\n선정된 TODO: {selected_ids}")
print(f"\n선정 이유:\n{reasoning}")

print("\n" + "=" * 80)
print("분석:")
print("=" * 80)

# 선정된 TODO 상세 정보
for todo_id in selected_ids:
    todo = next((t for t in todos if t.get("id") == todo_id), None)
    if todo:
        deadline_str = todo.get("deadline", "")
        if deadline_str:
            deadline_dt = datetime.fromisoformat(deadline_str)
            days_left = (deadline_dt - now).days
            print(f"\n✓ {todo_id}: {todo['title']}")
            print(f"  프로젝트: {todo['project']}, 요청자: {todo['requester']}")
            print(f"  마감: D-{days_left}, 우선순위: {todo['priority']}")

# 기대 결과
print("\n" + "=" * 80)
print("기대 결과:")
print("=" * 80)
print("마감이 많이 남은 순서: todo_3 (D-20) > todo_2 (D-5) > todo_1 (D-1)")
print("todo_4는 프로젝트/요청자 조건 불일치로 제외되어야 함")
