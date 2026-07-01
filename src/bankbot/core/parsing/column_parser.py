"""Column-aware parser for tabular statements (RBC, CIBC, and similar).

Many bank statements use separate money columns:

    DATE        DESCRIPTION              WITHDRAWALS   DEPOSITS   BALANCE

A plain line parser can't tell a $200 deposit from a $200 withdrawal — both read
as "200.00". This parser uses each amount's horizontal (x) position to place it in
the right column, so deposits become credits (income) and withdrawals become
debits. It relies on word coordinates from pdfplumber; when the tell-tale
Withdrawals/Deposits header pair isn't found it returns ``[]`` and the caller falls
back to the generic line parser.
"""
from __future__ import annotations

import re

from .base import ParsedTxn, parse_date, parse_money

_ROW_TOLERANCE = 3.0  # words within this many points of `top` share a row

# Header keywords -> logical column. Tokens are stripped to letters before matching.
_WITHDRAWAL_HEADERS = {"WITHDRAWAL", "WITHDRAWALS", "DEBIT", "DEBITS", "WITHDRAWN",
                       "PAYMENTS", "PAIDOUT", "MONEYOUT"}
_DEPOSIT_HEADERS = {"DEPOSIT", "DEPOSITS", "CREDIT", "CREDITS", "PAIDIN", "MONEYIN"}
_BALANCE_HEADERS = {"BALANCE"}

_MONEY_WORD_RE = re.compile(r"^-?\$?\d[\d,]*\.\d{2}$")


def _letters(token: str) -> str:
    return re.sub(r"[^A-Z]", "", token.upper())


def _is_money_word(token: str) -> bool:
    return bool(_MONEY_WORD_RE.match(token))


def _center(word: dict) -> float:
    return (word["x0"] + word["x1"]) / 2


def _cluster_rows(words: list[dict]) -> list[list[dict]]:
    """Group words into visual rows by their `top` coordinate, sorted left→right."""
    rows: list[list[dict]] = []
    for word in sorted(words, key=lambda w: (w["top"], w["x0"])):
        if rows and abs(word["top"] - rows[-1][0]["top"]) <= _ROW_TOLERANCE:
            rows[-1].append(word)
        else:
            rows.append([word])
    for row in rows:
        row.sort(key=lambda w: w["x0"])
    return rows


def _detect_columns(rows: list[list[dict]]) -> dict[str, float] | None:
    """Find the header row and return {column: x_center}.

    Requires BOTH a withdrawal-type and a deposit-type header (the defining shape of
    these statements); balance is optional.
    """
    for row in rows:
        centers: dict[str, float] = {}
        for word in row:
            letters = _letters(word["text"])
            if letters in _WITHDRAWAL_HEADERS and "withdrawal" not in centers:
                centers["withdrawal"] = _center(word)
            elif letters in _DEPOSIT_HEADERS and "deposit" not in centers:
                centers["deposit"] = _center(word)
            elif letters in _BALANCE_HEADERS and "balance" not in centers:
                centers["balance"] = _center(word)
        if "withdrawal" in centers and "deposit" in centers:
            return centers
    return None


def _nearest_column(x: float, centers: dict[str, float]) -> str:
    return min(centers, key=lambda name: abs(x - centers[name]))


def parse_pages(pages: list[list[dict]], year: int) -> list[ParsedTxn]:
    """Parse every page that has a Withdrawals/Deposits column header."""
    txns: list[ParsedTxn] = []
    for words in pages:
        if not words:
            continue
        rows = _cluster_rows(words)
        centers = _detect_columns(rows)
        if not centers:
            continue
        txns.extend(_parse_rows(rows, centers, year))
    return txns


def _parse_rows(rows: list[list[dict]], centers: dict[str, float], year: int) -> list[ParsedTxn]:
    out: list[ParsedTxn] = []
    current: ParsedTxn | None = None
    for row in rows:
        row_text = " ".join(w["text"] for w in row)
        money_words = [w for w in row if _is_money_word(w["text"])]
        date_hit = parse_date(row_text, year)

        # Continuation line (wrapped description): no date, no money.
        if date_hit is None and not money_words:
            if current is not None:
                extra = row_text.strip()
                if extra:
                    current.description = f"{current.description} {extra}".strip()
                    current.finalize()
            continue

        # A new transaction needs a date; rows with only a stray balance are skipped.
        if date_hit is None:
            continue

        txn_date, _dstart, dend = date_hit
        amount_cents, direction = _classify_amounts(money_words, centers)
        if amount_cents is None:
            # Dated row with only a balance figure (e.g. opening balance) — skip.
            current = None
            continue

        first_money_x0 = min(w["x0"] for w in money_words)
        desc_words = [w["text"] for w in row if w["x0"] < first_money_x0]
        desc = " ".join(desc_words)
        # Drop the leading date from the description.
        desc_date = parse_date(desc, year)
        if desc_date is not None:
            desc = desc[desc_date[2]:].strip(" -\t")
        else:
            desc = row_text[dend:].strip(" -\t")

        current = ParsedTxn(txn_date, desc or row_text, amount_cents, direction).finalize()
        out.append(current)
    return out


def _classify_amounts(
    money_words: list[dict], centers: dict[str, float]
) -> tuple[int | None, str]:
    """Pick the transaction amount + direction from a row's money words by column."""
    withdrawal_cents: int | None = None
    deposit_cents: int | None = None
    for word in money_words:
        parsed = parse_money(word["text"])
        if not parsed:
            continue
        cents, _neg = parsed
        column = _nearest_column(_center(word), centers)
        if column == "withdrawal" and withdrawal_cents is None:
            withdrawal_cents = cents
        elif column == "deposit" and deposit_cents is None:
            deposit_cents = cents
        # 'balance' column amounts are ignored.
    if withdrawal_cents:
        return withdrawal_cents, "debit"
    if deposit_cents:
        return deposit_cents, "credit"
    return None, "debit"
