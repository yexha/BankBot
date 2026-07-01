"""Classification engine: maps a transaction to a category + Essential/Want label.

Per-transaction order of decisions:
  1. Income (from :func:`income.detect_income`) -> category Income, auto.
  2. Other credits -> review (could be a refund/reimbursement, never auto-want).
  3. Forced-review debits (cash withdrawal, e-transfer) -> review.
  4. Rule match with confidence >= 0.5 -> auto.
  5. Anything else -> review (unrecognized).
"""
from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from .income import detect_income
from .review import forced_review_reason, is_cash_withdrawal

REVIEW_CONFIDENCE_FLOOR = 0.5


@dataclass
class Classification:
    category: str | None
    essential_want: str | None
    confidence: float
    is_income: bool
    review_status: str          # 'auto' | 'needs_review'
    source_rule_id: int | None = None
    review_reason: str | None = None


class _RuleLike(Protocol):
    id: int | None
    match_type: str
    pattern: str
    category: str
    essential_want: str
    priority: int


class _TxnLike(Protocol):
    normalized_desc: str
    direction: str
    amount_cents: int


def _confidence_for(rule: _RuleLike) -> float:
    if rule.match_type == "exact_payee":
        return 0.95
    if rule.priority >= 110:      # strong/specific keyword
        return 0.8
    return 0.65


def match_rule(normalized_desc: str, rules: Sequence[_RuleLike]) -> tuple[_RuleLike | None, float]:
    """First matching rule (rules must be passed highest-priority-first)."""
    for rule in rules:
        pat = rule.pattern.upper()
        if rule.match_type == "exact_payee":
            if normalized_desc == pat or normalized_desc.startswith(pat):
                return rule, _confidence_for(rule)
        elif rule.match_type == "regex":
            try:
                if re.search(rule.pattern, normalized_desc, re.IGNORECASE):
                    return rule, _confidence_for(rule)
            except re.error:
                continue
        else:  # keyword
            if pat in normalized_desc:
                return rule, _confidence_for(rule)
    return None, 0.0


def classify_one(
    txn: _TxnLike, rules: Sequence[_RuleLike], is_income: bool
) -> Classification:
    desc = txn.normalized_desc or ""

    if is_income:
        return Classification("Income", "income", 0.9, True, "auto")

    rule, conf = match_rule(desc, rules)

    # A learned exact-payee rule is authoritative: once the user has confirmed what
    # a payee is, future identical payees must NOT be re-queued (even e-transfers).
    if rule is not None and rule.match_type == "exact_payee":
        learned_income = rule.essential_want == "income"
        return Classification(rule.category, rule.essential_want, conf, learned_income,
                              "auto", source_rule_id=rule.id)

    if txn.direction == "credit":
        return Classification(
            "Transfer", None, 0.0, False, "needs_review",
            review_reason="incoming money we couldn't confirm as income",
        )

    # Unconfirmed cash withdrawals / e-transfers always go to review.
    reason = forced_review_reason(desc)
    if reason:
        category = "Cash Withdrawal" if is_cash_withdrawal(desc) else "Transfer"
        return Classification(category, None, 0.0, False, "needs_review",
                              review_reason=reason)

    if rule is not None and conf >= REVIEW_CONFIDENCE_FLOOR:
        return Classification(rule.category, rule.essential_want, conf, False,
                              "auto", source_rule_id=rule.id)

    return Classification("Uncategorized", None, 0.0, False, "needs_review",
                          review_reason="we don't recognize this description")


def classify_transactions(
    txns: Sequence[_TxnLike], rules: Sequence[_RuleLike]
) -> list[Classification]:
    """Classify a batch, running income detection across the whole batch first."""
    income_flags = detect_income(txns)
    return [classify_one(t, rules, income_flags[i]) for i, t in enumerate(txns)]
