#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
DB 마이그레이션: project_full_name 컬럼 추가

기존 todos 테이블에 project_full_name 컬럼을 추가하고,
기존 데이터의 project 코드를 기반으로 project_full_name을 채웁니다.
"""
import os
import sqlite3
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.utils.project_fullname_mapper import get_project_fullname

DB_PATH = "data/multi_project_8week_ko/todos_cache.db"


def migrate_db():
    """DB 마이그레이션 실행"""
    db_path = Path(DB_PATH)
    
    if not db_path.exists():
        print(f"❌ DB 파일이 없습니다: {db_path}")
        print("   앱을 실행하면 자동으로 생성됩니다.")
        return
    
    print(f"📂 DB 경로: {db_path}")
    
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    
    try:
        # 1. 컬럼 존재 여부 확인
        cur.execute("PRAGMA table_info(todos)")
        columns = [row[1] for row in cur.fetchall()]
        
        if "project_full_name" in columns:
            print("✅ project_full_name 컬럼이 이미 존재합니다.")
        else:
            print("➕ project_full_name 컬럼 추가 중...")
            cur.execute("ALTER TABLE todos ADD COLUMN project_full_name TEXT")
            conn.commit()
            print("✅ project_full_name 컬럼 추가 완료")
        
        # 2. 기존 데이터 업데이트
        print("\n🔄 기존 데이터 업데이트 중...")
        cur.execute("SELECT id, project FROM todos WHERE project IS NOT NULL AND project <> ''")
        rows = cur.fetchall()
        
        if not rows:
            print("   업데이트할 데이터가 없습니다.")
        else:
            updated = 0
            for todo_id, project_code in rows:
                project_fullname = get_project_fullname(project_code)
                if project_fullname:
                    cur.execute(
                        "UPDATE todos SET project_full_name = ? WHERE id = ?",
                        (project_fullname, todo_id)
                    )
                    updated += 1
            
            conn.commit()
            print(f"✅ {updated}개 TODO의 project_full_name 업데이트 완료")
        
        # 3. 결과 확인
        print("\n📊 마이그레이션 결과:")
        cur.execute("SELECT COUNT(*) FROM todos")
        total = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM todos WHERE project_full_name IS NOT NULL")
        with_fullname = cur.fetchone()[0]
        
        print(f"   전체 TODO: {total}개")
        print(f"   project_full_name 있음: {with_fullname}개")
        
        if with_fullname > 0:
            print("\n📋 샘플 데이터:")
            cur.execute(
                "SELECT project, project_full_name FROM todos "
                "WHERE project_full_name IS NOT NULL LIMIT 5"
            )
            for project, fullname in cur.fetchall():
                print(f"   {project} → {fullname}")
        
        print("\n✅ 마이그레이션 완료!")
        
    except Exception as e:
        print(f"\n❌ 마이그레이션 실패: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate_db()
