"""
틱 히스토리 다이얼로그

VirtualOffice 시뮬레이션의 틱별 활동 히스토리를 표시하는 다이얼로그입니다.
"""

import logging
from typing import List, Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHeaderView, QWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ..integrations.models import TickHistoryEntry

logger = logging.getLogger(__name__)


class TickHistoryDialog(QDialog):
    """틱 히스토리 다이얼로그
    
    최근 틱별 활동 요약을 테이블 형식으로 표시합니다.
    """
    
    def __init__(self, parent: Optional[QWidget] = None):
        """TickHistoryDialog 초기화
        
        Args:
            parent: 부모 위젯 (선택적)
        """
        super().__init__(parent)
        
        self.setWindowTitle("틱 히스토리")
        self.setMinimumSize(700, 500)
        
        self._setup_ui()
        
        logger.info("TickHistoryDialog 초기화 완료")
    
    def _setup_ui(self) -> None:
        """UI 구성"""
        layout = QVBoxLayout(self)
        
        # 헤더
        header_layout = QHBoxLayout()
        
        title_label = QLabel("📊 틱별 활동 히스토리")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # 통계 레이블
        self.stats_label = QLabel("총 0개 틱")
        header_layout.addWidget(self.stats_label)
        
        layout.addLayout(header_layout)
        
        # 테이블
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "틱 번호",
            "시뮬레이션 시간",
            "이메일",
            "메시지",
            "총 항목"
        ])
        
        # 테이블 설정
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        # 컬럼 너비 조정
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        
        layout.addWidget(self.table)
        
        # 하단 버튼
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        refresh_btn = QPushButton("🔄 새로고침")
        refresh_btn.clicked.connect(self.refresh_requested)
        button_layout.addWidget(refresh_btn)
        
        close_btn = QPushButton("닫기")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def set_history(self, history: List[TickHistoryEntry]) -> None:
        """틱 히스토리 설정
        
        Args:
            history: 틱 히스토리 목록 (최신순)
        """
        self.table.setRowCount(0)
        
        if not history:
            self.stats_label.setText("총 0개 틱")
            return
        
        # 통계 업데이트
        total_emails = sum(entry.email_count for entry in history)
        total_messages = sum(entry.message_count for entry in history)
        self.stats_label.setText(
            f"총 {len(history)}개 틱 | "
            f"이메일 {total_emails}개 | "
            f"메시지 {total_messages}개"
        )
        
        # 테이블 채우기
        for entry in history:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            # 틱 번호
            tick_item = QTableWidgetItem(str(entry.tick))
            tick_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 0, tick_item)
            
            # 시뮬레이션 시간
            sim_time_item = QTableWidgetItem(self._format_sim_time(entry.sim_time))
            self.table.setItem(row, 1, sim_time_item)
            
            # 이메일 수
            email_item = QTableWidgetItem(str(entry.email_count))
            email_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if entry.email_count > 0:
                email_item.setForeground(Qt.GlobalColor.blue)
            self.table.setItem(row, 2, email_item)
            
            # 메시지 수
            message_item = QTableWidgetItem(str(entry.message_count))
            message_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if entry.message_count > 0:
                message_item.setForeground(Qt.GlobalColor.darkGreen)
            self.table.setItem(row, 3, message_item)
            
            # 총 항목 수
            total_item = QTableWidgetItem(str(entry.total_count))
            total_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if entry.total_count > 0:
                font = total_item.font()
                font.setBold(True)
                total_item.setFont(font)
            self.table.setItem(row, 4, total_item)
        
        logger.info(f"틱 히스토리 표시: {len(history)}개 항목")
    
    def _format_sim_time(self, sim_time: str) -> str:
        """시뮬레이션 시간 포맷팅
        
        Args:
            sim_time: ISO 8601 형식 시간 문자열
        
        Returns:
            str: 포맷팅된 시간 문자열
        """
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(sim_time.replace('Z', '+00:00'))
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception as e:
            logger.warning(f"시간 포맷팅 실패: {e}")
            return sim_time
    
    def refresh_requested(self) -> None:
        """새로고침 요청 (서브클래스에서 오버라이드)"""
        pass
