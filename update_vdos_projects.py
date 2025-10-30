#!/usr/bin/env python3
"""
VDOS 데이터베이스의 TODO에 프로젝트 태그 할당
"""

import sqlite3
import os
import sys

# 프로젝트 루트를 sys.path에 추가
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

from src.services.project_tag_service import ProjectTagService

# VDOS 데이터베이스 경로
DB_PATH = "../virtualoffice/src/virtualoffice/todos_cache.db"

def update_vdos_projects():
    """VDOS 데이터베이스의 TODO에 프로젝트 할당"""
    if not os.path.exists(DB_PATH):
        print(f"❌ 데이터베이스 파일이 없습니다: {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # project 컬럼이 있는지 확인
    cur.execute("PRAGMA table_info(todos)")
    columns = [col[1] for col in cur.fetchall()]
    
    if 'project' not in columns:
        print("📝 project 컬럼 추가 중...")
        cur.execute("ALTER TABLE todos ADD COLUMN project TEXT")
        conn.commit()
        print("✅ project 컬럼 추가 완료")
    
    # 프로젝트 태그 서비스 초기화
    project_service = ProjectTagService()
    
    # 모든 TODO 조회
    cur.execute("SELECT id, title, description, source_message FROM todos")
    todos = cur.fetchall()
    
    print(f"📊 {len(todos)}개 TODO에 프로젝트 할당 시작...")
    
    # 프로젝트 목록
    projects = ["BRIDGE", "CARE", "HEAL", "LINK", "WC", "WD"]
    
    updated_count = 0
    for i, (todo_id, title, description, source_message) in enumerate(todos):
        try:
            # 순환 할당 (테스트용)
            project = projects[i % len(projects)]
            
            # 데이터베이스 업데이트
            cur.execute("UPDATE todos SET project = ? WHERE id = ?", (project, todo_id))
            updated_count += 1
            
            if updated_count % 10 == 0:
                print(f"  진행률: {updated_count}/{len(todos)} ({(updated_count/len(todos)*100):.1f}%)")
                
        except Exception as e:
            print(f"❌ TODO {todo_id} 업데이트 실패: {e}")
    
    conn.commit()
    
    # 결과 확인
    cur.execute("SELECT project, COUNT(*) FROM todos WHERE project IS NOT NULL GROUP BY project ORDER BY project")
    project_stats = cur.fetchall()
    
    print(f"\n✅ {updated_count}개 TODO에 프로젝트 할당 완료")
    print("\n📊 프로젝트별 TODO 통계:")
    for project, count in project_stats:
        print(f"  {project}: {count}개")
    
    conn.close()

if __name__ == "__main__":
    print("🏷️ VDOS 데이터베이스 프로젝트 태그 업데이트")
    print("=" * 50)
    update_vdos_projects()