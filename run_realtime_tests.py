"""
VirtualOffice 실시간 기능 테스트 실행 스크립트

이 스크립트는 Phase 2의 실시간 기능들을 순차적으로 테스트합니다.

사용법:
    python offline_agent/run_realtime_tests.py [옵션]

옵션:
    --quick     빠른 테스트 (기본 기능만)
    --full      전체 테스트 (모든 시나리오)
    --gui       GUI 통합 테스트 포함
"""

import sys
import argparse
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "offline_agent"))
sys.path.insert(0, str(project_root / "offline_agent" / "src"))

from integrations.virtualoffice_client import VirtualOfficeClient


def print_header(title):
    """헤더 출력"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def check_server_connection():
    """서버 연결 확인"""
    print_header("1. VirtualOffice 서버 연결 확인")
    
    client = VirtualOfficeClient(
        email_url="http://127.0.0.1:8000",
        chat_url="http://127.0.0.1:8001",
        sim_url="http://127.0.0.1:8015"
    )
    
    try:
        status = client.test_connection()
        print(f"Email Server: {'✓' if status['email'] else '✗'}")
        print(f"Chat Server:  {'✓' if status['chat'] else '✗'}")
        print(f"Sim Manager:  {'✓' if status['sim'] else '✗'}")
        
        if not all(status.values()):
            print("\n❌ 일부 서버에 연결할 수 없습니다.")
            print("\nVirtualOffice 서버를 시작하세요:")
            print("  cd virtualoffice")
            print("  briefcase dev")
            return False
        
        print("\n✅ 모든 서버 연결 성공!")
        return True
        
    except Exception as e:
        print(f"\n❌ 연결 실패: {e}")
        print("\nVirtualOffice 서버를 시작하세요:")
        print("  cd virtualoffice")
        print("  briefcase dev")
        return False


def check_simulation_running(client):
    """시뮬레이션 실행 확인"""
    print_header("2. 시뮬레이션 상태 확인")
    
    try:
        status = client.get_simulation_status()
        print(f"현재 틱: {status.current_tick}")
        print(f"시뮬레이션 시간: {status.sim_time}")
        print(f"실행 상태: {'🟢 실행 중' if status.is_running else '🔴 정지'}")
        print(f"자동 틱: {'활성화' if status.auto_tick else '비활성화'}")
        
        if not status.is_running:
            print("\n⚠️  시뮬레이션이 정지되어 있습니다.")
            print("VirtualOffice GUI에서 시뮬레이션을 시작하세요.")
            print("일부 테스트는 건너뛸 수 있습니다.")
            return False
        
        print("\n✅ 시뮬레이션 실행 중!")
        return True
        
    except Exception as e:
        print(f"\n❌ 상태 조회 실패: {e}")
        return False


def run_quick_tests():
    """빠른 테스트 실행"""
    print_header("3. 빠른 테스트 실행")
    
    import pytest
    
    # 기본 테스트만 실행
    tests = [
        "offline_agent/test/test_realtime_integration.py::TestRealtimeIntegration::test_01_simulation_monitor_basic",
        "offline_agent/test/test_realtime_integration.py::TestRealtimeIntegration::test_02_polling_worker_basic",
    ]
    
    print("\n실행할 테스트:")
    for test in tests:
        print(f"  - {test.split('::')[-1]}")
    
    print("\npytest 실행 중...\n")
    result = pytest.main([*tests, "-v", "-s"])
    
    return result == 0


def run_full_tests():
    """전체 테스트 실행"""
    print_header("3. 전체 테스트 실행")
    
    import pytest
    
    print("\n모든 실시간 기능 테스트를 실행합니다...")
    print("예상 소요 시간: 약 2-3분\n")
    
    result = pytest.main([
        "offline_agent/test/test_realtime_integration.py",
        "-v",
        "-s"
    ])
    
    return result == 0


def run_gui_tests():
    """GUI 통합 테스트 실행"""
    print_header("4. GUI 통합 테스트")
    
    print("\nGUI 테스트는 수동으로 진행해야 합니다.")
    print("\n다음 단계를 따라주세요:")
    print("  1. python offline_agent/run_gui.py 실행")
    print("  2. VirtualOffice 연동 패널에서 '연결' 버튼 클릭")
    print("  3. 페르소나 선택 (PM 자동 선택 확인)")
    print("  4. 시뮬레이션 상태 실시간 업데이트 확인")
    print("  5. 새 메일/메시지 자동 수집 확인")
    print("  6. 틱 진행 알림 확인")
    
    print("\n자세한 내용은 다음 문서를 참고하세요:")
    print("  offline_agent/docs/REALTIME_TESTING.md")
    print("  offline_agent/docs/GUI_REALTIME_INTEGRATION.md")


def print_summary(server_ok, sim_ok, tests_ok):
    """테스트 결과 요약"""
    print_header("테스트 결과 요약")
    
    print(f"\n서버 연결: {'✅ 성공' if server_ok else '❌ 실패'}")
    print(f"시뮬레이션: {'✅ 실행 중' if sim_ok else '⚠️  정지'}")
    print(f"자동 테스트: {'✅ 통과' if tests_ok else '❌ 실패'}")
    
    if server_ok and sim_ok and tests_ok:
        print("\n🎉 모든 실시간 기능이 정상 작동합니다!")
        print("\n다음 단계:")
        print("  1. GUI에서 실시간 기능 테스트")
        print("  2. Phase 3 UI 개선 작업 진행")
    else:
        print("\n⚠️  일부 테스트가 실패했습니다.")
        print("\n문제 해결:")
        if not server_ok:
            print("  - VirtualOffice 서버를 시작하세요")
        if not sim_ok:
            print("  - VirtualOffice GUI에서 시뮬레이션을 시작하세요")
        if not tests_ok:
            print("  - 테스트 로그를 확인하고 오류를 수정하세요")
        print("\n자세한 내용:")
        print("  offline_agent/docs/REALTIME_TESTING.md")


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="VirtualOffice 실시간 기능 테스트",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예제:
  python offline_agent/run_realtime_tests.py              # 빠른 테스트
  python offline_agent/run_realtime_tests.py --full       # 전체 테스트
  python offline_agent/run_realtime_tests.py --gui        # GUI 테스트 포함
        """
    )
    
    parser.add_argument(
        "--quick",
        action="store_true",
        help="빠른 테스트 (기본 기능만)"
    )
    
    parser.add_argument(
        "--full",
        action="store_true",
        help="전체 테스트 (모든 시나리오)"
    )
    
    parser.add_argument(
        "--gui",
        action="store_true",
        help="GUI 통합 테스트 포함"
    )
    
    args = parser.parse_args()
    
    # 기본값: 빠른 테스트
    if not args.quick and not args.full:
        args.quick = True
    
    print("=" * 70)
    print("  VirtualOffice 실시간 기능 테스트")
    print("=" * 70)
    print("\n이 스크립트는 Phase 2의 실시간 기능들을 테스트합니다:")
    print("  - SimulationMonitor: 시뮬레이션 상태 모니터링")
    print("  - PollingWorker: 백그라운드 데이터 수집")
    print("  - 증분 수집: since_id 사용")
    print("  - 오류 처리: 자동 재시도")
    
    # 1. 서버 연결 확인
    client = VirtualOfficeClient(
        email_url="http://127.0.0.1:8000",
        chat_url="http://127.0.0.1:8001",
        sim_url="http://127.0.0.1:8015"
    )
    
    server_ok = check_server_connection()
    if not server_ok:
        print("\n테스트를 중단합니다.")
        sys.exit(1)
    
    # 2. 시뮬레이션 상태 확인
    sim_ok = check_simulation_running(client)
    
    # 3. 테스트 실행
    if args.full:
        tests_ok = run_full_tests()
    else:
        tests_ok = run_quick_tests()
    
    # 4. GUI 테스트 안내
    if args.gui:
        run_gui_tests()
    
    # 5. 결과 요약
    print_summary(server_ok, sim_ok, tests_ok)
    
    # 종료 코드
    sys.exit(0 if (server_ok and tests_ok) else 1)


if __name__ == "__main__":
    main()
