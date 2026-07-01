"""Review queue: confirm the transactions the system wasn't sure about.

Cash withdrawals, e-transfers and unrecognized descriptions land here so they are
never silently mis-tagged. Confirming remembers the payee for next time.
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


class ReviewPage(QWidget):
    dataChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.addWidget(QLabel("<h2>Review queue</h2>"))
        self._intro = QLabel(
            "We weren't sure about these. Tell us what each one is — we'll remember the "
            "payee so you won't be asked again unless it changes."
        )
        self._intro.setWordWrap(True)
        outer.addWidget(self._intro)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._container = QWidget()
        self._list = QVBoxLayout(self._container)
        self._list.addStretch(1)
        self._scroll.setWidget(self._container)
        outer.addWidget(self._scroll, 1)

    def refresh(self) -> None:
        # Clear existing rows (keep the trailing stretch).
        while self._list.count() > 1:
            item = self._list.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        queue = repo.review_queue()
        if not queue:
            empty = QLabel("🎉 Nothing to review — every transaction is classified.")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._list.insertWidget(0, empty)
            return
        for txn in queue:
            self._list.insertWidget(self._list.count() - 1, self._make_row(txn))

    def _make_row(self, txn) -> QFrame:
        row = QFrame()
        row.setObjectName("reviewRow")
        v = QVBoxLayout(row)

        header = QLabel(
            f"<b>{format_money(txn.amount_cents, txn.currency)}</b> — "
            f"{txn.description}  <span style='color:gray'>({txn.txn_date:%b %d, %Y})</span>"
        )
        header.setWordWrap(True)
        v.addWidget(header)

        is_credit = txn.direction == "credit"
        if is_credit:
            hint = "Incoming money — is this income (e.g. a paycheck) or should we ignore it?"
        else:
            hint = {
                "Cash Withdrawal": "Cash withdrawal — what was it for?",
                "Transfer": "Transfer / e-transfer — is this a bill (e.g. rent) or a want?",
            }.get(txn.category or "", "We don't recognize this — how should we count it?")
        note = QLabel(hint)
        note.setObjectName("reviewHint")
        note.setWordWrap(True)
        v.addWidget(note)

        controls = QHBoxLayout()
        remember = QCheckBox("Remember this payee")
        remember.setChecked(True)
        controls.addWidget(remember)
        controls.addStretch(1)
        # Credits get an Income option; debits get the expense labels.
        if is_credit:
            actions = [("Income", "income"), ("Ignore", "ignore")]
        else:
            actions = [
                ("Essential", "essential"),
                ("Want", "want"),
                ("Recurring bill", "recurring_bill"),
                ("Ignore", "ignore"),
            ]
        for label, decision in actions:
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
