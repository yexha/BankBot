"""Transparent, rule-of-thumb guidance for how much of leftover to invest.

This is deliberately NOT a market predictor or stock picker. It is a simple,
explainable heuristic based on personal-finance common sense: keep an emergency
buffer, and the larger your monthly surplus is relative to your essential costs,
the larger the share you can reasonably direct to long-term investing. The user
always sets the final number; this only proposes a starting point and shows its
reasoning.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .money import format_money

_MIN_PCT = 50
_MAX_PCT = 85
_EMERGENCY_MONTHS_LOW = 3
_EMERGENCY_MONTHS_HIGH = 6


@dataclass
class InvestSuggestion:
    pct: int
    monthly_cents: int
    emergency_low_cents: int
    emergency_high_cents: int
    reasons: list[str] = field(default_factory=list)


def suggest_invest_pct(
    leftover_after_goals_cents: int, monthly_essential_cents: int, currency: str = "CAD"
) -> InvestSuggestion:
    """Propose a starting invest percentage of leftover-after-goals.

    Rules (all shown to the user):
      * Nothing left after goals -> suggest 0%.
      * Otherwise scale between 50% and 85% by how big the surplus is versus
        essential spending (a bigger cushion can support a bigger invested share).
      * Always flag the 3-6 month emergency-fund guideline as a precondition.
    """
    leftover = max(0, int(leftover_after_goals_cents))
    essentials = max(0, int(monthly_essential_cents))
    emergency_low = essentials * _EMERGENCY_MONTHS_LOW
    emergency_high = essentials * _EMERGENCY_MONTHS_HIGH

    if leftover <= 0:
        return InvestSuggestion(
            pct=0, monthly_cents=0,
            emergency_low_cents=emergency_low, emergency_high_cents=emergency_high,
            reasons=["After funding your goals there's nothing left to invest this month."],
        )

    if essentials <= 0:
        pct = 70  # no essentials on record — use a balanced default
    else:
        ratio = leftover / essentials
        pct = int(round(_MIN_PCT + 20 * min(ratio, 1.75)))
        pct = max(_MIN_PCT, min(_MAX_PCT, pct))

    monthly = leftover * pct // 100
    reasons = [
        f"Your goals already reserve money for your priorities, so most of the "
        f"remaining {format_money(leftover, currency)} can go toward long-term investing.",
        f"Suggested starting point: invest {pct}% "
        f"(= {format_money(monthly, currency)}/month), keeping the rest as an "
        f"accessible cash buffer.",
    ]
    if essentials > 0:
        reasons.append(
            f"Before investing heavily, aim to hold a 3–6 month emergency fund "
            f"(~{format_money(emergency_low, currency)}–{format_money(emergency_high, currency)}) "
            f"in cash/savings."
        )
    reasons.append(
        "This is a general rule of thumb you can adjust — it is not a market "
        "prediction or a guarantee of returns."
    )
    return InvestSuggestion(
        pct=pct, monthly_cents=monthly,
        emergency_low_cents=emergency_low, emergency_high_cents=emergency_high,
        reasons=reasons,
    )
