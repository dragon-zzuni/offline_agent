# -*- coding: utf-8 -*-
"""
텍스트 래핑 헬퍼
"""
from PyQt6.QtCore import QObject, QEvent


class WrapHelper(QObject):
    """다이얼로그 크기에 따라 라벨 너비를 자동 조정하는 헬퍼"""
    def __init__(self, labels, padding, dialog_obj):
        super().__init__()
        self.labels = labels
        self.padding = padding
        self.dialog = dialog_obj
    
    def eventFilter(self, obj, event):
        if event.type() in (QEvent.Type.Resize, QEvent.Type.Show):
            # 다이얼로그 너비 기준으로 계산 (스크롤바 너비 고려)
            dialog_width = self.dialog.width()
            available = max(dialog_width - self.padding * 4 - 40, 200)  # 여백 + 스크롤바
            for lbl in self.labels:
                lbl.setMaximumWidth(available)
        return False
