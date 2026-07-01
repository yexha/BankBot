"""Three linked risk sliders (High / Medium / Low) that always sum to 100%.

All balancing math lives in :mod:`bankbot.core.allocation` (unit-tested). This
widget is a thin, reentrancy-safe view over it: a ``_updating`` guard prevents the
programmatic slider updates from re-triggering the change handler.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QGridLayout, QLabel, QSlider, QWidget

from ...core.allocation import monthly_investment_cents  # noqa: F401 (kept for callers)
from ...core.allocation import normalize_split, rebalance, split_amount
from ...core.money import format_money

_TIERS = [("high", "High risk"), ("med", "Medium risk"), ("low", "Low risk")]


class LinkedRiskSliders(QWidget):
    changed = Signal(dict)  # {'high': int, 'med': int, 'low': int}

    def __init__(self, initial: dict[str, int] | None = None, parent=None):
        super().__init__(parent)
        self._values = normalize_split(initial or {"high": 20, "med": 40, "low": 40})
        self._amount_cents = 0
        self._currency = "CAD"
        self._updating = False
        self._sliders: dict[str, QSlider] = {}
        self._pct_labels: dict[str, QLabel] = {}
        self._amt_labels: dict[str, QLabel] = {}
        self._build()
        self._refresh_labels()

    def _build(self) -> None:
        grid = QGridLayout(self)
        grid.setColumnStretch(1, 1)
        for row, (key, label) in enumerate(_TIERS):
            name = QLabel(label)
            name.setMinimumWidth(110)
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(0, 100)
            slider.setValue(self._values[key])
            slider.valueChanged.connect(lambda v, k=key: self._on_change(k, v))
            pct = QLabel()
            pct.setMinimumWidth(44)
            pct.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            amt = QLabel()
            amt.setMinimumWidth(120)
            amt.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            grid.addWidget(name, row, 0)
            grid.addWidget(slider, row, 1)
            grid.addWidget(pct, row, 2)
            grid.addWidget(amt, row, 3)
            self._sliders[key] = slider
            self._pct_labels[key] = pct
            self._amt_labels[key] = amt
        self._total = QLabel()
        self._total.setObjectName("sliderTotal")
        grid.addWidget(self._total, len(_TIERS), 0, 1, 4)

    def _on_change(self, key: str, value: int) -> None:
        if self._updating:
            return
        self._values = rebalance(self._values, key, value)
        self._apply_to_sliders()
        self._refresh_labels()
        self.changed.emit(dict(self._values))

    def _apply_to_sliders(self) -> None:
        self._updating = True
        try:
            for key, slider in self._sliders.items():
                if slider.value() != self._values[key]:
                    slider.setValue(self._values[key])
        finally:
            self._updating = False

    def _refresh_labels(self) -> None:
        amounts = split_amount(self._amount_cents, self._values)
        for key, _ in _TIERS:
            self._pct_labels[key].setText(f"{self._values[key]}%")
            self._amt_labels[key].setText(format_money(amounts[key], self._currency))
        total = sum(self._values.values())
        self._total.setText(f"Total: {total}%  (always balanced to 100%)")

    # --- public API -----------------------------------------------------------
    def set_amount(self, cents: int, currency: str) -> None:
        self._amount_cents = max(0, int(cents))
        self._currency = currency
        self._refresh_labels()

    def values(self) -> dict[str, int]:
        return dict(self._values)

    def set_values(self, values: dict[str, int]) -> None:
        self._values = normalize_split(values)
        self._apply_to_sliders()
        self._refresh_labels()
