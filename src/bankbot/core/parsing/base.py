"""Parsing primitives: ParsedTxn, the BankProfile interface, and a robust generic
line parser used as the fallback for unknown formats.

The generic parser is intentionally forgiving: it extracts a date, a description
and the trailing amount from each line and infers direction from sign/keywords.
Whatever it can't confidently place still flows into the review queue downstream,
so imperfect parsing never silently mis-tags money.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import date

from ..money import to_cents
from ..text import normalize_description

_MONTHS = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
}

# Money like 1,234.56 or 1234.56 optionally with $, sign, parentheses, CR/DR.
_MONEY_RE = re.compile(r"\(?-?\$?\s?\d{1,3}(?:,\d{3})*(?:\.\d{2})\)?")
_ISO_DATE_RE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_NUM_DATE_RE = re.compile(r"\b(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\b")
_MON_DATE_RE = re.compile(r"\b([A-Za-z]{3,9})\.?\s+(\d{1,2})\b")
_DAY_MON_RE = re.compile(r"\b(\d{1,2})\s+([A-Za-z]{3,9})\b")
_YEAR_RE = re.compile(r"\b(20\d{2})\b")

_CREDIT_HINTS = ("CR", "DEPOSIT", "CREDIT", "PAYROLL", "REFUND", "REBATE", "PYMT RCVD")
_DEBIT_HINTS = ("DR", "WITHDRAWAL", "DEBIT", "PURCHASE", "PAYMENT", "FEE", "POS")


@dataclass
class ParsedTxn:
    txn_date: date
    description: str
    amount_cents: int
    direction: str            # 'debit' | 'credit'
    currency: str = "CAD"
    normalized_desc: str = ""
    dedupe_hash: str = ""

    def finalize(self) -> "ParsedTxn":
        """Fill normalized_desc + dedupe_hash. Idempotent."""
        self.normalized_desc = normalize_description(self.description)
        key = f"{self.txn_date.isoformat()}|{self.amount_cents}|{self.normalized_desc}"
        self.dedupe_hash = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self


class BankProfile:
    """Base profile. Subclasses set ``name``/``display`` and override ``detect``."""

    name = "generic"
    display = "Generic"
    keywords: tuple[str, ...] = ()

    def detect(self, text: str) -> bool:
        upper = text.upper()
        return any(k in upper for k in self.keywords)

    def parse(self, text: str, default_year: int) -> list[ParsedTxn]:
        return parse_generic(text, default_year)


# --- helpers ------------------------------------------------------------------
def detect_year(text: str) -> int:
    m = _YEAR_RE.search(text)
    return int(m.group(1)) if m else date.today().year


def parse_money(token: str) -> tuple[int, bool] | None:
    """Return (cents, is_negative) for a money token, or None if unparseable."""
    t = token.strip()
    negative = t.startswith("(") and t.endswith(")") or t.lstrip().startswith("-")
    cleaned = t.replace("(", "").replace(")", "").replace("$", "").replace(",", "").strip()
    cleaned = cleaned.lstrip("-").strip()
    if not cleaned:
        return None
    try:
        return to_cents(cleaned), negative
    except ValueError:
        return None


def parse_date(line: str, default_year: int) -> tuple[date, int, int] | None:
    """Find the first date in a line. Returns (date, match_start, match_end)."""
    m = _ISO_DATE_RE.search(line)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3))), m.start(), m.end()
        except ValueError:
            return None
    m = _MON_DATE_RE.search(line)
    if m and m.group(1).upper()[:3] in _MONTHS:
        try:
            return date(default_year, _MONTHS[m.group(1).upper()[:3]], int(m.group(2))), \
                m.start(), m.end()
        except ValueError:
            return None
    m = _DAY_MON_RE.search(line)
    if m and m.group(2).upper()[:3] in _MONTHS:
        try:
            return date(default_year, _MONTHS[m.group(2).upper()[:3]], int(m.group(1))), \
                m.start(), m.end()
        except ValueError:
            return None
    m = _NUM_DATE_RE.search(line)
    if m:
        mm, dd = int(m.group(1)), int(m.group(2))
        yy = m.group(3)
        year = default_year if yy is None else (int(yy) if len(yy) == 4 else 2000 + int(yy))
        if mm > 12 and dd <= 12:      # looks like DD/MM
            mm, dd = dd, mm
        try:
            return date(year, mm, dd), m.start(), m.end()
        except ValueError:
            return None
    return None


def infer_direction(line: str, negative: bool) -> str:
    upper = line.upper()
    if negative:
        return "debit"
    # Word-boundary check for short hints like CR/DR to avoid false hits.
    if any(re.search(rf"\b{h}\b", upper) for h in _CREDIT_HINTS):
        return "credit"
    if any(re.search(rf"\b{h}\b", upper) for h in _DEBIT_HINTS):
        return "debit"
    return "debit"


def parse_generic(text: str, default_year: int) -> list[ParsedTxn]:
    """Best-effort line-oriented parse. Never raises on a bad line."""
    txns: list[ParsedTxn] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if len(line) < 6:
            continue
        try:
            found = parse_date(line, default_year)
            if not found:
                continue
            txn_date, _dstart, dend = found
            monies = list(_MONEY_RE.finditer(line))
            if not monies:
                continue
            money_match = monies[-1]
            parsed = parse_money(money_match.group(0))
            if not parsed:
                continue
            cents, negative = parsed
            if cents == 0:
                continue
            desc = line[dend:money_match.start()].strip(" -\t")
            if not desc:
                desc = line[dend:].strip(" -\t")
            direction = infer_direction(line, negative)
            txns.append(
                ParsedTxn(txn_date, desc or line, cents, direction).finalize()
            )
        except Exception:
            # A single malformed line must never abort the whole import.
            continue
    return txns
