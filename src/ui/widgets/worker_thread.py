# -*- coding: utf-8 -*-
"""
백그라운드 작업 스레드
"""
import asyncio
from PyQt6.QtCore import QThread, pyqtSignal


class WorkerThread(QThread):
    """백그라운드 작업 스레드"""
    progress_updated = pyqtSignal(int)
    status_updated = pyqtSignal(str)
    result_ready = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, assistant, dataset_config, collect_options):
        super().__init__()
        self.assistant = assistant
        self.dataset_config = dataset_config or {}
        self.collect_options = collect_options or {}
        self.collect_options.setdefault("force_reload", True)
        self._should_stop = False
    
    def run(self):
        try:
            # 비동기 작업을 동기적으로 실행
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            self.status_updated.emit("시스템 초기화 중...")
            loop.run_until_complete(self.assistant.initialize(self.dataset_config))
            
            # skip_collection 옵션 확인
            skip_collection = self.collect_options.get("skip_collection", False)
            
            if skip_collection:
                # 기존 메시지 사용 (수집 건너뛰기)
                self.status_updated.emit("기존 메시지 사용 중...")
                self.progress_updated.emit(20)
                messages = getattr(self.assistant, 'collected_messages', [])
                
                if not messages:
                    self.error_occurred.emit("분석할 메시지가 없습니다.")
                    return
            else:
                # 새로 메시지 수집
                self.status_updated.emit("메시지 수집 중...")
                self.progress_updated.emit(20)
                
                messages = loop.run_until_complete(
                    self.assistant.collect_messages(**self.collect_options)
                )
                
                if not messages:
                    self.error_occurred.emit("수집된 메시지가 없습니다.")
                    return
            
            self.status_updated.emit("AI 분석 중...")
            self.progress_updated.emit(50)
            
            analysis_results = loop.run_until_complete(self.assistant.analyze_messages())
            
            self.status_updated.emit("TODO 리스트 생성 중...")
            self.progress_updated.emit(80)
            todo_list = loop.run_until_complete(self.assistant.generate_todo_list(analysis_results))

            self.progress_updated.emit(100)
            self.status_updated.emit("완료")
            
            result = {
                "success": True,
                "todo_list": todo_list,
                "analysis_results": analysis_results,
                "messages": messages,
                "analysis_report_text": getattr(self.assistant, "analysis_report_text", "")
            }
            
            self.result_ready.emit(result)
            
        except Exception as e:
            self.error_occurred.emit(f"오류 발생: {str(e)}")
        finally:
            loop.close()
    
    def stop(self):
        self._should_stop = True
