"""Monthly income vs cost summary with a category breakdown."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...core import repository as repo
from ...core.budget import summarize
from ...core.db import clear_transactions
from ...core.money import format_money
from ..widgets.money_summary import MoneySummary

_MONTH_NAMES = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


class SummaryPage(QWidget):
    dataChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        header = QHBoxLayout()
        header.addWidget(QLabel("<h2>Monthly summary</h2>"))
        header.addStretch(1)
        header.addWidget(QLabel("Month:"))
        self._month = QComboBox()
        self._month.currentIndexChanged.connect(self._on_month_changed)
        header.addWidget(self._month)
        layout.addLayout(header)

        self._summary = MoneySummary()
        layout.addWidget(self._summary)

        layout.addWidget(QLabel("<b>Spending by category</b>"))
        self._table = QTableWidget(0, 2)
        self._table.setHorizontalHeaderLabels(["Category", "Amount"])
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self._table, 1)

        footer = QHBoxLayout()
        footer.addStretch(1)
        self._clear_btn = QPushButton("Clear imported data")
        self._clear_btn.setObjectName("dangerButton")
        self._clear_btn.setToolTip(
            "Delete all imported statements and transactions. Your goals and slider "
            "settings are kept."
        )
        self._clear_btn.clicked.connect(self._clear_imported)
        footer.addWidget(self._clear_btn)
        layout.addLayout(footer)

    def refresh(self) -> None:
        months = repo.available_months() or [repo.latest_month()]
        self._month.blockSignals(True)
        current = self._month.currentData()
        self._month.clear()
        for (y, m) in months:
            self._month.addItem(f"{_MONTH_NAMES[m]} {y}", (y, m))
        # Restore selection if still present, else newest.
        idx = 0
        if current in months:
            idx = months.index(current)
        self._month.setCurrentIndex(idx)
        self._month.blockSignals(False)
        self._render()

    def _on_month_changed(self, _index: int) -> None:
        self._render()

    def _clear_imported(self) -> None:
        confirm = QMessageBox.question(
            self, "Clear imported data?",
            "This deletes all imported statements and transactions. Your goals, "
            "investment slider settings and learned rules are kept. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            clear_transactions()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Could not clear", str(exc))
            return
        self.refresh()
        self.dataChanged.emit()

    def _render(self) -> None:
        data = self._month.currentData()
        if not data:
            return
        year, month = data
        currency = repo.get_setting("currency", "CAD") or "CAD"
        txns = repo.transactions_for_month(year, month)
        summary = summarize(txns)
        self._summary.update_summary(summary, currency)

        rows = sorted(summary.by_category.items(), key=lambda kv: kv[1], reverse=True)
        self._table.setRowCount(len(rows))
        for r, (name, cents) in enumerate(rows):
            self._table.setItem(r, 0, QTableWidgetItem(name))
            amt = QTableWidgetItem(format_money(cents, currency))
            amt.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._table.setItem(r, 1, amt)
