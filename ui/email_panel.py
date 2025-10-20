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
        layout.setContentsMargins(12, 8, 12, 8)
        
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
    """이메일 패널 - TODO 가치가 있는 이메일만 표시"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.emails: List[Dict] = []
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
        desc = QLabel("TODO로 변환할 가치가 있는 이메일만 표시됩니다")
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
        layout.addWidget(self.email_list)
    
    def clear(self):
        """이메일 목록 초기화"""
        self.emails = []
        self.email_list.clear()
        self.count_label.setText("0건")
    
    def update_emails(self, emails: List[Dict]):
        """이메일 목록 업데이트
        
        Args:
            emails: 이메일 딕셔너리 리스트
        """
        self.emails = emails
        self.email_list.clear()
        
        if not emails:
            self.count_label.setText("0건")
            return
        
        # TODO 가치가 있는 이메일만 필터링
        filtered_emails = self._filter_todo_worthy_emails(emails)
        
        self.count_label.setText(f"{len(filtered_emails)}건")
        
        for email in filtered_emails:
            item = QListWidgetItem(self.email_list)
            widget = EmailItem(email, self)
            item.setSizeHint(widget.sizeHint())
            self.email_list.addItem(item)
            self.email_list.setItemWidget(item, widget)
    
    def _filter_todo_worthy_emails(self, emails: List[Dict]) -> List[Dict]:
        """TODO 가치가 있는 이메일만 필터링
        
        간단한 휴리스틱으로 필터링:
        - 요청/질문/확인이 포함된 이메일
        - 마감일이 언급된 이메일
        - 회의/미팅 관련 이메일
        
        Args:
            emails: 전체 이메일 리스트
            
        Returns:
            필터링된 이메일 리스트
            
        Examples:
            >>> emails = [
            ...     {"subject": "회의 요청", "body": "내일 오전 10시 회의 부탁드립니다"},
            ...     {"subject": "안녕하세요", "body": "잘 지내시나요?"}
            ... ]
            >>> filtered = self._filter_todo_worthy_emails(emails)
            >>> len(filtered)
            1
        """
        # TODO 관련 키워드 정의 (카테고리별 분류)
        keywords = {
            "request": ["요청", "request", "부탁", "확인", "check"],
            "review": ["검토", "review", "승인", "approval", "결재"],
            "meeting": ["회의", "meeting", "미팅", "일정", "schedule"],
            "urgent": ["마감", "deadline", "긴급", "urgent", "asap"],
            "inquiry": ["질문", "question", "문의", "inquiry"]
        }
        
        # 모든 키워드를 하나의 리스트로 통합
        all_keywords = [kw for category in keywords.values() for kw in category]
        
        filtered = []
        for email in emails:
            # 제목과 본문을 소문자로 변환하여 검색
            subject = (email.get("subject") or "").lower()
            body = (email.get("body") or "").lower()
            content = f"{subject} {body}"
            
            # 키워드 매칭 (하나라도 포함되면 필터링)
            if any(kw in content for kw in all_keywords):
                filtered.append(email)
                logger.debug(
                    f"이메일 필터링 통과: {email.get('subject', '제목없음')[:30]}"
                )
        
        logger.info(f"📧 이메일 필터링 완료: {len(emails)}개 → {len(filtered)}개")
        return filtered
