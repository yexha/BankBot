"""Leftover-money math for a period.

Leftover = Income − Essential − Want. Transactions still in the review queue
(``essential_want is None``) and those marked ``ignore`` are excluded until the
user confirms them, so leftover never silently includes unconfirmed money.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Protocol


class _TxnLike(Protocol):
    amount_cents: int
    direction: str
    essential_want: str | None
    is_income: bool
    review_status: str
    category: str | None


@dataclass
class BudgetSummary:
    income_cents: int = 0
    essential_cents: int = 0
    want_cents: int = 0
    needs_review_count: int = 0
    by_category: dict[str, int] = field(default_factory=dict)

    @property
    def leftover_cents(self) -> int:
        return self.income_cents - self.essential_cents - self.want_cents


def summarize(txns: Sequence[_TxnLike]) -> BudgetSummary:
    s = BudgetSummary()
    for t in txns:
        label = t.essential_want
        if t.review_status == "needs_review" and label is None:
            s.needs_review_count += 1
            continue
        if label == "income" or t.is_income:
            s.income_cents += t.amount_cents
        elif label == "essential":
            s.essential_cents += t.amount_cents
            _bump(s.by_category, t.category, t.amount_cents)
        elif label == "want":
            s.want_cents += t.amount_cents
            _bump(s.by_category, t.category, t.amount_cents)
        # 'ignore' / None -> excluded
    return s


def _bump(d: dict[str, int], key: str | None, amount: int) -> None:
    name = key or "Uncategorized"
    d[name] = d.get(name, 0) + amount
