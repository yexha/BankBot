"""Apply user decisions from the review queue and remember the pattern."""
from __future__ import annotations

from sqlalchemy import select

from .db import session_scope
from .models import Rule, Transaction

# review action -> (essential_want, is_recurring_bill)
_DECISIONS = {
    "income": ("income", False),
    "essential": ("essential", False),
    "want": ("want", False),
    "ignore": ("ignore", False),
    "recurring_bill": ("essential", True),
}

_LEARNED_PRIORITY = 500  # above every builtin rule


def apply_review_decision(txn_id: int, decision: str, remember: bool = True) -> None:
    """Confirm a queued transaction. When ``remember`` is set, create/update a
    user rule so the same payee auto-classifies next time."""
    if decision not in _DECISIONS:
        raise ValueError(f"Unknown review decision: {decision!r}")
    label, recurring = _DECISIONS[decision]
    is_income = decision == "income"

    with session_scope() as s:
        txn = s.get(Transaction, txn_id)
        if txn is None:
            return
        txn.essential_want = label
        txn.is_income = is_income
        txn.review_status = "confirmed"
        txn.confidence = 1.0
        if is_income:
            # Overriding to income also corrects the direction (e.g. a deposit that
            # was parsed as a withdrawal), so summaries treat it as money in.
            txn.category = "Income"
            txn.direction = "credit"
        else:
            # Any expense label means money out; correct a mis-parsed direction too.
            if decision in ("essential", "want", "recurring_bill"):
                txn.direction = "debit"
            if txn.category in (None, "Uncategorized", "Transfer", "Cash Withdrawal", "Income"):
                txn.category = "Recurring Bill" if recurring else "Uncategorized"
        category = txn.category or "Uncategorized"

        if remember and txn.normalized_desc:
            _upsert_learned_rule(s, txn.normalized_desc, category, label, recurring)


def _upsert_learned_rule(
    session, pattern: str, category: str, label: str, recurring: bool
) -> None:
    existing = session.scalar(
        select(Rule).where(
            Rule.match_type == "exact_payee",
            Rule.pattern == pattern,
            Rule.source == "user_confirmed",
        )
    )
    if existing:
        existing.category = category
        existing.essential_want = label
        existing.is_recurring_bill = recurring
    else:
        session.add(
            Rule(
                match_type="exact_payee",
                pattern=pattern,
                category=category,
                essential_want=label,
                is_recurring_bill=recurring,
                priority=_LEARNED_PRIORITY,
                source="user_confirmed",
            )
        )
