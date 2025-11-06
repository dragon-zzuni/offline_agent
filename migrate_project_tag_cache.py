# -*- coding: utf-8 -*-
"""
프로젝트 태그 캐시 DB 마이그레이션
classification_reason 컬럼 추가
"""
import sqlite3
from pathlib import Path

# 캐시 DB 경로
cache_db_path = Path("../virtualoffice/src/virtualoffice/project_tags_cache.db")

if not cache_db_path.exists():
    print(f"❌ 캐시 DB를 찾을 수 없습니다: {cache_db_path}")
    exit(1)

print(f"📂 캐시 DB 발견: {cache_db_path}")

conn = sqlite3.connect(str(cache_db_path))
cur = conn.cursor()

try:
    # 기존 컬럼 확인
    cur.execute("PRAGMA table_info(project_tag_cache)")
    columns = [col[1] for col in cur.fetchall()]
    
    print(f"\n현재 컬럼: {columns}")
    
    if 'classification_reason' in columns:
        print("\n✅ classification_reason 컬럼이 이미 존재합니다!")
    else:
        print("\n🔄 classification_reason 컬럼 추가 중...")
        cur.execute("""
            ALTER TABLE project_tag_cache 
            ADD COLUMN classification_reason TEXT
        """)
        conn.commit()
        print("✅ 컬럼 추가 완료!")
    
    # 업데이트된 컬럼 확인
    cur.execute("PRAGMA table_info(project_tag_cache)")
    columns = [col[1] for col in cur.fetchall()]
    print(f"\n업데이트된 컬럼: {columns}")
    
    # 통계 출력
    cur.execute("SELECT COUNT(*) FROM project_tag_cache")
    count = cur.fetchone()[0]
    print(f"\n📊 캐시된 항목 수: {count}개")
    
except Exception as e:
    print(f"\n❌ 마이그레이션 실패: {e}")
    conn.rollback()
finally:
    conn.close()

print("\n✅ 마이그레이션 완료!")
