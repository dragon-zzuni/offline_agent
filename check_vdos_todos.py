#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""VDOS todos_cache.db 확인"""

import sqlite3
from collections import Counter

# 올바른 DB 경로
DB_PATH = r"C:\Users\USER\Desktop\virtual-office-orchestration\virtualoffice\src\virtualoffice\todos_cache.db"

def check_todos():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        print(f"\n{'='*80}")
        print(f"VDOS TODO 데이터베이스 분석")
        print(f"경로: {DB_PATH}")
        print(f"{'='*80}\n")
        
        # 전체 TODO 개수
        cursor.execute("SELECT COUNT(*) FROM todos")
        total_count = cursor.fetchone()[0]
        print(f"📊 전체 TODO 개수: {total_count}\n")
        
        if total_count == 0:
            print("⚠️  TODO가 하나도 없습니다!")
            conn.close()
            return
        
        # 페르소나별 통계
        cursor.execute("""
            SELECT persona_name, COUNT(*) as count
            FROM todos
            GROUP BY persona_name
            ORDER BY count DESC
        """)
        
        print(f"{'페르소나':<20} {'TODO 개수':<10}")
        print(f"{'-'*80}")
        
        for persona_name, count in cursor.fetchall():
            print(f"{persona_name or '(없음)':<20} {count:<10}")
        
        print(f"\n{'='*80}")
        
        # 프로젝트 태그 통계
        cursor.execute("""
            SELECT project_tag, COUNT(*) as count
            FROM todos
            GROUP BY project_tag
            ORDER BY count DESC
            LIMIT 10
        """)
        
        print(f"\n프로젝트 태그 통계 (상위 10개):")
        print(f"{'-'*80}")
        
        for project_tag, count in cursor.fetchall():
            tag_display = project_tag if project_tag else "❌ 태그 없음"
            print(f"  {tag_display}: {count}개")
        
        # 태그 없는 TODO 비율
        cursor.execute("SELECT COUNT(*) FROM todos WHERE project_tag IS NULL OR project_tag = ''")
        no_tag_count = cursor.fetchone()[0]
        
        print(f"\n{'='*80}")
        print(f"태그 통계:")
        print(f"  - 태그 있음: {total_count - no_tag_count}개 ({((total_count - no_tag_count) / total_count * 100):.1f}%)")
        print(f"  - 태그 없음: {no_tag_count}개 ({(no_tag_count / total_count * 100):.1f}%)")
        print(f"{'='*80}\n")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

if __name__ == "__main__":
    check_todos()
