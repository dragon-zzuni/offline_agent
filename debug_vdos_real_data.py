#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
실제 VDOS 데이터베이스에서 데이터 추출 및 분석
"""
import sqlite3
import json
import os
from pathlib import Path

def check_vdos_databases():
    """VDOS 데이터베이스 파일들 확인"""
    
    # 데이터베이스 경로들
    vdos_db_path = Path("../virtualoffice/src/virtualoffice/vdos.db")
    todos_cache_path = Path("../virtualoffice/src/virtualoffice/todos_cache.db")
    
    print("🔍 VDOS 데이터베이스 파일 확인")
    print("=" * 50)
    
    # vdos.db 확인
    if vdos_db_path.exists():
        print(f"✅ vdos.db 발견: {vdos_db_path.absolute()}")
        print(f"   파일 크기: {vdos_db_path.stat().st_size:,} bytes")
        analyze_vdos_db(vdos_db_path)
    else:
        print(f"❌ vdos.db 없음: {vdos_db_path.absolute()}")
    
    print()
    
    # todos_cache.db 확인
    if todos_cache_path.exists():
        print(f"✅ todos_cache.db 발견: {todos_cache_path.absolute()}")
        print(f"   파일 크기: {todos_cache_path.stat().st_size:,} bytes")
        analyze_todos_cache_db(todos_cache_path)
    else:
        print(f"❌ todos_cache.db 없음: {todos_cache_path.absolute()}")

def analyze_vdos_db(db_path):
    """vdos.db 분석"""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 테이블 목록 확인
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        print(f"📊 vdos.db 테이블 목록: {', '.join(tables)}")
        
        # 각 테이블의 데이터 개수 확인
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"   - {table}: {count:,}개 레코드")
                
                # 이메일과 메시지 테이블이면 샘플 데이터 확인
                if 'email' in table.lower() or 'message' in table.lower() or 'chat' in table.lower():
                    cursor.execute(f"SELECT * FROM {table} LIMIT 3")
                    samples = cursor.fetchall()
                    if samples:
                        print(f"     📝 {table} 샘플 컬럼: {list(samples[0].keys())}")
                        
            except Exception as e:
                print(f"   - {table}: 오류 ({e})")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ vdos.db 분석 오류: {e}")

def analyze_todos_cache_db(db_path):
    """todos_cache.db 분석"""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 테이블 목록 확인
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        print(f"📊 todos_cache.db 테이블 목록: {', '.join(tables)}")
        
        # 각 테이블의 데이터 개수 확인
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"   - {table}: {count:,}개 레코드")
                
                # TODO 관련 테이블이면 샘플 데이터 확인
                if 'todo' in table.lower():
                    cursor.execute(f"SELECT * FROM {table} LIMIT 5")
                    samples = cursor.fetchall()
                    if samples:
                        print(f"     📝 {table} 컬럼: {list(samples[0].keys())}")
                        for i, sample in enumerate(samples):
                            title = sample.get('title', 'N/A')
                            priority = sample.get('priority', 'N/A')
                            status = sample.get('status', 'N/A')
                            print(f"     {i+1}. {title[:50]}... (우선순위: {priority}, 상태: {status})")
                        
            except Exception as e:
                print(f"   - {table}: 오류 ({e})")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ todos_cache.db 분석 오류: {e}")

def extract_recent_messages():
    """최근 메시지 데이터 추출"""
    vdos_db_path = Path("virtualoffice/src/virtualoffice/vdos.db")
    
    if not vdos_db_path.exists():
        print("❌ vdos.db 파일을 찾을 수 없습니다.")
        return []
    
    try:
        conn = sqlite3.connect(vdos_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 테이블 목록 확인
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        messages = []
        
        # 이메일 테이블에서 데이터 추출
        email_tables = [t for t in tables if 'email' in t.lower()]
        for table in email_tables:
            try:
                cursor.execute(f"SELECT * FROM {table} ORDER BY id DESC LIMIT 10")
                rows = cursor.fetchall()
                for row in rows:
                    msg = dict(row)
                    msg['type'] = 'email'
                    msg['source_table'] = table
                    messages.append(msg)
                print(f"📧 {table}에서 {len(rows)}개 이메일 추출")
            except Exception as e:
                print(f"❌ {table} 추출 오류: {e}")
        
        # 채팅/메시지 테이블에서 데이터 추출
        chat_tables = [t for t in tables if any(keyword in t.lower() for keyword in ['chat', 'message', 'msg'])]
        for table in chat_tables:
            try:
                cursor.execute(f"SELECT * FROM {table} ORDER BY id DESC LIMIT 10")
                rows = cursor.fetchall()
                for row in rows:
                    msg = dict(row)
                    msg['type'] = 'messenger'
                    msg['source_table'] = table
                    messages.append(msg)
                print(f"💬 {table}에서 {len(rows)}개 메시지 추출")
            except Exception as e:
                print(f"❌ {table} 추출 오류: {e}")
        
        conn.close()
        
        print(f"\n✅ 총 {len(messages)}개 메시지 추출 완료")
        return messages
        
    except Exception as e:
        print(f"❌ 메시지 추출 오류: {e}")
        return []

def extract_existing_todos():
    """기존 TODO 데이터 추출"""
    todos_cache_path = Path("virtualoffice/src/virtualoffice/todos_cache.db")
    
    if not todos_cache_path.exists():
        print("❌ todos_cache.db 파일을 찾을 수 없습니다.")
        return []
    
    try:
        conn = sqlite3.connect(todos_cache_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # TODO 테이블에서 데이터 추출
        cursor.execute("SELECT * FROM todos ORDER BY created_at DESC LIMIT 20")
        rows = cursor.fetchall()
        
        todos = []
        for row in rows:
            todo = dict(row)
            todos.append(todo)
        
        conn.close()
        
        print(f"✅ 총 {len(todos)}개 TODO 추출 완료")
        return todos
        
    except Exception as e:
        print(f"❌ TODO 추출 오류: {e}")
        return []

def main():
    """메인 실행 함수"""
    print("🚀 실제 VDOS 데이터베이스 분석 시작")
    print("=" * 60)
    
    # 1. 데이터베이스 파일 확인
    check_vdos_databases()
    
    print("\n" + "=" * 60)
    
    # 2. 최근 메시지 추출
    print("📨 최근 메시지 데이터 추출")
    messages = extract_recent_messages()
    
    if messages:
        print(f"\n📊 추출된 메시지 샘플:")
        for i, msg in enumerate(messages[:3]):
            print(f"  {i+1}. [{msg.get('type', 'unknown')}] {msg.get('subject', msg.get('content', 'N/A'))[:50]}...")
    
    print("\n" + "=" * 60)
    
    # 3. 기존 TODO 추출
    print("📋 기존 TODO 데이터 추출")
    todos = extract_existing_todos()
    
    if todos:
        print(f"\n📊 추출된 TODO 샘플:")
        for i, todo in enumerate(todos[:5]):
            print(f"  {i+1}. [{todo.get('priority', 'N/A')}] {todo.get('title', 'N/A')[:50]}...")
    
    print("\n🎉 분석 완료!")
    
    # 결과 요약
    print(f"\n📈 요약:")
    print(f"  - 추출된 메시지: {len(messages)}개")
    print(f"  - 기존 TODO: {len(todos)}개")

if __name__ == "__main__":
    main()