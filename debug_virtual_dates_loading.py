#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
가상 날짜 로딩 디버깅
"""
import sys
import os
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

import logging
logging.basicConfig(level=logging.INFO)

from utils.datetime_utils import load_virtual_dates
from nlp.message_grouping import group_by_day

# 1. virtual_dates.json 로드
print("=" * 80)
print("[1] virtual_dates.json 로드 테스트")
print("=" * 80)

virtual_dates = load_virtual_dates()
print(f"로드된 항목 수: {len(virtual_dates)}")

if not virtual_dates:
    print("❌ 로드 실패!")
    sys.exit(1)

# 2. 날짜 분포 확인
print("\n[2] 날짜 분포")
date_dist = {}
for key, date_str in virtual_dates.items():
    date_key = date_str.split()[0]  # YYYY-MM-DD
    date_dist[date_key] = date_dist.get(date_key, 0) + 1

print(f"총 {len(date_dist)}개 날짜")
print(f"날짜 범위: {min(date_dist.keys())} ~ {max(date_dist.keys())}")

print("\n날짜별 분포:")
for date_key in sorted(date_dist.keys()):
    print(f"  {date_key}: {date_dist[date_key]}건")

# 3. 테스트 메시지로 그룹핑 확인
print("\n[3] 메시지 그룹핑 테스트")

# 가상의 메시지 생성 (전체 사용)
test_messages = []
for key, date_str in virtual_dates.items():  # 전체 사용
    test_messages.append({
        "msg_id": key,
        "type": "email" if key.startswith("email_") else "messenger",
        "sender": "Test",
        "content": "Test",
        "date": date_str  # 가상 날짜를 직접 사용
    })

print(f"테스트 메시지 생성: {len(test_messages)}개")

# 그룹핑
daily_groups = group_by_day(test_messages)
print(f"\n일별 그룹: {len(daily_groups)}개")
for date_key in sorted(daily_groups.keys())[:10]:
    print(f"  {date_key}: {len(daily_groups[date_key])}건")

print("\n" + "=" * 80)
print("✅ 테스트 완료")
print("=" * 80)
