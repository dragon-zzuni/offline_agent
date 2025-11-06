# -*- coding: utf-8 -*-
"""
메시지 컨트롤러

메시지 수집 및 분석 로직을 담당합니다.
"""
import logging
from typing import List, Dict, Optional
from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class MessageController(QObject):
    """메시지 수집 및 분석 컨트롤러"""
    
    # 시그널 정의
    collection_started = pyqtSignal()
    collection_finished = pyqtSignal(dict)  # result
    collection_failed = pyqtSignal(str)  # error_message
    analysis_started = pyqtSignal(int)  # message_count
    analysis_finished = pyqtSignal(list, list)  # todos, analysis_results
    analysis_failed = pyqtSignal(str)  # error_message
    progress_updated = pyqtSignal(int, int)  # current, total
    
    def __init__(self, assistant, parent=None):
        super().__init__(parent)
        self.assistant = assistant
        self.worker_thread = None
        self.collected_messages = []
        self.analysis_results = []
        self.todos = []
    
    def start_collection(self, options: Optional[Dict] = None):
        """메시지 수집 시작"""
        try:
            logger.info("메시지 수집 시작")
            self.collection_started.emit()
            
            # 실제 수집 로직은 WorkerThread에서 처리
            # 여기서는 시그널만 발생
            
        except Exception as e:
            logger.error(f"메시지 수집 시작 오류: {e}")
            self.collection_failed.emit(str(e))
    
    def stop_collection(self):
        """메시지 수집 중지"""
        try:
            if self.worker_thread and self.worker_thread.isRunning():
                logger.info("메시지 수집 중지 요청")
                self.worker_thread.stop()
                self.worker_thread.wait(3000)
                self.worker_thread = None
        except Exception as e:
            logger.error(f"메시지 수집 중지 오류: {e}")
    
    def analyze_messages(self, messages: List[Dict]):
        """메시지 분석"""
        try:
            logger.info(f"메시지 분석 시작: {len(messages)}개")
            self.analysis_started.emit(len(messages))
            
            # 실제 분석 로직
            # TODO: SmartAssistant를 사용한 분석 구현
            
        except Exception as e:
            logger.error(f"메시지 분석 오류: {e}")
            self.analysis_failed.emit(str(e))
    
    def get_collected_messages(self) -> List[Dict]:
        """수집된 메시지 반환"""
        return self.collected_messages
    
    def get_analysis_results(self) -> List[Dict]:
        """분석 결과 반환"""
        return self.analysis_results
    
    def get_todos(self) -> List[Dict]:
        """TODO 목록 반환"""
        return self.todos
    
    def clear_data(self):
        """데이터 초기화"""
        self.collected_messages = []
        self.analysis_results = []
        self.todos = []
