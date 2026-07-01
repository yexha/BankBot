"""Recurring-credit / paycheck detection.

A credit is treated as income if it matches a payroll keyword OR recurs with a
similar amount under the same payee. e-Transfer credits are deliberately excluded
(they could be reimbursements) and are routed to review instead.
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from typing import Protocol

from .review import is_etransfer

INCOME_KEYWORDS = (
    "PAYROLL", "PAY ", "DIR DEP", "DIRECT DEP", "DEP PAY", "SALARY", "WAGES",
    "EMPLOYER", "GOV CANADA", "CANADA FED", "CRA ", "PENSION", "BENEFIT",
    "PAYDED", "EI ", "CPP", "OAS",
)
_AMOUNT_TOLERANCE = 0.10  # 10% amount variation still counts as the same recurring credit


class _TxnLike(Protocol):
    normalized_desc: str
    direction: str
    amount_cents: int


def detect_income(txns: Sequence[_TxnLike]) -> list[bool]:
    """Return a list of booleans aligned with ``txns`` marking income credits."""
    result = [False] * len(txns)
    credits = [
        (i, t)
        for i, t in enumerate(txns)
        if t.direction == "credit" and not is_etransfer(t.normalized_desc)
    ]

    # 1. Keyword-based payroll/benefit detection.
    for i, t in credits:
        if any(k in t.normalized_desc for k in INCOME_KEYWORDS):
            result[i] = True

    # 2. Recurrence: same payee, >=2 occurrences, similar amount.
    groups: dict[str, list[tuple[int, _TxnLike]]] = defaultdict(list)
    for i, t in credits:
        groups[t.normalized_desc].append((i, t))
    for items in groups.values():
        if len(items) < 2:
            continue
        amounts = [t.amount_cents for _, t in items]
        avg = sum(amounts) / len(amounts)
        if avg > 0 and all(abs(a - avg) <= _AMOUNT_TOLERANCE * avg for a in amounts):
            for i, _ in items:
                result[i] = True

    return result
