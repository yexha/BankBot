"""DB-backed services: seeding, recategorization, review decisions, settings."""
from __future__ import annotations

from datetime import date

from sqlalchemy import select

from bankbot.core import repository as repo
from bankbot.core.db import session_scope
from bankbot.core.import_service import recategorize_all
from bankbot.core.models import Category, Rule, Transaction
from bankbot.core.parsing.base import ParsedTxn
from bankbot.core.review_service import apply_review_decision


def _add_txn(desc, amount_cents, direction, txn_date=date(2026, 1, 10)):
    p = ParsedTxn(txn_date, desc, amount_cents, direction).finalize()
    with session_scope() as s:
        t = Transaction(
            txn_date=p.txn_date, description=p.description,
            normalized_desc=p.normalized_desc, amount_cents=p.amount_cents,
            direction=p.direction, dedupe_hash=p.dedupe_hash,
        )
        s.add(t)
        s.flush()
        return t.id


def test_seed_creates_categories_and_rules(database):
    with session_scope() as s:
        assert s.scalar(select(Category).limit(1)) is not None
        assert s.scalar(select(Rule).limit(1)) is not None
    assert repo.get_setting("currency") == "CAD"
    assert repo.get_setting("tfsa_limit") == "7000"


def test_recategorize_classifies(database):
    _add_txn("LOBLAWS #55 GROCERY", 8000, "debit")
    _add_txn("ACME CORP PAYROLL DEP", 250000, "credit")
    _add_txn("ATM WITHDRAWAL", 10000, "debit")
    recategorize_all()

    with session_scope() as s:
        rows = {t.normalized_desc: t for t in s.scalars(select(Transaction)).all()}
    grocery = next(t for d, t in rows.items() if "LOBLAWS" in d)
    payroll = next(t for d, t in rows.items() if "PAYROLL" in d)
    atm = next(t for d, t in rows.items() if "ATM" in d)
    assert grocery.essential_want == "essential"
    assert payroll.is_income
    assert atm.review_status == "needs_review"


def test_review_decision_confirms_and_learns(database):
    tid = _add_txn("INTERAC E-TRANSFER TO LANDLORD", 150000, "debit")
    recategorize_all()
    assert repo.review_queue()  # it's queued

    apply_review_decision(tid, "recurring_bill", remember=True)

    with session_scope() as s:
        t = s.get(Transaction, tid)
        assert t.review_status == "confirmed"
        assert t.essential_want == "essential"
        learned = s.scalars(
            select(Rule).where(Rule.source == "user_confirmed")
        ).all()
        assert len(learned) == 1
        assert learned[0].match_type == "exact_payee"


def test_confirmed_survives_recategorize(database):
    tid = _add_txn("INTERAC E-TRANSFER TO LANDLORD", 150000, "debit")
    recategorize_all()
    apply_review_decision(tid, "essential", remember=False)
    recategorize_all()  # should NOT revert the user's decision
    with session_scope() as s:
        t = s.get(Transaction, tid)
        assert t.review_status == "confirmed"
        assert t.essential_want == "essential"


def test_learned_rule_applies_to_future_txns(database):
    tid = _add_txn("INTERAC E-TRANSFER TO LANDLORD", 150000, "debit",
                   txn_date=date(2026, 1, 1))
    recategorize_all()
    apply_review_decision(tid, "recurring_bill", remember=True)
    # A new statement with the same payee next month.
    _add_txn("INTERAC E-TRANSFER TO LANDLORD", 150000, "debit",
             txn_date=date(2026, 2, 1))
    recategorize_all()
    with session_scope() as s:
        feb = s.scalar(
            select(Transaction).where(Transaction.txn_date == date(2026, 2, 1))
        )
    assert feb.essential_want == "essential"
    assert feb.review_status == "auto"  # auto-classified, not re-queued


def test_confirm_credit_as_income(database):
    tid = _add_txn("INTERAC E-TRANSFER AUTODEPOSIT ACME", 250000, "credit")
    recategorize_all()
    # A credit we couldn't confirm as income is queued, not counted as cost.
    with session_scope() as s:
        t = s.get(Transaction, tid)
        assert t.review_status == "needs_review"
        assert t.essential_want != "want"

    apply_review_decision(tid, "income", remember=True)
    with session_scope() as s:
        t = s.get(Transaction, tid)
        assert t.is_income
        assert t.essential_want == "income"
        assert t.review_status == "confirmed"


def test_learned_income_applies_to_future_credit(database):
    tid = _add_txn("INTERAC E-TRANSFER AUTODEPOSIT ACME", 250000, "credit",
                   txn_date=date(2026, 1, 1))
    recategorize_all()
    apply_review_decision(tid, "income", remember=True)
    _add_txn("INTERAC E-TRANSFER AUTODEPOSIT ACME", 250000, "credit",
             txn_date=date(2026, 2, 1))
    recategorize_all()
    with session_scope() as s:
        feb = s.scalar(
            select(Transaction).where(Transaction.txn_date == date(2026, 2, 1))
        )
    assert feb.is_income
    assert feb.review_status == "auto"


def test_settings_roundtrip(database):
    repo.set_setting("currency", "USD")
    assert repo.get_setting("currency") == "USD"
    database.reset_data()
    assert repo.get_setting("currency") == "CAD"  # reset restores defaults
