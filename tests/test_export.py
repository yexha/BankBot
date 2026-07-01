"""Report building and CSV/PDF export."""
from __future__ import annotations

from datetime import date

import pytest

from bankbot.core import export as export_mod
from bankbot.core import repository as repo
from bankbot.core.db import session_scope
from bankbot.core.import_service import recategorize_all
from bankbot.core.models import Transaction
from bankbot.core.parsing.base import ParsedTxn


def _add(desc, cents, direction, d=date(2026, 6, 10)):
    p = ParsedTxn(d, desc, cents, direction).finalize()
    with session_scope() as s:
        t = Transaction(txn_date=p.txn_date, description=p.description,
                        normalized_desc=p.normalized_desc, amount_cents=p.amount_cents,
                        direction=p.direction, dedupe_hash=p.dedupe_hash)
        s.add(t)


def _seed(database):
    _add("ACME PAYROLL DEP", 500000, "credit")
    _add("LOBLAWS GROCERY", 42000, "debit")
    _add("NETFLIX.COM", 1699, "debit")
    recategorize_all()


def test_build_report_totals(database):
    _seed(database)
    report = export_mod.build_report(2026, 6)
    assert report.income_cents == 500000
    assert report.essential_cents == 42000
    assert report.want_cents == 1699
    assert report.leftover_cents == 500000 - 42000 - 1699
    assert report.period_label == "June 2026"
    # Risk split always sums to 100.
    assert sum(report.risk_split.values()) == 100
    # Risk amounts sum to the monthly invest amount.
    assert sum(report.risk_amounts.values()) == report.monthly_invest_cents


def test_export_csv_writes_file(database, tmp_path):
    _seed(database)
    report = export_mod.build_report(2026, 6)
    out = tmp_path / "summary.csv"
    export_mod.export_csv(out, report)
    content = out.read_text(encoding="utf-8")
    assert "BankBot budget summary" in content
    assert "Income" in content
    assert "Groceries" in content
    assert "Leftover" in content


def test_export_pdf_writes_file(database, tmp_path):
    pytest.importorskip("reportlab")
    _seed(database)
    report = export_mod.build_report(2026, 6)
    out = tmp_path / "summary.pdf"
    export_mod.export_pdf(out, report)
    assert out.exists() and out.stat().st_size > 0
    assert out.read_bytes().startswith(b"%PDF")
