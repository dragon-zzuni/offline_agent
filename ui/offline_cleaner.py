# -*- coding: utf-8 -*-
"""
오프라인 정리 모듈 - 오프라인 상태에서 메시지 정리 기능
"""
import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTableWidget, QTableWidgetItem, QHeaderView, QTextEdit,
    QGroupBox, QCheckBox, QComboBox, QSpinBox, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

from main import SmartAssistant, DEFAULT_DATASET_ROOT


class OfflineCleanupWorker(QThread):
    """오프라인 정리 작업 스레드"""
    progress_updated = pyqtSignal(int)
    status_updated = pyqtSignal(str)
    result_ready = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, cleanup_config):
        super().__init__()
        self.cleanup_config = cleanup_config
    
    def run(self):
        assistant = None
        loop = None
        try:
            self.status_updated.emit("오프라인 정리 시작...")
            
            # 비동기 작업 실행
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            limit = self.cleanup_config.get("message_limit", 20)
            dataset_root = self.cleanup_config.get("dataset_root", str(DEFAULT_DATASET_ROOT))

            assistant = SmartAssistant()
            dataset_config = {
                "dataset_root": dataset_root,
                "force_reload": True,
            }
            collect_options = {
                "messenger_limit": limit,
                "email_limit": limit,
                "overall_limit": None,
                "force_reload": True,
            }

            loop.run_until_complete(assistant.initialize(dataset_config))
            messages = loop.run_until_complete(
                assistant.collect_messages(**collect_options)
            )
            
            if not messages:
                self.error_occurred.emit("정리할 메시지가 없습니다.")
                return
            
            self.progress_updated.emit(30)
            self.status_updated.emit("메시지 분석 중...")
            
            # NLP 분석
            summarizer = assistant.summarizer
            ranker = assistant.priority_ranker
            extractor = assistant.action_extractor
            
            self.progress_updated.emit(50)
            summaries = loop.run_until_complete(
                summarizer.batch_summarize(messages[:limit])
            )
            
            self.progress_updated.emit(70)
            ranked_pairs = loop.run_until_complete(
                ranker.rank_messages(messages)
            )
            
            self.progress_updated.emit(90)
            actions = loop.run_until_complete(
                extractor.batch_extract_actions(messages[:limit])
            )
            
            # 정리 결과 생성
            cleanup_result = {
                "timestamp": datetime.now().isoformat(),
                "total_messages": len(messages),
                "summaries": [s.to_dict() for s in summaries],
                "ranked_messages": [
                    (msg, score.to_dict() if hasattr(score, "to_dict") else score)
                    for msg, score in ranked_pairs
                ],
                "actions": [a.to_dict() if hasattr(a, "to_dict") else a for a in actions],
                "cleanup_config": self.cleanup_config,
                "messages": messages,
            }
            
            self.progress_updated.emit(100)
            self.status_updated.emit("오프라인 정리 완료")
            self.result_ready.emit(cleanup_result)
            
        except Exception as e:
            self.error_occurred.emit(f"오프라인 정리 오류: {str(e)}")
        finally:
            try:
                if assistant is not None:
                    loop.run_until_complete(assistant.cleanup())
            except Exception:
                pass
            if loop is not None:
                loop.close()


class OfflineCleanupDialog(QDialog):
    """오프라인 정리 대화상자"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("오프라인 정리")
        self.setModal(True)
        self.resize(800, 600)
        
        self.init_ui()
        self.worker_thread = None
    
    def init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        
        # 제목
        title = QLabel("오프라인 메시지 정리")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # 설정 그룹
        settings_group = QGroupBox("정리 설정")
        settings_layout = QVBoxLayout(settings_group)
        
        # 메시지 수집 개수
        settings_layout.addWidget(QLabel("수집할 메시지 개수:"))
        self.message_limit = QSpinBox()
        self.message_limit.setRange(1, 100)
        self.message_limit.setValue(20)
        settings_layout.addWidget(self.message_limit)
        
        # 정리 옵션
        self.include_summaries = QCheckBox("메시지 요약 포함")
        self.include_summaries.setChecked(True)
        settings_layout.addWidget(self.include_summaries)
        
        self.include_priorities = QCheckBox("우선순위 분석 포함")
        self.include_priorities.setChecked(True)
        settings_layout.addWidget(self.include_priorities)
        
        self.include_actions = QCheckBox("액션 추출 포함")
        self.include_actions.setChecked(True)
        settings_layout.addWidget(self.include_actions)
        
        layout.addWidget(settings_group)
        
        # 결과 표시 영역
        results_group = QGroupBox("정리 결과")
        results_layout = QVBoxLayout(results_group)
        
        # 결과 테이블
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels([
            "플랫폼", "발신자", "내용", "우선순위", "액션"
        ])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        results_layout.addWidget(self.results_table)
        
        # 상세 결과
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setMaximumHeight(150)
        self.details_text.setPlaceholderText("상세 결과가 여기에 표시됩니다.")
        results_layout.addWidget(self.details_text)
        
        layout.addWidget(results_group)
        
        # 버튼
        button_layout = QHBoxLayout()
        
        self.start_button = QPushButton("🧹 정리 시작")
        self.start_button.clicked.connect(self.start_cleanup)
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        button_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("⏹️ 중지")
        self.stop_button.clicked.connect(self.stop_cleanup)
        self.stop_button.setEnabled(False)
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        button_layout.addWidget(self.stop_button)
        
        self.save_button = QPushButton("💾 결과 저장")
        self.save_button.clicked.connect(self.save_results)
        self.save_button.setEnabled(False)
        button_layout.addWidget(self.save_button)
        
        self.close_button = QPushButton("❌ 닫기")
        self.close_button.clicked.connect(self.accept)
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
        
        # 상태 표시
        self.status_label = QLabel("준비됨")
        self.status_label.setStyleSheet("color: #666; padding: 5px;")
        layout.addWidget(self.status_label)
    
    def start_cleanup(self):
        """정리 시작"""
        cleanup_config = {
            "message_limit": self.message_limit.value(),
            "include_summaries": self.include_summaries.isChecked(),
            "include_priorities": self.include_priorities.isChecked(),
            "include_actions": self.include_actions.isChecked()
        }
        
        # UI 상태 변경
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.save_button.setEnabled(False)
        
        # 워커 스레드 시작
        self.worker_thread = OfflineCleanupWorker(cleanup_config)
        self.worker_thread.progress_updated.connect(self.update_progress)
        self.worker_thread.status_updated.connect(self.status_label.setText)
        self.worker_thread.result_ready.connect(self.handle_result)
        self.worker_thread.error_occurred.connect(self.handle_error)
        self.worker_thread.start()
    
    def stop_cleanup(self):
        """정리 중지"""
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.terminate()
            self.worker_thread.wait()
        
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status_label.setText("중지됨")
    
    def update_progress(self, value):
        """진행률 업데이트"""
        self.status_label.setText(f"진행률: {value}%")
    
    def handle_result(self, result):
        """결과 처리"""
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.save_button.setEnabled(True)
        self.status_label.setText("정리 완료")
        
        # 결과 테이블 업데이트
        self.update_results_table(result)
        
        # 상세 결과 업데이트
        self.update_details_text(result)
        
        # 결과 저장
        self.last_result = result
    
    def handle_error(self, error_message):
        """오류 처리"""
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status_label.setText("오류 발생")
        
        QMessageBox.critical(self, "오류", error_message)
    
    def update_results_table(self, result):
        """결과 테이블 업데이트"""
        ranked_messages = result["ranked_messages"]
        actions = result["actions"]
        
        self.results_table.setRowCount(len(ranked_messages))
        
        for i, (msg, priority) in enumerate(ranked_messages):
            self.results_table.setItem(i, 0, QTableWidgetItem(msg["platform"]))
            self.results_table.setItem(i, 1, QTableWidgetItem(msg["sender"]))
            
            content = msg["content"][:50] + "..." if len(msg["content"]) > 50 else msg["content"]
            self.results_table.setItem(i, 2, QTableWidgetItem(content))
            
            self.results_table.setItem(i, 3, QTableWidgetItem(priority["priority_level"]))
            
            # 해당 메시지의 액션 개수
            msg_actions = [a for a in actions if a["source_message_id"] == msg["msg_id"]]
            self.results_table.setItem(i, 4, QTableWidgetItem(str(len(msg_actions))))
    
    def update_details_text(self, result):
        """상세 결과 텍스트 업데이트"""
        details = "📊 오프라인 정리 결과\n"
        details += "=" * 40 + "\n\n"
        
        details += f"총 메시지: {result['total_messages']}개\n"
        details += f"요약: {len(result['summaries'])}개\n"
        details += f"우선순위 분석: {len(result['ranked_messages'])}개\n"
        details += f"액션 추출: {len(result['actions'])}개\n\n"
        
        # 우선순위별 통계
        priority_stats = {"high": 0, "medium": 0, "low": 0}
        for _, priority in result["ranked_messages"]:
            priority_stats[priority["priority_level"]] += 1
        
        details += "우선순위 분포:\n"
        details += f"  🔴 High: {priority_stats['high']}개\n"
        details += f"  🟡 Medium: {priority_stats['medium']}개\n"
        details += f"  🟢 Low: {priority_stats['low']}개\n\n"
        
        # 상위 액션들
        if result["actions"]:
            details += "추출된 액션 (상위 5개):\n"
            for i, action in enumerate(result["actions"][:5], 1):
                details += f"  {i}. {action['action_type']}: {action['title']}\n"
        
        self.details_text.setText(details)
    
    def save_results(self):
        """결과 저장"""
        if not hasattr(self, 'last_result'):
            QMessageBox.warning(self, "저장 오류", "저장할 결과가 없습니다.")
            return
        
        try:
            filename = f"offline_cleanup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.last_result, f, ensure_ascii=False, indent=2)
            
            QMessageBox.information(self, "저장 완료", f"결과가 {filename}에 저장되었습니다.")
            
        except Exception as e:
            QMessageBox.critical(self, "저장 오류", f"저장 중 오류가 발생했습니다: {e}")
