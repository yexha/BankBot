"""Review & override transactions.

By default this shows the queue of transactions the system wasn't sure about
(cash withdrawals, e-transfers, unrecognized descriptions). Every row lets you set
it to Income OR an expense label, so a mis-read direction (a deposit parsed as a
withdrawal, or vice-versa) can always be corrected. Toggle "Show all transactions"
to override anything that was already classified.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ...core import repository as repo
from ...core.money import format_money
from ...core.review_service import apply_review_decision


def _signed_amount(txn) -> str:
    money = format_money(txn.amount_cents, txn.currency)
    incoming = txn.is_income or (txn.essential_want == "income")
    return ("+" if incoming else "−") + money


def _current_label(txn) -> str:
    if txn.review_status == "needs_review":
        return "needs review"
    if txn.is_income or txn.essential_want == "income":
        return "Income"
    ew = txn.essential_want
    if ew == "essential":
        return f"Essential · {txn.category or 'Uncategorized'}"
    if ew == "want":
        return f"Want · {txn.category or 'Uncategorized'}"
    if ew == "ignore":
        return "Ignored"
    return txn.category or "Unclassified"


class ReviewPage(QWidget):
    dataChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.addWidget(QLabel("<h2>Review &amp; override</h2>"))
        self._intro = QLabel(
            "Set each item to Income or an expense type. If something was read the wrong "
            "way (a deposit counted as spending, or vice-versa), fix it here — we'll "
            "remember the payee for next time."
        )
        self._intro.setWordWrap(True)
        outer.addWidget(self._intro)

        self._show_all = QCheckBox("Show all transactions (override anything, not just the queue)")
        self._show_all.toggled.connect(self.refresh)
        outer.addWidget(self._show_all)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._container = QWidget()
        self._list = QVBoxLayout(self._container)
        self._list.addStretch(1)
        self._scroll.setWidget(self._container)
        outer.addWidget(self._scroll, 1)

    def refresh(self) -> None:
        while self._list.count() > 1:
            item = self._list.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        txns = repo.all_transactions() if self._show_all.isChecked() else repo.review_queue()
        if not txns:
            msg = ("No transactions imported yet." if self._show_all.isChecked()
                   else "🎉 Nothing to review — every transaction is classified.")
            empty = QLabel(msg)
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._list.insertWidget(0, empty)
            return
        for txn in txns:
            self._list.insertWidget(self._list.count() - 1, self._make_row(txn))

    def _make_row(self, txn) -> QFrame:
        row = QFrame()
        row.setObjectName("reviewRow")
        v = QVBoxLayout(row)

        header = QLabel(
            f"<b>{_signed_amount(txn)}</b> — {txn.description}  "
            f"<span style='color:gray'>({txn.txn_date:%b %d, %Y})</span>"
        )
        header.setWordWrap(True)
        v.addWidget(header)

        note = QLabel(f"Currently: <b>{_current_label(txn)}</b>")
        note.setObjectName("reviewHint")
        note.setWordWrap(True)
        v.addWidget(note)

        controls = QHBoxLayout()
        remember = QCheckBox("Remember this payee")
        remember.setChecked(True)
        controls.addWidget(remember)
        controls.addStretch(1)
        # Every row offers Income AND the expense labels, so either kind of
        # mis-classification (income<->expense) is fixable.
        for label, decision in [
            ("Income", "income"),
            ("Essential", "essential"),
            ("Want", "want"),
            ("Recurring bill", "recurring_bill"),
            ("Ignore", "ignore"),
        ]:
            btn = QPushButton(label)
            btn.clicked.connect(
                lambda _=False, tid=txn.id, d=decision, cb=remember:
                self._decide(tid, d, cb.isChecked())
            )
            controls.addWidget(btn)
        v.addLayout(controls)
        return row

    def _decide(self, txn_id: int, decision: str, remember: bool) -> None:
        try:
            apply_review_decision(txn_id, decision, remember=remember)
        except Exception as exc:  # noqa: BLE001
            self._intro.setText(f"Could not save that decision: {exc}")
            return
        self.refresh()
        self.dataChanged.emit()
