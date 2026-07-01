"""Savings-goal math.

Required monthly contribution to hit a goal by its target date, plus allocation of
those contributions against available leftover in user-priority order. Goal money
is reserved *before* the investment slider math (``leftover after goals``).
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from math import ceil
from typing import Protocol


class _GoalLike(Protocol):
    name: str
    target_amount_cents: int
    target_date: date
    current_saved_cents: int
    priority: int


def months_between(start: date, end: date) -> int:
    """Whole months from ``start`` to ``end``; never negative (0 if end has passed)."""
    months = (end.year - start.year) * 12 + (end.month - start.month)
    if end.day < start.day:
        months -= 1
    return max(months, 0)


def required_monthly(goal: _GoalLike, today: date | None = None) -> int:
    """Cents/month needed to reach the goal. 0 if already met.

    If the target date is in the past/this month, the full remaining amount is
    treated as due now (1 month) rather than dividing by zero.
    """
    today = today or date.today()
    remaining = goal.target_amount_cents - goal.current_saved_cents
    if remaining <= 0:
        return 0
    months = months_between(today, goal.target_date)
    months = max(months, 1)
    return ceil(remaining / months)


@dataclass
class GoalPlanItem:
    name: str
    required_cents: int
    funded_cents: int
    fully_funded: bool


@dataclass
class GoalPlan:
    items: list[GoalPlanItem]
    total_required_cents: int
    total_funded_cents: int
    leftover_after_goals_cents: int

    @property
    def underfunded(self) -> bool:
        return self.total_funded_cents < self.total_required_cents


def plan_goals(
    goals: Sequence[_GoalLike], leftover_cents: int, today: date | None = None
) -> GoalPlan:
    """Allocate ``leftover_cents`` to goals by priority; never goes negative.

    Goals are funded in priority order (lower ``priority`` value first). If leftover
    runs out, later goals are partially/zero funded and ``underfunded`` is True.
    """
    ordered = sorted(goals, key=lambda g: g.priority)
    remaining = max(leftover_cents, 0)
    items: list[GoalPlanItem] = []
    total_required = 0
    total_funded = 0
    for g in ordered:
        req = required_monthly(g, today)
        funded = min(req, remaining)
        remaining -= funded
        total_required += req
        total_funded += funded
        items.append(GoalPlanItem(g.name, req, funded, funded >= req))
    leftover_after = max(leftover_cents, 0) - total_funded
    return GoalPlan(items, total_required, total_funded, leftover_after)
