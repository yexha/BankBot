"""Column-aware parsing: deposits become credits, withdrawals become debits.

Word coordinates below mirror the RBC 'High Interest eSavings' layout:
    DATE   DESCRIPTION            WITHDRAWALS   DEPOSITS   BALANCE
"""
from __future__ import annotations

from bankbot.core.parsing.column_parser import parse_pages

# Approximate column x-centers.
COL = {"date": 70, "desc": 200, "withdrawal": 480, "deposit": 600, "balance": 710}


def word(text, center, top, width=40):
    return {"text": text, "x0": center - width / 2, "x1": center + width / 2, "top": top}


def header_row(top=100):
    return [
        word("DATE", COL["date"], top),
        word("DESCRIPTION", COL["desc"], top, 90),
        word("WITHDRAWALS", COL["withdrawal"], top, 90),
        word("DEPOSITS", COL["deposit"], top, 70),
        word("BALANCE", COL["balance"], top, 70),
    ]


def date_words(text, top):
    # "Jun 22, 2026" split like pdfplumber would.
    parts = text.split()
    words = []
    x = 45
    for p in parts:
        words.append(word(p, x, top, 22))
        x += 26
    return words


def test_deposit_is_credit_withdrawal_is_debit():
    page = [
        *header_row(),
        *date_words("Jun 22, 2026", 140),
        word("e-Transfer", 150, 140, 60), word("Autodeposit", 230, 140, 70),
        word("$320.00", COL["deposit"], 140), word("$688.83", COL["balance"], 140),

        *date_words("Jun 16, 2026", 180),
        word("Online", 150, 180, 40), word("Transfer", 200, 180, 50),
        word("$70.00", COL["withdrawal"], 180), word("$228.83", COL["balance"], 180),
    ]
    txns = parse_pages([page], 2026)
    assert len(txns) == 2

    deposit = txns[0]
    assert deposit.direction == "credit"
    assert deposit.amount_cents == 32000
    assert deposit.txn_date.isoformat() == "2026-06-22"
    assert "AUTODEPOSIT" in deposit.normalized_desc
    assert "688" not in deposit.normalized_desc  # balance not swallowed into desc/amount

    withdrawal = txns[1]
    assert withdrawal.direction == "debit"
    assert withdrawal.amount_cents == 7000


def test_single_deposit_amount_no_balance():
    page = [
        *header_row(),
        *date_words("Jun 1, 2026", 140),
        word("Deposit", 150, 140, 50), word("interest", 205, 140, 50),
        word("$0.22", COL["deposit"], 140),
    ]
    txns = parse_pages([page], 2026)
    assert len(txns) == 1
    assert txns[0].direction == "credit"
    assert txns[0].amount_cents == 22


def test_wrapped_description_continuation():
    page = [
        *header_row(),
        *date_words("Jun 5, 2026", 140),
        word("e-Transfer", 150, 140, 60), word("Autodeposit", 230, 140, 70),
        word("$1,391.61", COL["deposit"], 140), word("$1,398.83", COL["balance"], 140),
        # Wrapped continuation line: no date, no money.
        word("K.C", 150, 158, 30), word("Landscaping", 190, 158, 70),
        word("Ltd", 270, 158, 25),
    ]
    txns = parse_pages([page], 2026)
    assert len(txns) == 1
    assert txns[0].amount_cents == 139161
    assert "LANDSCAPING" in txns[0].normalized_desc


def test_no_headers_returns_empty():
    page = [
        *date_words("Jun 5, 2026", 140),
        word("Some purchase", 200, 140, 90), word("$50.00", 600, 140),
    ]
    assert parse_pages([page], 2026) == []


def test_opening_balance_row_skipped():
    # A dated row with only a balance figure must not become a transaction.
    page = [
        *header_row(),
        *date_words("May 22, 2026", 140),
        word("Opening", 150, 140, 50), word("Balance", 205, 140, 50),
        word("$1,511.18", COL["balance"], 140),
    ]
    assert parse_pages([page], 2026) == []
