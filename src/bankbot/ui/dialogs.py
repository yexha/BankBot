"""Small dialogs, including the TFSA/FHSA account-optimization popup."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QVBoxLayout,
)

from ..core import repository as repo
from ..core.accounts import DISCLAIMER, suggest_accounts
from ..core.money import format_money


class AccountTipsDialog(QDialog):
    """Suggests how to split the monthly investment across FHSA / TFSA.

    General educational guidance based on current account rules — not tax advice.
    """

    def __init__(self, monthly_invest_cents: int, currency: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Account-type tips")
        self.setMinimumWidth(440)
        self._monthly = monthly_invest_cents
        self._currency = currency

        layout = QVBoxLayout(self)
        header = QLabel(
            f"You're planning to invest "
            f"<b>{format_money(monthly_invest_cents, currency)}/month</b>. Here's a way to "
            f"use tax-advantaged room first:"
        )
        header.setWordWrap(True)
        layout.addWidget(header)

        self._home = QCheckBox("I'm saving for a first home (prioritize FHSA)")
        self._home.setChecked(True)
        self._home.toggled.connect(self._render)
        layout.addWidget(self._home)

        self._body = QLabel()
        self._body.setTextFormat(Qt.TextFormat.RichText)
        self._body.setWordWrap(True)
        layout.addWidget(self._body)

        disclaimer = QLabel(DISCLAIMER)
        disclaimer.setObjectName("frameworkNote")
        disclaimer.setWordWrap(True)
        layout.addWidget(disclaimer)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

        self._render()

    def _render(self) -> None:
        tfsa = repo.get_setting("tfsa_limit", "7000") or "7000"
        fhsa = repo.get_setting("fhsa_annual_limit", "8000") or "8000"
        suggestions = suggest_accounts(
            self._monthly, tfsa, fhsa, saving_for_home=self._home.isChecked()
        )
        if not suggestions:
            self._body.setText(
                "Set a monthly investment amount on the Invest page to see suggestions."
            )
            return
        rows = [
            f"• <b>{format_money(s.monthly_cents, self._currency)}/month → {s.account}</b>"
            f" — {s.note}"
            for s in suggestions
        ]
        self._body.setText("<br>".join(rows))
