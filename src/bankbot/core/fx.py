"""Currency conversion using a stored manual/cached rate (no paid FX API).

The stored rate is CAD per 1 USD (e.g. 1.35). Conversions are exact in cents with
half-up rounding.
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal


def convert(amount_cents: int, from_cur: str, to_cur: str, cad_per_usd: float | str) -> int:
    """Convert a cent amount between CAD and USD. Unknown pairs return unchanged."""
    from_cur, to_cur = from_cur.upper(), to_cur.upper()
    if from_cur == to_cur:
        return amount_cents
    rate = Decimal(str(cad_per_usd))
    if rate <= 0:
        return amount_cents
    amt = Decimal(amount_cents)
    if from_cur == "USD" and to_cur == "CAD":
        result = amt * rate
    elif from_cur == "CAD" and to_cur == "USD":
        result = amt / rate
    else:
        return amount_cents
    return int(result.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
