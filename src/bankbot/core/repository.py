"""Query/CRUD helpers used by both the UI and the logic layers."""
from __future__ import annotations

from datetime import date

from sqlalchemy import func, select

from .db import session_scope
from .models import Goal, Rule, Setting, Transaction


# --- Settings -----------------------------------------------------------------
def get_setting(key: str, default: str | None = None) -> str | None:
    with session_scope() as s:
        row = s.get(Setting, key)
        return row.value if row else default


def set_setting(key: str, value: str) -> None:
    with session_scope() as s:
        row = s.get(Setting, key)
        if row:
            row.value = value
        else:
            s.add(Setting(key=key, value=str(value)))


def get_settings(*keys: str) -> dict[str, str | None]:
    return {k: get_setting(k) for k in keys}


# --- Transactions -------------------------------------------------------------
def transactions_for_month(year: int, month: int) -> list[Transaction]:
    """All transactions whose date falls in the given calendar month."""
    start = date(year, month, 1)
    end = date(year + (month == 12), (month % 12) + 1, 1)
    with session_scope() as s:
        stmt = (
            select(Transaction)
            .where(Transaction.txn_date >= start, Transaction.txn_date < end)
            .order_by(Transaction.txn_date)
        )
        return list(s.scalars(stmt).all())


def available_months() -> list[tuple[int, int]]:
    """Distinct (year, month) pairs that have transactions, newest first."""
    with session_scope() as s:
        rows = s.scalars(select(Transaction.txn_date)).all()
    months = {(d.year, d.month) for d in rows}
    return sorted(months, reverse=True)


def latest_month() -> tuple[int, int]:
    """Most recent month with data, else the current calendar month."""
    months = available_months()
    if months:
        return months[0]
    today = date.today()
    return (today.year, today.month)


def review_queue() -> list[Transaction]:
    with session_scope() as s:
        stmt = (
            select(Transaction)
            .where(Transaction.review_status == "needs_review")
            .order_by(Transaction.txn_date)
        )
        return list(s.scalars(stmt).all())


def all_transactions() -> list[Transaction]:
    """Every transaction, newest first — used by the 'override anything' review view."""
    with session_scope() as s:
        stmt = select(Transaction).order_by(Transaction.txn_date.desc())
        return list(s.scalars(stmt).all())


# --- Goals --------------------------------------------------------------------
def list_goals() -> list[Goal]:
    with session_scope() as s:
        return list(s.scalars(select(Goal).order_by(Goal.priority)).all())


def add_goal(
    name: str, target_cents: int, target_date: date, saved_cents: int = 0,
    currency: str = "CAD",
) -> int:
    with session_scope() as s:
        max_pri = s.scalar(select(func.max(Goal.priority)))
        goal = Goal(
            name=name, target_amount_cents=target_cents, target_date=target_date,
            current_saved_cents=saved_cents, currency=currency,
            priority=(max_pri + 1) if max_pri is not None else 0,
        )
        s.add(goal)
        s.flush()
        return goal.id


def delete_goal(goal_id: int) -> None:
    with session_scope() as s:
        goal = s.get(Goal, goal_id)
        if goal:
            s.delete(goal)


def move_goal(goal_id: int, direction: int) -> None:
    """Swap a goal's priority with its neighbour (-1 = up, +1 = down)."""
    with session_scope() as s:
        goals = list(s.scalars(select(Goal).order_by(Goal.priority)).all())
        idx = next((i for i, g in enumerate(goals) if g.id == goal_id), None)
        if idx is None:
            return
        swap = idx + direction
        if 0 <= swap < len(goals):
            goals[idx].priority, goals[swap].priority = (
                goals[swap].priority, goals[idx].priority,
            )


def active_rules() -> list[Rule]:
    """All rules, highest priority first (user-confirmed before builtin)."""
    with session_scope() as s:
        return list(s.scalars(select(Rule).order_by(Rule.priority.desc())).all())
