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
        root = QVBoxLayout(self)

        title = QLabel(f"🔴 {todo.get('title','(제목없음)')}")
        title.setStyleSheet("font-weight: 700;")
        root.addWidget(title)

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

        if unread:
            title.setText("🟢 " + (todo.get('title','(제목없음)')))
            self.setStyleSheet("""
                QWidget { border: 1px solid #FB923C; border-radius: 10px; background: #FFF7ED; }
                QWidget:hover { border-color: #F97316; background: #FFE7D3; }
            """)
        else:
            self.setStyleSheet("""
                QWidget { border: 1px solid #E5E7EB; border-radius: 10px; background: #FFFFFF; }
                QWidget:hover { border-color: #60A5FA; background: #F8FAFC; }
            """)

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

        b_send.clicked.connect(lambda: self.send_clicked.emit(self._payload()))
        b_hold.clicked.connect(lambda: self.hold_clicked.emit(self._payload()))
        b_snooz.clicked.connect(lambda: self.snooze_clicked.emit(self._payload()))

    def _payload(self) -> dict:
        payload = dict(self.todo)
        payload["draft_subject"] = self.subject.toPlainText().strip()
        payload["draft_body"] = self.body.toPlainText().strip()
        return payload
