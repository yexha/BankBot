"""The risk sliders must ALWAYS sum to 100 and never go negative."""
from __future__ import annotations

import random

import pytest

from bankbot.core.allocation import (
    monthly_investment_cents,
    normalize_split,
    rebalance,
    split_amount,
)


def _valid(split: dict[str, int]) -> bool:
    return sum(split.values()) == 100 and all(v >= 0 for v in split.values())


def test_rebalance_keeps_sum_100_for_every_move():
    values = {"high": 20, "med": 40, "low": 40}
    for _ in range(2000):
        changed = random.choice(list(values))
        new_value = random.randint(-50, 150)  # deliberately out of range
        values = rebalance(values, changed, new_value)
        assert _valid(values), values


def test_rebalance_clamps_and_sets_target():
    out = rebalance({"high": 33, "med": 33, "low": 34}, "high", 100)
    assert out["high"] == 100 and out["med"] == 0 and out["low"] == 0
    out = rebalance({"high": 33, "med": 33, "low": 34}, "high", -10)
    assert out["high"] == 0 and _valid(out)


def test_rebalance_even_split_when_others_zero():
    out = rebalance({"high": 100, "med": 0, "low": 0}, "high", 40)
    assert out == {"high": 40, "med": 30, "low": 30}


def test_rebalance_proportional():
    # med:low = 2:1, remaining 40 -> ~27/13
    out = rebalance({"high": 40, "med": 40, "low": 20}, "high", 60)
    assert out["high"] == 60
    assert out["med"] + out["low"] == 40
    assert out["med"] > out["low"]


@pytest.mark.parametrize("values", [
    {"high": 0, "med": 0, "low": 0},
    {"high": 10, "med": 10, "low": 10},
    {"high": 200, "med": 50, "low": 0},
])
def test_normalize_split(values):
    assert _valid(normalize_split(values))


def test_split_amount_sums_exactly():
    parts = split_amount(10001, {"high": 33, "med": 33, "low": 34})
    assert sum(parts.values()) == 10001
    assert all(v >= 0 for v in parts.values())


def test_split_amount_zero():
    parts = split_amount(0, {"high": 50, "med": 30, "low": 20})
    assert sum(parts.values()) == 0


def test_monthly_investment():
    assert monthly_investment_cents(100000, 50) == 50000
    assert monthly_investment_cents(100000, 0) == 0
    assert monthly_investment_cents(-5000, 50) == 0     # negative leftover -> 0
    assert monthly_investment_cents(100000, 150) == 100000  # clamps to 100%
