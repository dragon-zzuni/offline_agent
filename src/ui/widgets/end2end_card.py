# -*- coding: utf-8 -*-
"""
End2End 카드 위젯 - Top-3 TODO 전용
"""
import json
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton
from PyQt6.QtCore import pyqtSignal

from ..todo_helpers import _deadline_badge, _evidence_count


class End2EndCard(QWidget):
    """Top-3 TODO를 위한 End-to-End 카드 위젯"""
    send_clicked = pyqtSignal(dict)
    hold_clicked = pyqtSignal(dict)
    snooze_clicked = pyqtSignal(dict)

    def __init__(self, todo: dict, parent=None, unread: bool = False):
        super().__init__(parent)
        self.todo = todo
        self._unread = unread
        
        # 스타일 정의
        self._unread_style = """
            QWidget { border: 1px solid #FB923C; border-radius: 10px; background: #FFF7ED; }
            QWidget:hover { border-color: #F97316; background: #FFE7D3; }
        """
        self._read_style = """
            QWidget { border: 1px solid #E5E7EB; border-radius: 10px; background: #FFFFFF; }
            QWidget:hover { border-color: #60A5FA; background: #F8FAFC; }
        """
        
        root = QVBoxLayout(self)

        self.title_label = QLabel(f"🔴 {todo.get('title','(제목없음)')}")
        self.title_label.setStyleSheet("font-weight: 700;")
        root.addWidget(self.title_label)

        chips = QHBoxLayout()
        try:
            reasons = json.loads(todo.get("evidence", "[]"))[:3] if todo.get("evidence") else []
        except Exception:
            reasons = []
        for chip in reasons:
            lbl = QLabel(f"〔{chip}〕")
            lbl.setStyleSheet("color:#374151; background:#F3F4F6; padding:2px 6px; border-radius:8px;")
            chips.addWidget(lbl)
        dl_badge = _deadline_badge(todo)
        if dl_badge:
            text, fg, bg = dl_badge
            dlabel = QLabel(f"〔{text}〕")
            dlabel.setStyleSheet(f"color:{fg}; background:{bg}; padding:2px 6px; border-radius:8px;")
            chips.addWidget(dlabel)
        ev_count = _evidence_count(todo)
        if ev_count:
            elabel = QLabel(f"〔근거:{ev_count}〕")
            elabel.setStyleSheet("color:#0F172A; background:#E2E8F0; padding:2px 6px; border-radius:8px;")
            chips.addWidget(elabel)
        chips.addStretch(1)
        root.addLayout(chips)

        self.subject = QTextEdit(todo.get("draft_subject", ""))
        self.subject.setFixedHeight(32)
        self.body = QTextEdit(todo.get("draft_body", ""))
        self.body.setFixedHeight(120)
        root.addWidget(self.subject)
        root.addWidget(self.body)

        # 초기 스타일 적용
        self._apply_style()

        btns = QHBoxLayout()
        b_send = QPushButton("보내기")
        b_hold = QPushButton("캘린더 홀드(15분)")
        b_snooz = QPushButton("스누즈")
        for b in (b_send, b_hold, b_snooz):
            b.setStyleSheet("padding:6px 10px; border-radius:6px; font-weight:600;")
        btns.addWidget(b_send)
        btns.addWidget(b_hold)
        btns.addWidget(b_snooz)
        root.addLayout(btns)

        b_send.clicked.connect(lambda: self._on_button_clicked(self.send_clicked))
        b_hold.clicked.connect(lambda: self._on_button_clicked(self.hold_clicked))
        b_snooz.clicked.connect(lambda: self._on_button_clicked(self.snooze_clicked))
        
        # 텍스트 편집 시작 시 unread 해제
        self.subject.textChanged.connect(self._on_text_changed)
        self.body.textChanged.connect(self._on_text_changed)

    def _apply_style(self):
        """현재 unread 상태에 맞는 스타일 적용"""
        if self._unread:
            self.title_label.setText("🟢 " + self.todo.get('title', '(제목없음)'))
            self.setStyleSheet(self._unread_style)
        else:
            self.title_label.setText("🔴 " + self.todo.get('title', '(제목없음)'))
            self.setStyleSheet(self._read_style)
    
    def set_unread(self, unread: bool):
        """읽음/안읽음 상태 설정
        
        Args:
            unread: True면 안읽음, False면 읽음
        """
        if self._unread != unread:
            self._unread = unread
            self._apply_style()
    
    def _on_text_changed(self):
        """텍스트 변경 시 unread 해제"""
        if self._unread:
            self.set_unread(False)
    
    def _on_button_clicked(self, signal: pyqtSignal):
        """버튼 클릭 시 unread 해제 후 시그널 발생"""
        if self._unread:
            self.set_unread(False)
        signal.emit(self._payload())

    def _payload(self) -> dict:
        payload = dict(self.todo)
        payload["draft_subject"] = self.subject.toPlainText().strip()
        payload["draft_body"] = self.body.toPlainText().strip()
        return payload
