"""A clean income / essential / want / leftover summary panel."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel

from ...core.budget import BudgetSummary
from ...core.money import format_money


class MoneySummary(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("moneySummary")
        grid = QGridLayout(self)
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(8)
        self._rows: dict[str, QLabel] = {}
        labels = [
            ("income", "Income"),
            ("essential", "Essential spending"),
            ("want", "Wants"),
            ("leftover", "Leftover"),
        ]
        for row, (key, text) in enumerate(labels):
            name = QLabel(text)
            name.setObjectName(f"summaryName_{key}")
            value = QLabel("—")
            value.setObjectName(f"summaryValue_{key}")
            value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            grid.addWidget(name, row, 0)
            grid.addWidget(value, row, 1)
            self._rows[key] = value
        self._review = QLabel("")
        self._review.setObjectName("summaryReview")
        grid.addWidget(self._review, len(labels), 0, 1, 2)

    def update_summary(self, summary: BudgetSummary, currency: str) -> None:
        self._rows["income"].setText(format_money(summary.income_cents, currency))
        self._rows["essential"].setText(format_money(summary.essential_cents, currency))
        self._rows["want"].setText(format_money(summary.want_cents, currency))
        leftover = summary.leftover_cents
        self._rows["leftover"].setText(format_money(leftover, currency))
        self._rows["leftover"].setProperty("negative", leftover < 0)
        self._rows["leftover"].style().unpolish(self._rows["leftover"])
        self._rows["leftover"].style().polish(self._rows["leftover"])
        if summary.needs_review_count:
            self._review.setText(
                f"⚠ {summary.needs_review_count} transaction(s) awaiting your review "
                "aren't counted yet — confirm them for an accurate leftover."
            )
        else:
            self._review.setText("")
