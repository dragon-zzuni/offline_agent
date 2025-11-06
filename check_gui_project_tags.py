#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI에서 로드된 TODO 프로젝트 태그 확인
"""

import sys
import os
import sqlite3
from collections import Counter

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

def check_gui_project_tags():
    """GUI TODO 캐시에서 프로젝트 태그 확인"""
    print("🔍 GUI TODO 캐시 프로젝트 태그 분석")
    
    # TODO 캐시 DB 경로
    cache_db_path = "../virtualoffice/src/virtualoffice/todos_cache.db"
    
    if not os.path.exists(cache_db_path):
        print(f"❌ TODO 캐시 DB를 찾을 수 없습니다: {cache_db_path}")
        return
    
    print(f"📁 TODO 캐시 DB: {cache_db_path}")
    
    try:
        conn = sqlite3.connect(cache_db_path)
        cursor = conn.cursor()
        
        # 테이블 목록 확인
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"📋 테이블 목록: {[table[0] for table in tables]}")
        
        # TODO 테이블 스키마 확인
        cursor.execute("PRAGMA table_info(todos)")
        columns = cursor.fetchall()
        print(f"📊 TODO 테이블 컬럼: {[col[1] for col in columns]}")
        
        # 전체 TODO 수 확인
        cursor.execute("SELECT COUNT(*) FROM todos")
        total_count = cursor.fetchone()[0]
        print(f"📋 총 TODO 수: {total_count}")
        
        # 프로젝트 태그별 분포 확인
        cursor.execute("SELECT project, COUNT(*) FROM todos GROUP BY project ORDER BY COUNT(*) DESC")
        tag_distribution = cursor.fetchall()
        
        print("\n📊 프로젝트 태그별 TODO 분포:")
        used_tags = set()
        for tag, count in tag_distribution:
            print(f"  - {tag}: {count}개")
            if tag and tag not in ['UNKNOWN', 'GENERAL']:
                used_tags.add(tag)
        
        print(f"\n✅ 실제 사용된 프로젝트 태그: {used_tags}")
        
        # 최근 TODO 몇 개 샘플 확인
        cursor.execute("SELECT title, project, requester FROM todos ORDER BY created_at DESC LIMIT 10")
        recent_todos = cursor.fetchall()
        
        print("\n📝 최근 TODO 샘플:")
        for i, (title, tag, requester) in enumerate(recent_todos, 1):
            print(f"  {i}. [{tag}] {title[:50]}... (요청자: {requester})")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 데이터베이스 오류: {e}")

if __name__ == "__main__":
    check_gui_project_tags()