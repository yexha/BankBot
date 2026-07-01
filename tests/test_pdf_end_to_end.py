"""Real end-to-end: generate a column-layout PDF and parse it through the whole
pipeline (pdfplumber word extraction -> column parser). Skipped if reportlab or
pdfplumber aren't installed."""
from __future__ import annotations

import pytest

pytest.importorskip("reportlab")
pytest.importorskip("pdfplumber")

from reportlab.pdfgen import canvas  # noqa: E402

from bankbot.core.parsing.extractor import extract_file  # noqa: E402

# (description, withdrawal, deposit)  — mirrors an RBC eSavings statement
ROWS = [
    ("Jun 22, 2026", "e-Transfer - Autodeposit layne", None, "320.00", "688.83"),
    ("Jun 16, 2026", "Online Transfer to Deposit Account-9856", "70.00", None, "228.83"),
    ("Jun 8, 2026", "Online Transfer to Deposit Account-6496", "1,100.00", None, "298.83"),
    ("Jun 5, 2026", "e-Transfer - Autodeposit K.C Landscaping Ltd", None, "1,391.61", "1,398.83"),
    ("Jun 1, 2026", "Deposit interest", None, "0.22", None),
    ("May 25, 2026", "Online Transfer to Deposit Account-6610", "905.00", None, "6.18"),
]
# Column x positions (points from left).
X_DATE, X_DESC, X_WD, X_DEP, X_BAL = 40, 120, 330, 420, 510


def _make_pdf(path):
    c = canvas.Canvas(str(path), pagesize=(612, 792))
    c.setFont("Helvetica-Bold", 9)
    c.drawString(X_DATE, 700, "RBC Royal Bank — High Interest eSavings")
    y = 660
    c.drawString(X_DATE, y, "DATE")
    c.drawString(X_DESC, y, "DESCRIPTION")
    c.drawRightString(X_WD + 40, y, "WITHDRAWALS")
    c.drawRightString(X_DEP + 40, y, "DEPOSITS")
    c.drawRightString(X_BAL + 40, y, "BALANCE")
    c.setFont("Helvetica", 9)
    y -= 20
    for date_s, desc, wd, dep, bal in ROWS:
        c.drawString(X_DATE, y, date_s)
        c.drawString(X_DESC, y, desc)
        if wd:
            c.drawRightString(X_WD + 40, y, f"${wd}")
        if dep:
            c.drawRightString(X_DEP + 40, y, f"${dep}")
        if bal:
            c.drawRightString(X_BAL + 40, y, f"${bal}")
        y -= 22
    c.save()


def test_rbc_style_pdf_parses_credits_and_debits(tmp_path):
    pdf = tmp_path / "rbc.pdf"
    _make_pdf(pdf)

    result = extract_file(pdf, currency="CAD")
    assert result.ok, result.error
    assert len(result.transactions) == len(ROWS)

    by_desc = {t.normalized_desc: t for t in result.transactions}

    layne = next(t for d, t in by_desc.items() if "LAYNE" in d)
    assert layne.direction == "credit"
    assert layne.amount_cents == 32000

    landscaping = next(t for d, t in by_desc.items() if "LANDSCAPING" in d)
    assert landscaping.direction == "credit"
    assert landscaping.amount_cents == 139161

    interest = next(t for d, t in by_desc.items() if "INTEREST" in d)
    assert interest.direction == "credit"
    assert interest.amount_cents == 22

    wd = next(t for t in result.transactions if t.amount_cents == 7000)
    assert wd.direction == "debit"
    assert "DEPOSIT ACCOUNT" in wd.normalized_desc

    # Balances must never be mistaken for transaction amounts.
    assert all(t.amount_cents not in (68883, 22883, 29883, 139883, 618)
               for t in result.transactions)

    credits = sum(t.amount_cents for t in result.transactions if t.direction == "credit")
    debits = sum(t.amount_cents for t in result.transactions if t.direction == "debit")
    assert credits == 32000 + 139161 + 22       # deposits
    assert debits == 7000 + 110000 + 90500      # withdrawals
