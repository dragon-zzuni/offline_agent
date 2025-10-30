#!/usr/bin/env python3
"""
프로젝트 태그가 없는 TODO 분석
"""

import sys
import os
sys.path.append('.')
sys.path.append('src')

import sqlite3
import json

def analyze_missing_project_tags():
    """프로젝트 태그가 없는 TODO들 분석"""
    db_path = 'C:/Users/USER/Desktop/virtual-office-orchestration/virtualoffice/src/virtualoffice/todos_cache.db'
    
    if not os.path.exists(db_path):
        print(f"❌ 데이터베이스 파일이 없습니다: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # 전체 통계
        cur.execute('SELECT COUNT(*) FROM todos WHERE status != "done"')
        total_todos = cur.fetchone()[0]
        
        cur.execute('SELECT COUNT(*) FROM todos WHERE status != "done" AND project IS NOT NULL')
        tagged_todos = cur.fetchone()[0]
        
        untagged_todos = total_todos - tagged_todos
        
        print('=== TODO 프로젝트 태그 현황 ===')
        print(f'전체 활성 TODO: {total_todos}개')
        print(f'프로젝트 태그 있음: {tagged_todos}개 ({tagged_todos/total_todos*100:.1f}%)')
        print(f'프로젝트 태그 없음: {untagged_todos}개 ({untagged_todos/total_todos*100:.1f}%)')
        
        # 프로젝트별 분포
        cur.execute('SELECT project, COUNT(*) FROM todos WHERE status != "done" AND project IS NOT NULL GROUP BY project ORDER BY COUNT(*) DESC')
        project_stats = cur.fetchall()
        
        print('\n=== 프로젝트별 분포 ===')
        for project, count in project_stats:
            print(f'{project}: {count}개')
        
        # 프로젝트 태그가 없는 TODO들의 메시지 내용 분석
        cur.execute('SELECT id, title, source_message FROM todos WHERE status != "done" AND (project IS NULL OR project = "") LIMIT 10')
        untagged_samples = cur.fetchall()
        
        print('\n=== 프로젝트 태그가 없는 TODO 샘플 (10개) ===')
        for i, (todo_id, title, source_message) in enumerate(untagged_samples, 1):
            print(f'{i:2d}. {title}')
            
            if source_message:
                try:
                    if source_message.startswith('{'):
                        message_data = json.loads(source_message)
                        subject = message_data.get('subject', '')
                        content = message_data.get('content', '')
                        sender = message_data.get('sender', '')
                        
                        print(f'     발신자: {sender}')
                        if subject:
                            print(f'     제목: {subject[:60]}...')
                        if content:
                            print(f'     내용: {content[:60]}...')
                        
                        # 프로젝트 관련 키워드 확인
                        full_text = f"{title} {subject} {content}".lower()
                        project_keywords = [
                            'care connect', 'careconnect',
                            'health link', 'healthlink', 
                            'wellcare', 'well care',
                            'welldata', 'well data',
                            'carebridge', 'care bridge',
                            'welllink', 'well link'
                        ]
                        
                        found_keywords = [kw for kw in project_keywords if kw in full_text]
                        if found_keywords:
                            print(f'     🔍 발견된 키워드: {found_keywords}')
                        else:
                            print(f'     ❓ 프로젝트 키워드 없음')
                            
                except Exception as e:
                    print(f'     ❌ 메시지 파싱 실패: {e}')
            else:
                print(f'     ❓ 소스 메시지 없음')
            
            print()
        
        # 일반적인 TODO 유형 분석
        cur.execute('''
            SELECT title, COUNT(*) as count 
            FROM todos 
            WHERE status != "done" AND (project IS NULL OR project = "")
            GROUP BY title 
            ORDER BY count DESC 
            LIMIT 5
        ''')
        common_titles = cur.fetchall()
        
        print('=== 가장 많은 미분류 TODO 유형 ===')
        for title, count in common_titles:
            print(f'{title}: {count}개')
        
        conn.close()
        
    except Exception as e:
        print(f'❌ 분석 실패: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analyze_missing_project_tags()