"""Goal contribution math and priority-ordered funding."""
from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from bankbot.core.goals import months_between, plan_goals, required_monthly


def goal(name, target, target_date, saved=0, priority=0):
    return SimpleNamespace(
        name=name, target_amount_cents=target, target_date=target_date,
        current_saved_cents=saved, priority=priority,
    )


def test_months_between():
    assert months_between(date(2026, 1, 1), date(2026, 12, 1)) == 11
    assert months_between(date(2026, 1, 15), date(2026, 2, 1)) == 0  # <1 whole month
    assert months_between(date(2026, 6, 1), date(2026, 1, 1)) == 0  # past -> 0


def test_required_monthly_basic():
    g = goal("Vehicle", 1_500_000, date(2027, 12, 1))  # $15,000
    req = required_monthly(g, today=date(2026, 6, 1))   # 18 months
    assert req == 1_500_000 // 18 or req == (1_500_000 + 17) // 18


def test_required_monthly_already_met():
    g = goal("Done", 100000, date(2027, 1, 1), saved=100000)
    assert required_monthly(g, today=date(2026, 1, 1)) == 0


def test_required_monthly_past_due_is_full_amount():
    g = goal("Late", 120000, date(2025, 1, 1))
    assert required_monthly(g, today=date(2026, 6, 1)) == 120000  # 1 month


def test_plan_goals_priority_and_leftover():
    today = date(2026, 1, 1)
    g1 = goal("A", 120000, date(2026, 12, 1), priority=0)   # ~10909/mo
    g2 = goal("B", 120000, date(2026, 12, 1), priority=1)
    plan = plan_goals([g2, g1], leftover_cents=15000, today=today)
    # Priority 0 funded first and fully; priority 1 gets the remainder.
    assert plan.items[0].name == "A"
    assert plan.items[0].fully_funded
    assert not plan.items[1].fully_funded
    assert plan.leftover_after_goals_cents == 15000 - plan.total_funded_cents
    assert plan.leftover_after_goals_cents >= 0
    assert plan.underfunded


def test_plan_goals_never_negative_leftover():
    today = date(2026, 1, 1)
    g = goal("Big", 10_000_000, date(2026, 2, 1), priority=0)
    plan = plan_goals([g], leftover_cents=5000, today=today)
    assert plan.leftover_after_goals_cents == 0
    assert plan.total_funded_cents == 5000
    assert plan.underfunded


def test_plan_goals_full_surplus():
    today = date(2026, 1, 1)
    g = goal("Small", 12000, date(2026, 12, 1), priority=0)  # 1000/mo
    plan = plan_goals([g], leftover_cents=50000, today=today)
    assert plan.items[0].fully_funded
    assert not plan.underfunded
    assert plan.leftover_after_goals_cents == 50000 - plan.total_funded_cents
