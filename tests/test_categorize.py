"""Rule matching and the critical review-flagging behavior."""
from __future__ import annotations

from types import SimpleNamespace

from bankbot.core.categorize.engine import classify_one, classify_transactions, match_rule
from tests.conftest import make_txn


def rule(pattern, category, ess, match_type="keyword", priority=100, rid=1):
    return SimpleNamespace(
        id=rid, match_type=match_type, pattern=pattern, category=category,
        essential_want=ess, priority=priority,
    )


def test_match_rule_keyword():
    rules = [rule("NETFLIX", "Subscriptions", "want", priority=110)]
    r, conf = match_rule("NETFLIX.COM 866", rules)
    assert r is not None and r.category == "Subscriptions"
    assert conf == 0.8


def test_match_rule_priority_order():
    rules = [
        rule("STARBUCKS", "Dining", "want", priority=110, rid=2),
        rule("STAR", "Shopping", "want", priority=100, rid=3),
    ]
    r, _ = match_rule("STARBUCKS #123", rules)
    assert r.id == 2  # highest priority first


def test_keyword_debit_auto():
    rules = [rule("LOBLAW", "Groceries", "essential", priority=110)]
    txn = make_txn(direction="debit", description="LOBLAWS #45", amount_cents=8000)
    c = classify_one(txn, rules, is_income=False)
    assert c.category == "Groceries"
    assert c.essential_want == "essential"
    assert c.review_status == "auto"


def test_cash_withdrawal_forced_to_review():
    txn = make_txn(direction="debit", description="ATM WITHDRAWAL", amount_cents=20000)
    c = classify_one(txn, [], is_income=False)
    assert c.review_status == "needs_review"
    assert c.essential_want is None       # never auto-tagged as want
    assert "cash" in c.review_reason.lower()


def test_etransfer_forced_to_review():
    txn = make_txn(direction="debit", description="INTERAC E-TRANSFER SENT",
                   amount_cents=150000)
    c = classify_one(txn, [], is_income=False)
    assert c.review_status == "needs_review"
    assert c.essential_want is None


def test_unknown_debit_goes_to_review():
    txn = make_txn(direction="debit", description="SOME RANDOM PLACE", amount_cents=3000)
    c = classify_one(txn, [], is_income=False)
    assert c.review_status == "needs_review"
    assert c.category == "Uncategorized"


def test_unconfirmed_credit_goes_to_review():
    txn = make_txn(direction="credit", description="MYSTERY DEPOSIT", amount_cents=5000)
    c = classify_one(txn, [], is_income=False)  # not flagged as income
    assert c.review_status == "needs_review"


def test_income_is_auto():
    txn = make_txn(direction="credit", description="ACME PAYROLL DEP", amount_cents=300000)
    c = classify_one(txn, [], is_income=True)
    assert c.is_income and c.essential_want == "income"
    assert c.review_status == "auto"


def test_classify_transactions_batch_detects_income():
    rules = [rule("LOBLAW", "Groceries", "essential", priority=110)]
    txns = [
        make_txn(direction="credit", description="ACME PAYROLL", amount_cents=250000),
        make_txn(direction="debit", description="LOBLAWS", amount_cents=8000),
        make_txn(direction="debit", description="ATM WITHDRAWAL", amount_cents=10000),
    ]
    results = classify_transactions(txns, rules)
    assert results[0].is_income
    assert results[1].essential_want == "essential"
    assert results[2].review_status == "needs_review"
