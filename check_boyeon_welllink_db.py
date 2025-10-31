#!/usr/bin/env python3
"""
DB에서 임보연 관련 WellLink TODO 직접 확인
"""

import sqlite3
import os
from datetime import datetime

def main():
    print("🔍 DB에서 임보연 관련 WellLink TODO 확인")
    print("=" * 60)
    
    # DB 경로
    vdos_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                           'virtualoffice', 'src', 'virtualoffice')
    db_path = os.path.join(vdos_dir, 'todos_cache.db')
    
    print(f"📁 DB 경로: {db_path}")
    
    if not os.path.exists(db_path):
        print(f"❌ DB 파일을 찾을 수 없음")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. 전체 프로젝트 통계
        print(f"\n📊 전체 프로젝트 통계:")
        cursor.execute("""
            SELECT project, COUNT(*) as count 
            FROM todos 
            WHERE project IS NOT NULL AND project != ''
            GROUP BY project 
            ORDER BY count DESC
        """)
        
        project_stats = cursor.fetchall()
        total_todos = sum(count for _, count in project_stats)
        
        for project, count in project_stats:
            percentage = (count / total_todos) * 100 if total_todos > 0 else 0
            print(f"   {project}: {count}개 ({percentage:.1f}%)")
        
        # 2. WellLink 관련 TODO (WELL, WI)
        print(f"\n🔗 WellLink 관련 TODO:")
        cursor.execute("""
            SELECT COUNT(*) 
            FROM todos 
            WHERE project IN ('WELL', 'WI')
        """)
        
        welllink_count = cursor.fetchone()[0]
        welllink_percentage = (welllink_count / total_todos) * 100 if total_todos > 0 else 0
        print(f"   총 {welllink_count}개 ({welllink_percentage:.1f}%)")
        
        # 3. WellLink TODO 상세 목록
        print(f"\n📝 WellLink TODO 상세 (최근 10개):")
        cursor.execute("""
            SELECT id, title, description, project, priority, created_at, requester
            FROM todos 
            WHERE project IN ('WELL', 'WI')
            ORDER BY created_at DESC
            LIMIT 10
        """)
        
        welllink_todos = cursor.fetchall()
        
        if welllink_todos:
            for i, (todo_id, title, description, project, priority, created_at, requester) in enumerate(welllink_todos, 1):
                print(f"\n{i}. [{project}] {priority}")
                print(f"   📄 제목: {title[:80]}...")
                if description:
                    print(f"   📝 설명: {description[:80]}...")
                print(f"   👤 요청자: {requester}")
                print(f"   📅 생성일: {created_at}")
        else:
            print("   ❌ WellLink 관련 TODO가 없습니다")
        
        # 4. 요청자별 WellLink TODO 통계
        print(f"\n👥 요청자별 WellLink TODO 통계:")
        cursor.execute("""
            SELECT requester, COUNT(*) as count 
            FROM todos 
            WHERE project IN ('WELL', 'WI')
            GROUP BY requester 
            ORDER BY count DESC
            LIMIT 10
        """)
        
        requester_stats = cursor.fetchall()
        for requester, count in requester_stats:
            print(f"   {requester}: {count}개")
        
        # 5. 임보연 관련 TODO 찾기 (요청자 또는 내용에 임보연 포함)
        print(f"\n🔍 임보연 관련 TODO:")
        cursor.execute("""
            SELECT id, title, description, project, priority, requester, created_at
            FROM todos 
            WHERE requester LIKE '%boyeon%' 
               OR requester LIKE '%임보연%'
               OR title LIKE '%임보연%'
               OR title LIKE '%boyeon%'
               OR description LIKE '%임보연%'
               OR description LIKE '%boyeon%'
            ORDER BY created_at DESC
            LIMIT 10
        """)
        
        boyeon_todos = cursor.fetchall()
        
        if boyeon_todos:
            print(f"   총 {len(boyeon_todos)}개 발견:")
            for i, (todo_id, title, description, project, priority, requester, created_at) in enumerate(boyeon_todos, 1):
                print(f"\n{i}. [{project or 'UNKNOWN'}] {priority}")
                print(f"   📄 제목: {title[:80]}...")
                if description:
                    print(f"   📝 설명: {description[:80]}...")
                print(f"   👤 요청자: {requester}")
                print(f"   📅 생성일: {created_at}")
        else:
            print("   ❌ 임보연 관련 TODO가 없습니다")
        
        # 6. 최근 생성된 TODO 확인
        print(f"\n⏰ 최근 생성된 TODO (상위 5개):")
        cursor.execute("""
            SELECT id, title, description, project, priority, requester, created_at
            FROM todos 
            ORDER BY created_at DESC
            LIMIT 5
        """)
        
        recent_todos = cursor.fetchall()
        for i, (todo_id, title, description, project, priority, requester, created_at) in enumerate(recent_todos, 1):
            print(f"\n{i}. [{project or 'UNKNOWN'}] {priority}")
            print(f"   📄 제목: {title[:60]}...")
            if description:
                print(f"   📝 설명: {description[:60]}...")
            print(f"   👤 요청자: {requester}")
            print(f"   📅 생성일: {created_at}")
        
        conn.close()
        print(f"\n✅ 분석 완료!")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()