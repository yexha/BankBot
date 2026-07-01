"""Settings: currency, manual FX rate, theme, re-categorize, reset data."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...core import repository as repo
from ...core.db import reset_data
from ...core.import_service import recategorize_all
from ..theme import toggle_theme


class SettingsPage(QWidget):
    dataChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<h2>Settings</h2>"))

        form = QFormLayout()
        self._currency = QComboBox()
        self._currency.addItems(["CAD", "USD"])
        self._currency.currentTextChanged.connect(
            lambda c: (repo.set_setting("currency", c), self.dataChanged.emit())
        )
        form.addRow("Currency", self._currency)

        self._fx = QDoubleSpinBox()
        self._fx.setRange(0.01, 100.0)
        self._fx.setDecimals(4)
        self._fx.setSingleStep(0.01)
        self._fx.editingFinished.connect(
            lambda: repo.set_setting("manual_fx_rate", str(self._fx.value()))
        )
        form.addRow("Exchange rate (CAD per 1 USD)", self._fx)
        layout.addLayout(form)

        # Theme toggle.
        theme_row = QHBoxLayout()
        theme_row.addWidget(QLabel("Appearance"))
        self._theme_btn = QPushButton("Toggle dark / light")
        self._theme_btn.clicked.connect(self._toggle_theme)
        theme_row.addWidget(self._theme_btn)
        theme_row.addStretch(1)
        layout.addLayout(theme_row)

        # Actions.
        recat = QPushButton("Re-run categorization rules")
        recat.clicked.connect(self._recategorize)
        layout.addWidget(recat)

        reset = QPushButton("Clear / reset all stored data")
        reset.setObjectName("dangerButton")
        reset.clicked.connect(self._reset)
        layout.addWidget(reset)

        self._status = QLabel("")
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        note = QLabel(
            "Contribution limits (TFSA/FHSA) used elsewhere are editable and were verified "
            "for 2026 — update them here if the CRA figures change. Export to CSV/PDF is "
            "planned for the next build."
        )
        note.setWordWrap(True)
        note.setObjectName("frameworkNote")
        layout.addWidget(note)
        layout.addStretch(1)

    def refresh(self) -> None:
        self._currency.blockSignals(True)
        self._currency.setCurrentText(repo.get_setting("currency", "CAD") or "CAD")
        self._currency.blockSignals(False)
        try:
            self._fx.setValue(float(repo.get_setting("manual_fx_rate", "1.35") or "1.35"))
        except ValueError:
            self._fx.setValue(1.35)

    def _toggle_theme(self) -> None:
        app = QApplication.instance()
        if app:
            new = toggle_theme(app)
            self._status.setText(f"Theme set to {new}.")

    def _recategorize(self) -> None:
        try:
            recategorize_all()
            self._status.setText("Re-ran categorization on all transactions.")
            self.dataChanged.emit()
        except Exception as exc:  # noqa: BLE001
            self._status.setText(f"Could not re-run categorization: {exc}")

    def _reset(self) -> None:
        confirm = QMessageBox.question(
            self, "Reset all data?",
            "This permanently deletes all imported statements, transactions, goals and "
            "learned rules on this computer. This cannot be undone. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            reset_data()
            self._status.setText("All stored data has been cleared.")
            self.refresh()
            self.dataChanged.emit()
        except Exception as exc:  # noqa: BLE001
            self._status.setText(f"Could not reset data: {exc}")
