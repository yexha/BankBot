"""Generic line parsing, dedupe-hash stability, and error handling."""
from __future__ import annotations

from datetime import date

from bankbot.core.parsing.base import ParsedTxn, parse_generic, parse_money
from bankbot.core.parsing.extractor import extract_file
from bankbot.core.parsing.profiles import choose_profile

SAMPLE = """
ACME BANK STATEMENT 2026
Account activity
Jan 03  LOBLAWS #123 GROCERY           45.20
Jan 05  NETFLIX.COM                     16.99
Jan 06  ACME CORP PAYROLL DEPOSIT      2,500.00 CR
Jan 08  ATM WITHDRAWAL                  100.00
Jan 15  INTERAC E-TRANSFER SENT       1,500.00
"""


def test_parse_money():
    assert parse_money("1,234.56") == (123456, False)
    assert parse_money("(45.00)") == (4500, True)
    assert parse_money("$16.99") == (1699, False)
    assert parse_money("nonsense") is None


def test_parse_generic_extracts_rows():
    txns = parse_generic(SAMPLE, default_year=2026)
    descs = [t.normalized_desc for t in txns]
    assert any("LOBLAWS" in d for d in descs)
    assert any("NETFLIX" in d for d in descs)
    assert len(txns) == 5
    payroll = next(t for t in txns if "PAYROLL" in t.normalized_desc)
    assert payroll.direction == "credit"
    assert payroll.amount_cents == 250000
    atm = next(t for t in txns if "ATM" in t.normalized_desc)
    assert atm.direction == "debit"


def test_dedupe_hash_is_stable_and_distinct():
    a = ParsedTxn(date(2026, 1, 3), "LOBLAWS #123", 4520, "debit").finalize()
    b = ParsedTxn(date(2026, 1, 3), "LOBLAWS #123", 4520, "debit").finalize()
    c = ParsedTxn(date(2026, 1, 3), "LOBLAWS #123", 4521, "debit").finalize()
    assert a.dedupe_hash == b.dedupe_hash
    assert a.dedupe_hash != c.dedupe_hash


def test_choose_profile_detects_and_falls_back():
    assert choose_profile("Welcome to RBC Royal Bank").name == "rbc"
    assert choose_profile("random text with no bank").name == "generic"


def test_extract_missing_file_reports_error():
    result = extract_file("/nonexistent/does-not-exist.pdf")
    assert not result.ok
    assert result.error


def test_extract_unsupported_type(tmp_path):
    f = tmp_path / "note.txt"
    f.write_text("hello")
    result = extract_file(f)
    assert not result.ok
    assert "Unsupported" in result.error or "Could not read" in result.error
