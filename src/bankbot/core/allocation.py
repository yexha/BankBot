"""Risk-allocation math.

The three risk sliders (High / Medium / Low) must ALWAYS sum to exactly 100 and
none may go negative — a classic source of UI drift. ``rebalance`` recomputes the
other two proportionally whenever one slider moves, using largest-remainder
rounding so the integer percentages sum to exactly 100.
"""
from __future__ import annotations

TIERS = ("high", "med", "low")


def rebalance(values: dict[str, int], changed: str, new_value: int) -> dict[str, int]:
    """Return a new split after the user sets ``changed`` to ``new_value``.

    Guarantees: every value in [0, 100], total == 100. The remaining budget is
    distributed across the other two tiers in proportion to their previous values
    (evenly if both were zero).
    """
    if changed not in values:
        raise KeyError(changed)
    new_value = max(0, min(100, int(round(new_value))))
    others = [k for k in values if k != changed]
    remaining = 100 - new_value

    prev_sum = sum(values[k] for k in others)
    result = {changed: new_value}

    if prev_sum <= 0:
        base, rem = divmod(remaining, len(others))
        for k in others:
            result[k] = base
        for k in others[:rem]:
            result[k] += 1
        return result

    raw = {k: remaining * values[k] / prev_sum for k in others}
    floored = {k: int(raw[k]) for k in others}
    leftover = remaining - sum(floored.values())
    # Hand the leftover units to the largest fractional remainders first.
    for k in sorted(others, key=lambda k: raw[k] - floored[k], reverse=True)[:leftover]:
        floored[k] += 1
    result.update(floored)
    return result


def normalize_split(values: dict[str, int]) -> dict[str, int]:
    """Clamp to non-negative and scale to sum exactly 100 (defaults to even)."""
    clean = {k: max(0, int(v)) for k, v in values.items()}
    total = sum(clean.values())
    if total == 0:
        base, rem = divmod(100, len(clean))
        out = {k: base for k in clean}
        for k in list(clean)[:rem]:
            out[k] += 1
        return out
    raw = {k: 100 * v / total for k, v in clean.items()}
    floored = {k: int(raw[k]) for k in clean}
    leftover = 100 - sum(floored.values())
    for k in sorted(clean, key=lambda k: raw[k] - floored[k], reverse=True)[:leftover]:
        floored[k] += 1
    return floored


def split_amount(amount_cents: int, pct: dict[str, int]) -> dict[str, int]:
    """Split a cent amount by percentages so the parts sum to exactly the input."""
    amount_cents = max(0, int(amount_cents))
    total_pct = sum(pct.values()) or 1
    raw = {k: amount_cents * v / total_pct for k, v in pct.items()}
    floored = {k: int(raw[k]) for k in pct}
    leftover = amount_cents - sum(floored.values())
    for k in sorted(pct, key=lambda k: raw[k] - floored[k], reverse=True)[:leftover]:
        floored[k] += 1
    return floored


def monthly_investment_cents(leftover_after_goals_cents: int, invest_pct: int) -> int:
    """Dollar amount (cents) to invest per month from leftover-after-goals."""
    invest_pct = max(0, min(100, int(invest_pct)))
    return max(0, leftover_after_goals_cents) * invest_pct // 100
