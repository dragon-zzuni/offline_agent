#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
백그라운드 분석 로그 실시간 모니터링
"""
import subprocess
import time
import threading
import sys
import os
from pathlib import Path

def monitor_logs():
    """로그 실시간 모니터링"""
    print("🔍 Smart Assistant 백그라운드 분석 로그 모니터링 시작")
    print("=" * 60)
    print("📋 모니터링 대상:")
    print("  - TODO 추출 로직")
    print("  - 백그라운드 분석 결과 처리")
    print("  - 중첩된 리스트 구조 처리")
    print("  - VDOS 데이터 연동")
    print("=" * 60)
    
    # Smart Assistant 실행
    try:
        print("🚀 Smart Assistant 실행 중...")
        
        # GUI 모드로 실행 (백그라운드에서 로그 출력)
        process = subprocess.Popen(
            [sys.executable, "run_gui.py"],
            cwd="offline_agent",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        print("✅ Smart Assistant 시작됨 (PID: {})".format(process.pid))
        print("📊 실시간 로그 출력:")
        print("-" * 60)
        
        # 실시간 로그 출력
        for line in iter(process.stdout.readline, ''):
            if line:
                # 중요한 로그만 필터링
                line = line.strip()
                if any(keyword in line.lower() for keyword in [
                    'todo', 'background', 'analysis', 'extract', 'vdos', 
                    'error', 'warning', '추출', '분석', '백그라운드', '처리'
                ]):
                    timestamp = time.strftime("%H:%M:%S")
                    print(f"[{timestamp}] {line}")
                    
                    # 특별히 중요한 로그는 강조
                    if any(keyword in line.lower() for keyword in [
                        'todo 생성', 'todo 추출', 'background_analysis', 
                        'extract_todos_recursive', '잘못된 todo'
                    ]):
                        print("🔥 " + "="*50)
                        print(f"🔥 중요: {line}")
                        print("🔥 " + "="*50)
        
    except KeyboardInterrupt:
        print("\n⏹️ 모니터링 중단됨")
        if 'process' in locals():
            process.terminate()
    except Exception as e:
        print(f"❌ 모니터링 오류: {e}")

def start_virtualoffice_if_needed():
    """필요시 VirtualOffice 시작"""
    print("🔧 VirtualOffice 상태 확인...")
    
    # VDOS 데이터베이스 확인
    vdos_db_path = Path("../virtualoffice/src/virtualoffice/vdos.db")
    if vdos_db_path.exists():
        print("✅ VDOS 데이터베이스 발견")
        return True
    else:
        print("⚠️ VDOS 데이터베이스 없음 - VirtualOffice를 먼저 실행해주세요")
        return False

def main():
    """메인 실행 함수"""
    print("🎯 Smart Assistant 백그라운드 분석 실시간 모니터링")
    print("=" * 70)
    
    # VirtualOffice 상태 확인
    if not start_virtualoffice_if_needed():
        print("❌ VirtualOffice가 실행되지 않았습니다.")
        print("💡 먼저 VirtualOffice를 실행한 후 다시 시도해주세요.")
        return
    
    print("\n📝 모니터링 안내:")
    print("  - Ctrl+C로 모니터링 중단")
    print("  - Smart Assistant GUI에서 '새 메시지 분석' 또는 '재분석' 실행")
    print("  - TODO 추출 과정을 실시간으로 확인")
    print("\n⏳ 3초 후 모니터링 시작...")
    time.sleep(3)
    
    # 로그 모니터링 시작
    monitor_logs()

if __name__ == "__main__":
    main()