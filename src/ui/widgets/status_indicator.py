# -*- coding: utf-8 -*-
"""
상태 표시 위젯
"""
from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import Qt


class StatusIndicator(QLabel):
    """상태 표시기"""
    def __init__(self, text="오프라인"):
        super().__init__(text)
        self.setFixedSize(100, 30)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                border: 2px solid #ccc;
                border-radius: 15px;
                background-color: #f0f0f0;
                color: #666;
                font-weight: bold;
            }
        """)
        self.current_status = "offline"
    
    def set_status(self, status):
        self.current_status = status
        if status == "online":
            self.setText("온라인")
            self.setStyleSheet("""
                QLabel {
                    border: 2px solid #4CAF50;
                    border-radius: 15px;
                    background-color: #E8F5E8;
                    color: #2E7D32;
                    font-weight: bold;
                }
            """)
        else:
            self.setText("오프라인")
            self.setStyleSheet("""
                QLabel {
                    border: 2px solid #ccc;
                    border-radius: 15px;
                    background-color: #f0f0f0;
                    color: #666;
                    font-weight: bold;
                }
            """)


class EmojiLabel(QLabel):
    """이모지 전용 라벨"""
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        f = self.font()
        f.setFamily("Segoe UI Emoji")  # 이모지 전용 폰트
        self.setFont(f)
