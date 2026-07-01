"""Leftover math: income − essential − want, excluding review/ignore."""
from __future__ import annotations

from bankbot.core.budget import summarize
from tests.conftest import make_txn


def test_summarize_basic():
    txns = [
        make_txn(direction="credit", amount_cents=500000, essential_want="income",
                 is_income=True),
        make_txn(direction="debit", amount_cents=150000, essential_want="essential",
                 category="Rent/Mortgage"),
        make_txn(direction="debit", amount_cents=40000, essential_want="essential",
                 category="Groceries"),
        make_txn(direction="debit", amount_cents=20000, essential_want="want",
                 category="Dining"),
    ]
    s = summarize(txns)
    assert s.income_cents == 500000
    assert s.essential_cents == 190000
    assert s.want_cents == 20000
    assert s.leftover_cents == 290000
    assert s.by_category["Rent/Mortgage"] == 150000


def test_review_and_ignore_excluded():
    txns = [
        make_txn(direction="credit", amount_cents=300000, essential_want="income",
                 is_income=True),
        make_txn(direction="debit", amount_cents=150000, essential_want=None,
                 review_status="needs_review"),
        make_txn(direction="debit", amount_cents=5000, essential_want="ignore"),
    ]
    s = summarize(txns)
    assert s.income_cents == 300000
    assert s.essential_cents == 0
    assert s.want_cents == 0
    assert s.needs_review_count == 1
    assert s.leftover_cents == 300000


def test_leftover_can_be_negative():
    txns = [
        make_txn(direction="credit", amount_cents=100000, essential_want="income",
                 is_income=True),
        make_txn(direction="debit", amount_cents=150000, essential_want="essential"),
    ]
    assert summarize(txns).leftover_cents == -50000
