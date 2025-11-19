# -*- coding: utf-8 -*-
"""
마감일 조건만 준 경우 Top3 선정 확인
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
        "project": "CI",
        "project_full_name": "CareBridge Integration",
        "requester": "boyeon.kim@example.com",
        "type": "review",
        "source_type": "messenger",
        "priority": "medium",
        "deadline": (now + timedelta(days=5)).isoformat(),  # D-5
        "status": "pending"
    },
    {
        "id": "todo_3",
        "title": "장기 프로젝트 계획",
        "project": "CC",
        "project_full_name": "Care Connect 2.0",
        "requester": "doyoon.lee@example.com",
        "type": "meeting",
        "source_type": "email",
        "priority": "low",
        "deadline": (now + timedelta(days=20)).isoformat(),  # D-20
        "status": "pending"
    },
    {
        "id": "todo_4",
        "title": "중간 작업",
        "project": "PN",
        "project_full_name": "Project NOVA",
        "requester": "yujun.park@example.com",
        "type": "task",
        "source_type": "email",
        "priority": "medium",
        "deadline": (now + timedelta(days=10)).isoformat(),  # D-10
        "status": "pending"
    },
    {
        "id": "todo_5",
        "title": "매우 긴급",
        "project": "PL",
        "project_full_name": "Project LUMINA",
        "requester": "hyungwoo.jeon@example.com",
        "type": "deadline",
        "source_type": "email",
        "priority": "high",
        "deadline": (now + timedelta(hours=12)).isoformat(),  # D-0 (12시간)
        "status": "pending"
    }
]

# 자연어 규칙: 마감일 조건만 (프로젝트/요청자/유형 조건 없음)
natural_rule = "마감이 많이 남은 것을 우선적으로 선정해주세요"

print("=" * 80)
print("테스트: 마감일 조건만 준 경우")
print("=" * 80)
print(f"\n자연어 규칙: {natural_rule}")
print("(프로젝트, 요청자, 유형 조건 없음)\n")

print("TODO 리스트:")
for todo in todos:
    deadline_str = todo.get("deadline", "")
    if deadline_str:
        deadline_dt = datetime.fromisoformat(deadline_str)
        days_left = (deadline_dt - now).days
        hours_left = (deadline_dt - now).total_seconds() / 3600
        
        if days_left == 0:
            deadline_display = f"D-0 ({hours_left:.1f}시간)"
        else:
            deadline_display = f"D-{days_left}"
            
        print(f"  - {todo['id']}: {todo['title'][:30]}")
        print(f"    프로젝트: {todo['project']}, 요청자: {todo['requester'].split('@')[0]}")
        print(f"    유형: {todo['type']}, 마감: {deadline_display}, 우선순위: {todo['priority']}")

print("\n" + "=" * 80)
print("폴백 모드 선정 (LLM 없이)...")
print("=" * 80 + "\n")

selector = Top3LLMSelector()
selected_ids = selector.select_top3(todos, natural_rule)
reasoning = selector.last_reasoning

print("\n" + "=" * 80)
print("선정 결과:")
print("=" * 80)
print(f"\n선정된 TODO: {selected_ids}")
if reasoning:
    print(f"\n선정 이유:\n{reasoning}")

print("\n" + "=" * 80)
print("선정된 TODO 상세:")
print("=" * 80)

# 마감일 순으로 정렬해서 표시
selected_todos = []
for todo_id in selected_ids:
    todo = next((t for t in todos if t.get("id") == todo_id), None)
    if todo:
        selected_todos.append(todo)

selected_todos.sort(key=lambda t: datetime.fromisoformat(t.get("deadline", "")))

for todo in selected_todos:
    deadline_str = todo.get("deadline", "")
    if deadline_str:
        deadline_dt = datetime.fromisoformat(deadline_str)
        days_left = (deadline_dt - now).days
        hours_left = (deadline_dt - now).total_seconds() / 3600
        
        if days_left == 0:
            deadline_display = f"D-0 ({hours_left:.1f}시간)"
        else:
            deadline_display = f"D-{days_left}"
            
        print(f"\n✓ {todo['id']}: {todo['title']}")
        print(f"  프로젝트: {todo['project']}, 요청자: {todo['requester'].split('@')[0]}")
        print(f"  유형: {todo['type']}, 마감: {deadline_display}, 우선순위: {todo['priority']}")

# 기대 결과
print("\n" + "=" * 80)
print("기대 결과 vs 실제 결과:")
print("=" * 80)
print("\n기대: 마감이 많이 남은 순서")
print("  1위: todo_3 (D-20)")
print("  2위: todo_4 (D-10)")
print("  3위: todo_2 (D-5)")

print("\n실제 선정된 TODO를 마감일 순으로 정렬:")
for i, todo in enumerate(selected_todos, 1):
    deadline_dt = datetime.fromisoformat(todo.get("deadline", ""))
    days_left = (deadline_dt - now).days
    hours_left = (deadline_dt - now).total_seconds() / 3600
    
    if days_left == 0:
        deadline_display = f"D-0 ({hours_left:.1f}시간)"
    else:
        deadline_display = f"D-{days_left}"
    print(f"  {i}위: {todo['id']} ({deadline_display})")

print("\n" + "=" * 80)
print("분석:")
print("=" * 80)
print("폴백 모드는 '마감일 임박도'로 점수를 계산합니다:")
print("  - 24시간 이내: +2점")
print("  - 72시간 이내: +1점")
print("  - 그 외: 0점")
print("\n따라서 '마감이 많이 남은 것'이라는 규칙과 정반대로 동작합니다!")
print("D-20, D-10, D-5는 모두 72시간 이상 남아서 마감일 점수가 0점이고,")
print("우선순위 점수만으로 선정됩니다 (high=3, medium=2, low=1)")
