"""Suggested invest % — a transparent heuristic, not a market prediction."""
from __future__ import annotations

from bankbot.core.advice import suggest_invest_pct


def test_zero_leftover_suggests_zero():
    s = suggest_invest_pct(0, 200000)
    assert s.pct == 0
    assert s.monthly_cents == 0
    assert s.reasons


def test_no_essentials_uses_balanced_default():
    s = suggest_invest_pct(100000, 0)
    assert s.pct == 70
    assert s.monthly_cents == 70000


def test_scales_with_surplus_vs_essentials():
    # small surplus vs essentials -> lower %, large surplus -> higher (capped 85)
    low = suggest_invest_pct(50000, 100000)     # ratio 0.5 -> 60
    mid = suggest_invest_pct(100000, 100000)    # ratio 1.0 -> 70
    high = suggest_invest_pct(500000, 100000)   # ratio 5 -> capped 85
    assert low.pct == 60
    assert mid.pct == 70
    assert high.pct == 85
    assert 50 <= low.pct <= mid.pct <= high.pct <= 85


def test_monthly_amount_matches_pct():
    s = suggest_invest_pct(100000, 100000)
    assert s.monthly_cents == 100000 * s.pct // 100


def test_emergency_fund_range_reported():
    s = suggest_invest_pct(100000, 200000)
    assert s.emergency_low_cents == 200000 * 3
    assert s.emergency_high_cents == 200000 * 6
