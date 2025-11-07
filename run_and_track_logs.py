"""
앱 실행 후 로그 추적 스크립트
"""
import subprocess
import time
import os
import sys

def track_logs():
    print("=" * 80)
    print("Smart Assistant 실행 중...")
    print("=" * 80)
    print("\n로그에서 중복 제거 정보를 추적합니다...")
    print("앱이 실행되면 '분석 시작' 버튼을 눌러주세요.\n")
    
    # 로그 파일 경로
    log_file = "offline_agent/smart_assistant.log"
    
    # 기존 로그 파일 삭제 (새로 시작)
    if os.path.exists(log_file):
        os.remove(log_file)
        print(f"기존 로그 파일 삭제: {log_file}\n")
    
    # 앱 실행 (백그라운드)
    print("앱 실행 중... (Ctrl+C로 종료)\n")
    
    try:
        # 로그 파일이 생성될 때까지 대기
        timeout = 30
        start_time = time.time()
        while not os.path.exists(log_file):
            if time.time() - start_time > timeout:
                print(f"⚠️ {timeout}초 동안 로그 파일이 생성되지 않았습니다.")
                print("앱을 수동으로 실행해주세요: python offline_agent/run_gui.py")
                return
            time.sleep(0.5)
        
        print(f"✅ 로그 파일 생성됨: {log_file}\n")
        print("=" * 80)
        print("중복 제거 로그 추적 중... (실시간)")
        print("=" * 80)
        print()
        
        # 로그 파일 실시간 추적
        with open(log_file, 'r', encoding='utf-8') as f:
            # 파일 끝으로 이동
            f.seek(0, 2)
            
            duplicate_section = False
            
            while True:
                line = f.readline()
                if not line:
                    time.sleep(0.1)
                    continue
                
                # 중복 제거 관련 로그만 출력
                if "중복 TODO" in line or "=== 중복 제거된 TODO 샘플" in line:
                    duplicate_section = True
                    print("\n" + "🔍 " + line.strip())
                elif duplicate_section:
                    if line.strip():
                        print("   " + line.strip())
                    else:
                        duplicate_section = False
                
                # 전체 분석 완료 로그
                if "분석 완료" in line or "TODO 생성 완료" in line:
                    print("\n" + "✅ " + line.strip())
                
    except KeyboardInterrupt:
        print("\n\n로그 추적 종료")
    except Exception as e:
        print(f"\n오류 발생: {e}")

if __name__ == "__main__":
    track_logs()
