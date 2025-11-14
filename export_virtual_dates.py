#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
VDOS DB의 virtual_date를 JSON으로 export
"""
import sqlite3
import json
import os

def main():
    # VDOS DB 연결
    conn = sqlite3.connect('virtualoffice/src/virtualoffice/vdos.db')
    cursor = conn.cursor()
    
    virtual_dates = {}
    
    # 1. 이메일 virtual_date 추출
    print("=== 이메일 virtual_date 추출 ===")
    cursor.execute("SELECT id, virtual_date FROM emails WHERE virtual_date IS NOT NULL")
    emails = cursor.fetchall()
    for email_id, virtual_date in emails:
        key = f"email_{email_id}"
        virtual_dates[key] = virtual_date
    print(f"✅ {len(emails)}개 이메일")
    
    # 2. 메시지 virtual_date 추출 (room_slug 포함)
    print("\n=== 메시지 virtual_date 추출 ===")
    cursor.execute("""
        SELECT cm.id, cm.virtual_date, cm.room_id, cr.slug
        FROM chat_messages cm
        LEFT JOIN chat_rooms cr ON cm.room_id = cr.id
        WHERE cm.virtual_date IS NOT NULL
    """)
    messages = cursor.fetchall()
    for msg_id, virtual_date, room_id, room_slug in messages:
        # msg_id 형식: chat_{room_slug}_{id}
        if room_slug:
            key = f"chat_{room_slug}_{msg_id}"
        else:
            key = f"message_{msg_id}"  # fallback
        virtual_dates[key] = virtual_date
    print(f"✅ {len(messages)}개 메시지")
    
    conn.close()
    
    # 3. JSON 파일로 저장
    output_path = "offline_agent/data/multi_project_8week_ko/virtual_dates.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(virtual_dates, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ {output_path}에 저장 완료!")
    print(f"총 {len(virtual_dates)}개 항목")
    
    # 4. 날짜 분포 확인
    from collections import defaultdict
    date_distribution = defaultdict(int)
    for key, date_str in virtual_dates.items():
        date_key = date_str.split()[0]  # YYYY-MM-DD 부분만
        date_distribution[date_key] += 1
    
    print(f"\n=== 날짜별 분포 ===")
    for date_key in sorted(date_distribution.keys()):
        print(f"  {date_key}: {date_distribution[date_key]}건")

if __name__ == "__main__":
    main()
