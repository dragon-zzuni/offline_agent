#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VDOS 데이터베이스 스키마 확인
"""
import sqlite3
from pathlib import Path

def check_database_schema():
    """데이터베이스 스키마 확인"""
    
    # 데이터베이스 경로
    vdos_db_path = Path("../virtualoffice/src/virtualoffice/vdos.db")
    
    if not vdos_db_path.exists():
        print(f"❌ 데이터베이스 파일을 찾을 수 없습니다: {vdos_db_path}")
        return
    
    try:
        conn = sqlite3.connect(vdos_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 모든 테이블 목록 가져오기
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]
        
        print(f"📊 데이터베이스 테이블 목록 ({len(tables)}개):")
        for table in tables:
            print(f"  - {table}")
        
        print("\n" + "="*60)
        
        # 각 테이블의 스키마 확인
        for table in tables:
            print(f"\n📋 테이블: {table}")
            print("-" * 40)
            
            # 테이블 스키마 확인
            cursor.execute(f"PRAGMA table_info({table})")
            columns = cursor.fetchall()
            
            print("컬럼 정보:")
            for col in columns:
                col_name = col[1]
                col_type = col[2]
                not_null = "NOT NULL" if col[3] else ""
                default_val = f"DEFAULT {col[4]}" if col[4] is not None else ""
                primary_key = "PRIMARY KEY" if col[5] else ""
                
                print(f"  {col_name:20} {col_type:15} {not_null:10} {default_val:15} {primary_key}")
            
            # 데이터 개수 확인
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"데이터 개수: {count:,}개")
                
                # 샘플 데이터 확인 (처음 3개)
                if count > 0:
                    cursor.execute(f"SELECT * FROM {table} LIMIT 3")
                    samples = cursor.fetchall()
                    if samples:
                        print("샘플 데이터:")
                        for i, sample in enumerate(samples):
                            print(f"  {i+1}. {dict(sample)}")
                
            except Exception as e:
                print(f"데이터 조회 오류: {e}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 데이터베이스 스키마 확인 오류: {e}")

if __name__ == "__main__":
    check_database_schema()