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
        self._update_label_widths()
    
    def eventFilter(self, obj, event):
        if event.type() in (QEvent.Type.Resize, QEvent.Type.Show):
            self._update_label_widths()
        return False
    
    def _update_label_widths(self):
        """다이얼로그 현재 너비에 맞춰 라벨 최대 너비 조정"""
        dialog_width = self.dialog.width() or self.dialog.sizeHint().width() or 600
        available = max(dialog_width - self.padding * 4 - 40, 220)  # 여백 + 스크롤바
        for lbl in self.labels:
            lbl.setMaximumWidth(available)
