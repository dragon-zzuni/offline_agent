# -*- coding: utf-8 -*-
"""
Top-3 규칙 설정 다이얼로그
"""
from typing import Dict, Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QFormLayout, QDoubleSpinBox,
    QDialogButtonBox, QTextEdit, QCheckBox
)

# TOP3_RULE_DEFAULT는 services에서 import
from src.services import TOP3_RULE_DEFAULT


class Top3RuleDialog(QDialog):
    """Top-3 가중치 조정 다이얼로그"""
    def __init__(self, current_rules: Dict[str, float], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Top-3 기준 설정")
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)
        desc = QLabel("각 가중치를 조정하면 Top-3 선정 점수에 바로 반영됩니다.")
        desc.setWordWrap(True)
        desc.setStyleSheet("color:#374151;")
        layout.addWidget(desc)

        form = QFormLayout()

        self.priority_high = QDoubleSpinBox()
        self.priority_high.setRange(0.1, 10.0)
        self.priority_high.setSingleStep(0.1)
        self.priority_high.setDecimals(1)

        self.priority_medium = QDoubleSpinBox()
        self.priority_medium.setRange(0.1, 10.0)
        self.priority_medium.setSingleStep(0.1)
        self.priority_medium.setDecimals(1)

        self.priority_low = QDoubleSpinBox()
        self.priority_low.setRange(0.1, 10.0)
        self.priority_low.setSingleStep(0.1)
        self.priority_low.setDecimals(1)

        self.deadline_emphasis = QDoubleSpinBox()
        self.deadline_emphasis.setRange(0.0, 168.0)
        self.deadline_emphasis.setSingleStep(1.0)
        self.deadline_emphasis.setDecimals(1)

        self.evidence_per_item = QDoubleSpinBox()
        self.evidence_per_item.setRange(0.0, 1.0)
        self.evidence_per_item.setSingleStep(0.05)
        self.evidence_per_item.setDecimals(2)

        self.evidence_max_bonus = QDoubleSpinBox()
        self.evidence_max_bonus.setRange(0.0, 5.0)
        self.evidence_max_bonus.setSingleStep(0.1)
        self.evidence_max_bonus.setDecimals(2)

        form.addRow("High 우선순위 가중치", self.priority_high)
        form.addRow("Medium 우선순위 가중치", self.priority_medium)
        form.addRow("Low 우선순위 가중치", self.priority_low)
        form.addRow("마감 임박 보너스 (기본 24)", self.deadline_emphasis)
        form.addRow("근거 1개당 보너스", self.evidence_per_item)
        form.addRow("근거 보너스 최대치", self.evidence_max_bonus)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._apply_initial(current_rules)

    def _apply_initial(self, rules: Dict[str, float]) -> None:
        self.priority_high.setValue(rules.get("priority_high", TOP3_RULE_DEFAULT["priority_high"]))
        self.priority_medium.setValue(rules.get("priority_medium", TOP3_RULE_DEFAULT["priority_medium"]))
        self.priority_low.setValue(rules.get("priority_low", TOP3_RULE_DEFAULT["priority_low"]))
        self.deadline_emphasis.setValue(rules.get("deadline_emphasis", TOP3_RULE_DEFAULT["deadline_emphasis"]))
        self.evidence_per_item.setValue(rules.get("evidence_per_item", TOP3_RULE_DEFAULT["evidence_per_item"]))
        self.evidence_max_bonus.setValue(rules.get("evidence_max_bonus", TOP3_RULE_DEFAULT["evidence_max_bonus"]))

    def rules(self) -> Dict[str, float]:
        return {
            "priority_high": self.priority_high.value(),
            "priority_medium": self.priority_medium.value(),
            "priority_low": self.priority_low.value(),
            "deadline_emphasis": self.deadline_emphasis.value(),
            "deadline_base": TOP3_RULE_DEFAULT["deadline_base"],
            "evidence_per_item": self.evidence_per_item.value(),
            "evidence_max_bonus": self.evidence_max_bonus.value(),
        }


class Top3NaturalRuleDialog(QDialog):
    """자연어 규칙 입력 다이얼로그"""
    def __init__(self, parent=None, seed_text: Optional[str] = None, summary_text: Optional[str] = None):
        super().__init__(parent)
        self.setWindowTitle("자연어 규칙 입력")
        self.setMinimumSize(420, 320)

        layout = QVBoxLayout(self)
        info = QLabel(
            "자연어로 Top-3 우선순위 규칙을 입력하세요.\n"
            "예) \"박부장님 메일은 최우선\" 또는 \"버그 보고서는 우선순위 높게\""
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        if summary_text:
            summary_box = QTextEdit()
            summary_box.setReadOnly(True)
            summary_box.setPlainText(summary_text)
            summary_box.setStyleSheet("background:#F3F4F6; color:#1F2937;")
            summary_box.setFixedHeight(90)
            layout.addWidget(summary_box)

        self.editor = QTextEdit()
        self.editor.setPlaceholderText("규칙을 입력하세요...")
        if seed_text:
            self.editor.setPlainText(seed_text)
        layout.addWidget(self.editor, 1)

        self.reset_box = QCheckBox("기존 규칙 초기화")
        layout.addWidget(self.reset_box)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def rule_text(self) -> str:
        return self.editor.toPlainText().strip()

    def should_reset(self) -> bool:
        return self.reset_box.isChecked()
