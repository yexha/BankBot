# BankBot

A **local-first** personal finance & investment-allocation desktop app for
Windows 11. It ingests PDF/PNG bank statements, categorizes spending, computes
your leftover money, and helps you plan savings goals and a risk-tiered
investment allocation.

BankBot is a **planning and allocation tool** — it does not pick stocks, predict
markets, move money, or upload your data anywhere. Everything runs locally.

> ⚠️ **Not financial advice.** BankBot provides general budgeting and allocation
> guidance based on your own data and general financial principles. It is not
> personalized financial, investment, or tax advice, and it cannot predict market
> performance. Consult a licensed financial advisor for investment decisions.

## Status — core foundation (build pass 1)

Implemented and unit-tested:

1. Project scaffold, local SQLite schema, PySide6 app shell with a persistent
   disclaimer banner.
2. PDF/PNG import pipeline (pdfplumber text + Tesseract/pdf2image OCR fallback),
   deduplicated storage, background parsing so the UI never freezes.
3. Categorization engine + income detection + **review queue** — cash withdrawals,
   e-transfers and unrecognized descriptions are never auto-tagged; you confirm
   them and BankBot remembers the payee.
4. Monthly income vs cost summary with category breakdown.
5. Savings goals with required-monthly-contribution math and **leftover-after-goals**.
6. Investment allocation: monthly-invest slider + three risk sliders that always
   sum to 100%, with transparent allocation models and plain-language reasoning.

Planned for the next pass: TFSA/FHSA account-optimization popup, CSV/PDF export,
and PyInstaller single-`.exe` packaging (bundling Tesseract + poppler).

## Architecture

- `src/bankbot/core/` — pure logic (parsing, categorization, budget/goal/allocation
  math, DB). **No Qt imports**, so it is fully unit-testable.
- `src/bankbot/ui/` — all PySide6 code (pages, widgets, background workers).
- `tests/` — unit tests for the money math and parsing (run headless in CI).

Money is stored as **integer cents** to avoid floating-point drift.

## Running (development)

```bash
pip install -r requirements.txt
python run.py
```

OCR of scanned PDFs/PNGs additionally needs Tesseract and poppler on the PATH
(these will be bundled into the packaged `.exe`). Text-based PDFs work without them.

## Tests

```bash
pip install SQLAlchemy pytest
python -m pytest
```

Your data lives in `%APPDATA%/BankBot/bankbot.db` on Windows (a per-user data dir
elsewhere). It is never uploaded.
