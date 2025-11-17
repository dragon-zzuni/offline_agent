# -*- coding: utf-8 -*-
"""
이메일 패널 - TODO 가치가 있는 이메일만 필터링하여 표시

LLM을 사용하여 이메일을 분석하고 TODO로 변환할 가치가 있는지 판단합니다.
"""
import os
import logging
from typing import Dict, List, Optional
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, 
    QListWidgetItem, QPushButton, QTextEdit, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal

from config.settings import LLM_CONFIG

logger = logging.getLogger(__name__)


class EmailItem(QWidget):
    """이메일 아이템 위젯"""
    
    def __init__(self, email: Dict, parent=None):
        super().__init__(parent)
        self.email = email
        self._init_ui()
    
    def _init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)
        
        # 최소 높이 설정으로 레이아웃 깨짐 방지
        self.setMinimumHeight(120)
        
        # 상단: 제목 + 발신자
        top = QHBoxLayout()
        
        subject = self.email.get("subject", "제목 없음")
        subject_label = QLabel(subject)
        subject_label.setStyleSheet("font-weight:700; color:#1F2937;")
        top.addWidget(subject_label, 1)
        
        sender = self.email.get("sender", "")
        sender_label = QLabel(f"발신: {sender}")
        sender_label.setStyleSheet("color:#6B7280; background:#F3F4F6; padding:2px 8px; border-radius:8px;")
        top.addWidget(sender_label, 0)
        
        layout.addLayout(top)
        
        # 중간: 간단한 내용 미리보기
        body = self.email.get("body", "")
        preview = body[:100] + "..." if len(body) > 100 else body
        preview_label = QLabel(preview)
        preview_label.setStyleSheet("color:#6B7280; background:#F9FAFB; padding:6px 10px; border-radius:6px; border:1px solid #E5E7EB;")
        preview_label.setWordWrap(True)
        layout.addWidget(preview_label)
        
        # 하단: 메타 정보
        meta = QHBoxLayout()
        
        timestamp = self.email.get("timestamp", "")
        if timestamp:
            time_label = QLabel(f"수신: {timestamp}")
            time_label.setStyleSheet("color:#9CA3AF; font-size:11px;")
            meta.addWidget(time_label)
        
        meta.addStretch(1)
        layout.addLayout(meta)
        
        # 스타일
        self.setStyleSheet("""
            QWidget {
                border: 1px solid #D1D5DB;
                border-radius: 10px;
                background: #FFFFFF;
            }
            QWidget:hover {
                border-color: #9CA3AF;
                background: #F9FAFB;
            }
        """)


class EmailPanel(QWidget):
    """이메일 패널 - TODO 리스트에 없는 이메일 표시"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.emails: List[Dict] = []
        self.todo_message_ids: set = set()  # TODO에 포함된 메시지 ID 추적
        self._init_ui()
    
    def _init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 헤더
        header = QHBoxLayout()
        title = QLabel("📧 수신 메일")
        title.setStyleSheet("font-size:16px; font-weight:700; color:#1F2937;")
        header.addWidget(title)
        
        self.count_label = QLabel("0건")
        self.count_label.setStyleSheet("color:#6B7280; background:#F3F4F6; padding:4px 12px; border-radius:12px;")
        header.addWidget(self.count_label)
        
        header.addStretch(1)
        layout.addLayout(header)
        
        # 설명
        desc = QLabel("TODO 리스트에 포함되지 않은 이메일만 표시됩니다")
        desc.setStyleSheet("color:#6B7280; font-size:12px; margin-bottom:8px;")
        layout.addWidget(desc)
        
        # 이메일 리스트
        self.email_list = QListWidget()
        self.email_list.setUniformItemSizes(False)
        self.email_list.setSpacing(8)
        self.email_list.setStyleSheet("""
            QListWidget {
                background: #F8FAFC;
                border: none;
            }
            QListWidget::item {
                padding: 0px;
                margin: 4px;
                background: transparent;
            }
        """)
        self.email_list.itemClicked.connect(self._on_email_clicked)
        layout.addWidget(self.email_list)
    
    def clear(self):
        """이메일 목록 초기화"""
        self.emails = []
        self.email_list.clear()
        self.count_label.setText("0건")
    
    def update_emails(self, emails: List[Dict], todo_items: List[Dict] = None):
        """이메일 목록 업데이트
        
        Args:
            emails: 이메일 딕셔너리 리스트
            todo_items: TODO 아이템 리스트 (선택사항)
        """
        self.emails = emails
        self.email_list.clear()
        self.todo_message_ids = set()
        
        # TODO 아이템에서 메시지 ID 추출
        if todo_items:
            for todo in todo_items:
                source_msg = todo.get("source_message", {})
                if isinstance(source_msg, str):
                    import json
                    try:
                        source_msg = json.loads(source_msg)
                    except:
                        source_msg = {}
                msg_id = source_msg.get("id") or source_msg.get("msg_id")
                if msg_id:
                    self.todo_message_ids.add(msg_id)
        
        if not emails:
            self.count_label.setText("0건")
            return
        
        # TODO에 없는 이메일만 필터링
        filtered_emails = self._filter_non_todo_emails(emails)
        
        # 최신순 정렬 (timestamp/date 기준 내림차순)
        # 여러 필드명 지원: timestamp, date, sent_at
        def get_sort_key(email):
            from datetime import datetime
            time_value = email.get('timestamp') or email.get('date') or email.get('sent_at') or ''
            
            # 날짜 문자열을 datetime 객체로 변환하여 정확한 정렬
            if time_value:
                try:
                    # 여러 날짜 형식 지원
                    for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d']:
                        try:
                            return datetime.strptime(time_value, fmt)
                        except ValueError:
                            continue
                    # 파싱 실패 시 문자열 그대로 반환
                    return time_value
                except:
                    return time_value
            return datetime.min  # 날짜 없으면 가장 오래된 것으로 처리
        
        filtered_emails.sort(key=get_sort_key, reverse=True)
        
        # 정렬 결과 로깅 (디버깅용)
        if filtered_emails:
            logger.info(f"📧 이메일 정렬 완료 (최신순, 총 {len(filtered_emails)}건):")
            for i, email in enumerate(filtered_emails[:3], 1):  # 상위 3개만 로깅
                time_val = email.get('timestamp') or email.get('date') or email.get('sent_at') or 'No date'
                subject = email.get('subject', 'No subject')[:40]
                logger.info(f"  {i}. {subject} - {time_val}")
        
        self.count_label.setText(f"{len(filtered_emails)}건")
        
        for email in filtered_emails:
            item = QListWidgetItem(self.email_list)
            widget = EmailItem(email, self)
            # 위젯의 실제 크기를 계산하여 설정
            widget.adjustSize()
            item.setSizeHint(widget.sizeHint())
            self.email_list.addItem(item)
            self.email_list.setItemWidget(item, widget)
    
    def _filter_non_todo_emails(self, emails: List[Dict]) -> List[Dict]:
        """TODO 리스트에 없는 이메일만 필터링
        
        Args:
            emails: 전체 이메일 리스트
            
        Returns:
            TODO에 없는 이메일 리스트
        """
        filtered = []
        for email in emails:
            # 이메일 타입만 필터링
            if email.get("type", "").lower() != "email":
                continue
            
            # TODO에 포함되지 않은 이메일만 추가
            msg_id = email.get("msg_id") or email.get("id")
            if msg_id and msg_id not in self.todo_message_ids:
                filtered.append(email)
        
        logger.info(f"📧 TODO에 없는 이메일: {len(filtered)}건 (전체 {len(emails)}건)")
        return filtered
    
    def _on_email_clicked(self, item: QListWidgetItem):
        """이메일 클릭 이벤트 핸들러
        
        클릭된 이메일의 상세 내용을 다이얼로그로 표시합니다.
        """
        try:
            # 클릭된 아이템의 인덱스 가져오기
            row = self.email_list.row(item)
            
            # TODO에 없는 이메일 목록에서 해당 이메일 찾기
            filtered_emails = self._filter_non_todo_emails(self.emails)
            
            if row < 0 or row >= len(filtered_emails):
                logger.warning(f"유효하지 않은 이메일 인덱스: {row}")
                return
            
            email = filtered_emails[row]
            
            # MessageDetailDialog를 사용하여 이메일 상세 표시
            from .message_detail_dialog import MessageDetailDialog
            
            # 단일 이메일을 위한 요약 그룹 데이터 생성
            summary_group = {
                "period_label": email.get("subject", "이메일 상세"),
                "statistics_summary": f"발신: {email.get('sender', 'Unknown')}",
                "total_messages": 1,
                "email_count": 1,
                "messenger_count": 0
            }
            
            # 다이얼로그 생성 및 표시
            dialog = MessageDetailDialog(summary_group, [email], self)
            dialog.exec()
            
        except Exception as e:
            logger.error(f"이메일 클릭 처리 오류: {e}", exc_info=True)
            QMessageBox.warning(
                self,
                "오류",
                f"이메일을 표시하는 중 오류가 발생했습니다:\n{str(e)}"
            )
    

