"""Ambiguity detection -> review-queue flagging.

Critical requirement: cash withdrawals, e-transfers, and generic/unrecognized
descriptions must NEVER be auto-tagged as want or silently ignored. They are
forced into the manual review queue instead.
"""
from __future__ import annotations

CASH_KEYWORDS = ("ATM", "ABM", "WITHDRAWAL", "CASH WITHDRAWAL", "CASH ADVANCE")
ETRANSFER_KEYWORDS = (
    "INTERAC", "E-TRANSFER", "ETRANSFER", "E-TFR", "EMAIL TRF", "EMAIL TRANSFER",
    "SEND MONEY", "ETRNSFR", "E TRANSFER",
)


def is_etransfer(normalized_desc: str) -> bool:
    return any(k in normalized_desc for k in ETRANSFER_KEYWORDS)


def is_cash_withdrawal(normalized_desc: str) -> bool:
    return any(k in normalized_desc for k in CASH_KEYWORDS)


def forced_review_reason(normalized_desc: str) -> str | None:
    """Return a human reason if this debit must go to review, else None."""
    if is_cash_withdrawal(normalized_desc):
        return "cash withdrawal — tell us what this was for"
    if is_etransfer(normalized_desc):
        return "e-transfer — is this a bill (e.g. rent) or a want?"
    return None
