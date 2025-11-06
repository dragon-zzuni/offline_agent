#!/usr/bin/env python3
"""
파일 모니터링 시스템 - VDOS 페르소나 파일 변경 감지
"""
import os
import time
import logging
from typing import Callable, Optional, Dict, Set
from pathlib import Path
from datetime import datetime
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

logger = logging.getLogger(__name__)

class VDOSFileHandler(FileSystemEventHandler):
    """VDOS 페르소나 파일 변경을 감지하는 핸들러"""
    
    def __init__(self, callback: Callable[[Path], None]):
        """
        Args:
            callback: 파일 변경 시 호출될 콜백 함수
        """
        super().__init__()
        self.callback = callback
        self.last_modified: Dict[str, float] = {}
        self.debounce_time = 1.0  # 1초 디바운스
    
    def on_modified(self, event):
        """파일 수정 이벤트 처리"""
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        
        # VDOS 페르소나 파일만 처리
        if not self._is_vdos_persona_file(file_path):
            return
        
        # 디바운스 처리 (짧은 시간 내 중복 이벤트 방지)
        current_time = time.time()
        file_key = str(file_path)
        
        if file_key in self.last_modified:
            if current_time - self.last_modified[file_key] < self.debounce_time:
                return
        
        self.last_modified[file_key] = current_time
        
        logger.info(f"VDOS 페르소나 파일 변경 감지: {file_path.name}")
        
        try:
            self.callback(file_path)
        except Exception as e:
            logger.error(f"파일 변경 콜백 실행 실패: {e}")
    
    def on_created(self, event):
        """파일 생성 이벤트 처리"""
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        
        if self._is_vdos_persona_file(file_path):
            logger.info(f"새 VDOS 페르소나 파일 생성: {file_path.name}")
            
            try:
                self.callback(file_path)
            except Exception as e:
                logger.error(f"파일 생성 콜백 실행 실패: {e}")
    
    def _is_vdos_persona_file(self, file_path: Path) -> bool:
        """VDOS 페르소나 파일인지 확인"""
        if file_path.suffix.lower() != '.json':
            return False
        
        filename = file_path.name.lower()
        return filename.startswith('vdos-personas')


class VDOSFileMonitor:
    """VDOS 페르소나 파일 모니터링 클래스"""
    
    def __init__(self, watch_directory: str, callback: Callable[[Path], None]):
        """
        Args:
            watch_directory: 모니터링할 디렉토리 경로
            callback: 파일 변경 시 호출될 콜백 함수
        """
        self.watch_directory = Path(watch_directory)
        self.callback = callback
        self.observer: Optional[Observer] = None
        self.handler: Optional[VDOSFileHandler] = None
        self.is_monitoring = False
        
        # 디렉토리 존재 확인
        if not self.watch_directory.exists():
            logger.warning(f"모니터링 디렉토리가 존재하지 않습니다: {self.watch_directory}")
    
    def start_monitoring(self) -> bool:
        """파일 모니터링을 시작합니다"""
        if self.is_monitoring:
            logger.warning("이미 모니터링이 실행 중입니다")
            return True
        
        if not self.watch_directory.exists():
            logger.error(f"모니터링 디렉토리가 존재하지 않습니다: {self.watch_directory}")
            return False
        
        try:
            self.handler = VDOSFileHandler(self.callback)
            self.observer = Observer()
            self.observer.schedule(
                self.handler, 
                str(self.watch_directory), 
                recursive=False
            )
            
            self.observer.start()
            self.is_monitoring = True
            
            logger.info(f"VDOS 파일 모니터링 시작: {self.watch_directory}")
            return True
            
        except Exception as e:
            logger.error(f"파일 모니터링 시작 실패: {e}")
            return False    
    d
ef stop_monitoring(self) -> bool:
        """파일 모니터링을 중지합니다"""
        if not self.is_monitoring:
            logger.warning("모니터링이 실행되지 않고 있습니다")
            return True
        
        try:
            if self.observer:
                self.observer.stop()
                self.observer.join(timeout=5.0)
            
            self.is_monitoring = False
            self.observer = None
            self.handler = None
            
            logger.info("VDOS 파일 모니터링 중지")
            return True
            
        except Exception as e:
            logger.error(f"파일 모니터링 중지 실패: {e}")
            return False
    
    def is_running(self) -> bool:
        """모니터링이 실행 중인지 확인"""
        return self.is_monitoring and self.observer and self.observer.is_alive()
    
    def get_status(self) -> Dict:
        """모니터링 상태 정보를 반환"""
        return {
            'is_monitoring': self.is_monitoring,
            'is_running': self.is_running(),
            'watch_directory': str(self.watch_directory),
            'directory_exists': self.watch_directory.exists(),
            'observer_alive': self.observer.is_alive() if self.observer else False
        }


class VDOSAutoReloader:
    """VDOS 데이터 자동 재로딩 클래스"""
    
    def __init__(self, data_loader, watch_directory: str):
        """
        Args:
            data_loader: VDOSDataLoader 인스턴스
            watch_directory: 모니터링할 디렉토리 경로
        """
        self.data_loader = data_loader
        self.monitor = VDOSFileMonitor(watch_directory, self._on_file_changed)
        self.reload_count = 0
        self.last_reload_time: Optional[datetime] = None
        self.reload_errors: List[str] = []
    
    def _on_file_changed(self, file_path: Path):
        """파일 변경 시 호출되는 콜백"""
        logger.info(f"VDOS 파일 변경으로 인한 자동 재로딩: {file_path.name}")
        
        try:
            # 잠시 대기 (파일 쓰기 완료 대기)
            time.sleep(0.5)
            
            # 데이터 재로딩
            success = self.data_loader.load_and_extract_all(file_path)
            
            if success:
                self.reload_count += 1
                self.last_reload_time = datetime.now()
                logger.info(f"VDOS 데이터 자동 재로딩 성공 (#{self.reload_count})")
                
                # 에러 기록 초기화
                self.reload_errors.clear()
            else:
                error_msg = f"데이터 재로딩 실패: {file_path.name}"
                self.reload_errors.append(error_msg)
                logger.error(error_msg)
                
                # 에러 기록 제한 (최대 10개)
                if len(self.reload_errors) > 10:
                    self.reload_errors = self.reload_errors[-10:]
        
        except Exception as e:
            error_msg = f"자동 재로딩 중 예외 발생: {e}"
            self.reload_errors.append(error_msg)
            logger.error(error_msg)
    
    def start(self) -> bool:
        """자동 재로딩을 시작합니다"""
        return self.monitor.start_monitoring()
    
    def stop(self) -> bool:
        """자동 재로딩을 중지합니다"""
        return self.monitor.stop_monitoring()
    
    def is_running(self) -> bool:
        """자동 재로딩이 실행 중인지 확인"""
        return self.monitor.is_running()
    
    def get_status(self) -> Dict:
        """자동 재로딩 상태 정보를 반환"""
        monitor_status = self.monitor.get_status()
        
        return {
            **monitor_status,
            'reload_count': self.reload_count,
            'last_reload_time': self.last_reload_time.isoformat() if self.last_reload_time else None,
            'recent_errors': self.reload_errors[-5:],  # 최근 5개 에러만
            'error_count': len(self.reload_errors)
        }


# 편의 함수
def create_auto_reloader(data_loader, 
                        watch_directory: str = "offline_agent/data/multi_project_8week_ko") -> VDOSAutoReloader:
    """VDOS 자동 재로더를 생성합니다"""
    return VDOSAutoReloader(data_loader, watch_directory)


if __name__ == "__main__":
    # 테스트 실행
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    
    from utils.vdos_data_loader import VDOSDataLoader
    
    logging.basicConfig(level=logging.INFO)
    
    # 데이터 로더 생성
    loader = VDOSDataLoader()
    loader.load_and_extract_all()
    
    # 자동 재로더 생성 및 시작
    auto_reloader = create_auto_reloader(loader)
    
    print("=== VDOS 파일 모니터링 테스트 ===")
    print("자동 재로딩을 시작합니다...")
    
    if auto_reloader.start():
        print("모니터링이 시작되었습니다.")
        print("VDOS 페르소나 파일을 수정해보세요.")
        print("Ctrl+C로 종료할 수 있습니다.")
        
        try:
            while True:
                time.sleep(1)
                status = auto_reloader.get_status()
                if status['reload_count'] > 0:
                    print(f"재로딩 횟수: {status['reload_count']}")
        except KeyboardInterrupt:
            print("\n모니터링을 중지합니다...")
            auto_reloader.stop()
            print("완료")
    else:
        print("모니터링 시작 실패")