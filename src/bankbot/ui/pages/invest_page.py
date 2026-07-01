"""Investment allocation: how much of leftover-after-goals to invest, and the
risk split across broad, transparent allocation models.

This is a planning tool. It maps risk tiers to well-known diversification
categories — it does not pick stocks or predict returns.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from ...core import repository as repo
from ...core.allocation import monthly_investment_cents
from ...core.budget import summarize
from ...core.content import FRAMEWORK_NOTE, RISK_TIERS
from ...core.goals import plan_goals
from ...core.money import format_money
from ..widgets.linked_risk_sliders import LinkedRiskSliders


class InvestPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._leftover_after_goals = 0
        self._currency = "CAD"

        outer = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        self._v = QVBoxLayout(body)
        scroll.setWidget(body)
        outer.addWidget(scroll)

        self._v.addWidget(QLabel("<h2>Invest your leftover</h2>"))

        # Currency selector.
        cur_row = QHBoxLayout()
        cur_row.addWidget(QLabel("Currency:"))
        self._currency_box = QComboBox()
        self._currency_box.addItems(["CAD", "USD"])
        self._currency_box.currentTextChanged.connect(self._on_currency)
        cur_row.addWidget(self._currency_box)
        cur_row.addStretch(1)
        self._v.addLayout(cur_row)

        self._available = QLabel()
        self._available.setObjectName("investAvailable")
        self._available.setWordWrap(True)
        self._v.addWidget(self._available)

        # Monthly invest slider.
        self._v.addWidget(QLabel("<b>How much of that to invest per month</b>"))
        inv_row = QHBoxLayout()
        self._invest_slider = QSlider(Qt.Orientation.Horizontal)
        self._invest_slider.setRange(0, 100)
        self._invest_slider.valueChanged.connect(self._on_invest_pct)
        self._invest_label = QLabel()
        self._invest_label.setMinimumWidth(200)
        self._invest_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        inv_row.addWidget(self._invest_slider, 1)
        inv_row.addWidget(self._invest_label)
        self._v.addLayout(inv_row)

        # Risk split.
        self._v.addWidget(QLabel("<b>Risk split</b> (always balanced to 100%)"))
        self._risk = LinkedRiskSliders()
        self._risk.changed.connect(self._on_risk_changed)
        self._v.addWidget(self._risk)

        # Allocation models + why-invest panel.
        self._tier_example_labels: dict[str, QLabel] = {}
        self._v.addWidget(QLabel("<b>Why these categories</b>"))
        for tier in ("high", "med", "low"):
            self._v.addWidget(self._tier_card(tier))

        note = QLabel(FRAMEWORK_NOTE)
        note.setObjectName("frameworkNote")
        note.setWordWrap(True)
        self._v.addWidget(note)

        disclaimer = QLabel(
            "This is general educational guidance based on your own data and general "
            "financial principles — not personalized financial, investment, or tax "
            "advice, and not a prediction of returns. Consult a licensed advisor."
        )
        disclaimer.setObjectName("investDisclaimer")
        disclaimer.setWordWrap(True)
        self._v.addWidget(disclaimer)
        self._v.addStretch(1)

    def _tier_card(self, key: str) -> QFrame:
        tier = RISK_TIERS[key]
        card = QFrame()
        card.setObjectName("tierCard")
        v = QVBoxLayout(card)
        v.addWidget(QLabel(f"<b>{tier.label}</b>"))
        examples = QLabel()
        examples.setObjectName("tierExamples")
        examples.setWordWrap(True)
        v.addWidget(examples)
        why = QLabel(tier.why)
        why.setWordWrap(True)
        v.addWidget(why)
        self._tier_example_labels[key] = examples
        return card

    # --- data -----------------------------------------------------------------
    def refresh(self) -> None:
        self._currency = repo.get_setting("currency", "CAD") or "CAD"
        self._currency_box.blockSignals(True)
        self._currency_box.setCurrentText(self._currency)
        self._currency_box.blockSignals(False)

        # Recompute leftover-after-goals independently.
        year, month = repo.latest_month()
        leftover = summarize(repo.transactions_for_month(year, month)).leftover_cents
        plan = plan_goals(repo.list_goals(), leftover)
        self._leftover_after_goals = plan.leftover_after_goals_cents

        self._available.setText(
            f"Leftover after goals available to invest: "
            f"<b>{format_money(self._leftover_after_goals, self._currency)}</b>"
        )

        # Restore saved slider positions.
        pct = int(repo.get_setting("monthly_invest_pct", "50") or "50")
        self._invest_slider.blockSignals(True)
        self._invest_slider.setValue(max(0, min(100, pct)))
        self._invest_slider.blockSignals(False)

        self._risk.set_values({
            "high": int(repo.get_setting("risk_high_pct", "20") or "20"),
            "med": int(repo.get_setting("risk_med_pct", "40") or "40"),
            "low": int(repo.get_setting("risk_low_pct", "40") or "40"),
        })

        self._update_examples()
        self._update_amounts()

    def _update_examples(self) -> None:
        for key, label in self._tier_example_labels.items():
            tier = RISK_TIERS[key]
            examples = tier.examples_cad if self._currency == "CAD" else tier.examples_usd
            label.setText(f"Examples: {examples}")

    def _monthly_cents(self) -> int:
        return monthly_investment_cents(self._leftover_after_goals, self._invest_slider.value())

    def _update_amounts(self) -> None:
        monthly = self._monthly_cents()
        self._invest_label.setText(
            f"{self._invest_slider.value()}% = {format_money(monthly, self._currency)}/mo"
        )
        self._risk.set_amount(monthly, self._currency)

    # --- handlers -------------------------------------------------------------
    def _on_invest_pct(self, value: int) -> None:
        repo.set_setting("monthly_invest_pct", str(value))
        self._update_amounts()

    def _on_risk_changed(self, values: dict) -> None:
        repo.set_setting("risk_high_pct", str(values["high"]))
        repo.set_setting("risk_med_pct", str(values["med"]))
        repo.set_setting("risk_low_pct", str(values["low"]))

    def _on_currency(self, currency: str) -> None:
        repo.set_setting("currency", currency)
        self._currency = currency
        self._update_examples()
        self._update_amounts()
        self._available.setText(
            f"Leftover after goals available to invest: "
            f"<b>{format_money(self._leftover_after_goals, self._currency)}</b>"
        )
