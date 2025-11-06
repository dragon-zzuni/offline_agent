# -*- coding: utf-8 -*-
"""
Chip 위젯
"""
from PyQt6.QtWidgets import QLabel


class Chip(QLabel):
    """칩 스타일 라벨"""
    def __init__(self, text, bg="#E5E7EB", fg="#111827"):
        super().__init__(text)
        self.setProperty("chip", True)
        self.setStyleSheet(f"""
            QLabel[chip="true"] {{
                background: {bg};
                color: {fg};
                padding: 2px 8px;
                border-radius: 999px;
                font-weight: 600;
            }}
        """)
