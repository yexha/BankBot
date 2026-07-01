"""Money helpers.

All monetary amounts are stored as **integer cents** to avoid floating-point
drift in budget and goal math. Conversions happen only at the UI boundary.
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation


def to_cents(value: float | int | str | Decimal) -> int:
    """Convert a dollar amount to integer cents, rounding half-up.

    Raises ``ValueError`` on input that cannot be interpreted as money.
    """
    try:
        d = Decimal(str(value).replace(",", "").replace("$", "").strip())
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Not a monetary value: {value!r}") from exc
    cents = (d * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(cents)


def to_dollars(cents: int) -> Decimal:
    """Convert integer cents back to a Decimal dollar amount."""
    return (Decimal(int(cents)) / 100).quantize(Decimal("0.01"))


def format_money(cents: int, currency: str = "CAD") -> str:
    """Human-readable money string, e.g. ``$1,234.56 CAD``."""
    dollars = to_dollars(cents)
    sign = "-" if dollars < 0 else ""
    return f"{sign}${abs(dollars):,.2f} {currency}"
