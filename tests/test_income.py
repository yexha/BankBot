"""Recurring-credit / paycheck detection."""
from __future__ import annotations

from bankbot.core.categorize.income import detect_income
from tests.conftest import make_txn


def test_keyword_income():
    txns = [make_txn(direction="credit", description="ACME CORP PAYROLL",
                     amount_cents=250000)]
    assert detect_income(txns) == [True]


def test_recurring_similar_amount_income():
    txns = [
        make_txn(direction="credit", description="EMPLOYER XYZ", amount_cents=200000),
        make_txn(direction="credit", description="EMPLOYER XYZ", amount_cents=201000),
    ]
    assert detect_income(txns) == [True, True]


def test_single_unknown_credit_not_income():
    txns = [make_txn(direction="credit", description="RANDOM CO", amount_cents=5000)]
    assert detect_income(txns) == [False]


def test_etransfer_credit_not_income():
    txns = [
        make_txn(direction="credit", description="INTERAC E-TRANSFER FROM JOHN",
                 amount_cents=200000),
        make_txn(direction="credit", description="INTERAC E-TRANSFER FROM JOHN",
                 amount_cents=200000),
    ]
    # Even though it recurs, e-transfers are never auto-classified as income.
    assert detect_income(txns) == [False, False]


def test_debit_never_income():
    txns = [make_txn(direction="debit", description="PAYROLL SERVICES INC",
                     amount_cents=9000)]
    assert detect_income(txns) == [False]
