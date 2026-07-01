"""Build and export a budget-breakdown report (CSV / PDF).

Gathers the month's summary, category breakdown, goal plan, and investment
allocation into one report, then writes CSV (stdlib) or PDF (reportlab, lazy
import). All amounts are formatted at the boundary; math stays in cents.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from .. import config
from . import repository as repo
from .allocation import monthly_investment_cents, normalize_split, split_amount
from .budget import summarize
from .goals import plan_goals
from .money import format_money

EXPORT_DISCLAIMER = config.DISCLAIMER

_MONTHS = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


@dataclass
class Report:
    year: int
    month: int
    currency: str = "CAD"
    income_cents: int = 0
    essential_cents: int = 0
    want_cents: int = 0
    leftover_cents: int = 0
    needs_review_count: int = 0
    categories: list[tuple[str, int]] = field(default_factory=list)
    goals: list[tuple[str, int, int]] = field(default_factory=list)  # name, required, funded
    reserved_for_goals_cents: int = 0
    leftover_after_goals_cents: int = 0
    monthly_invest_cents: int = 0
    risk_split: dict[str, int] = field(default_factory=dict)
    risk_amounts: dict[str, int] = field(default_factory=dict)

    @property
    def period_label(self) -> str:
        return f"{_MONTHS[self.month]} {self.year}"


def build_report(year: int, month: int) -> Report:
    currency = repo.get_setting("currency", "CAD") or "CAD"
    txns = repo.transactions_for_month(year, month)
    summary = summarize(txns)

    goal_rows = repo.list_goals()
    plan = plan_goals(goal_rows, summary.leftover_cents)

    invest_pct = int(repo.get_setting("monthly_invest_pct", "50") or "50")
    monthly = monthly_investment_cents(plan.leftover_after_goals_cents, invest_pct)
    split = normalize_split({
        "high": int(repo.get_setting("risk_high_pct", "20") or "20"),
        "med": int(repo.get_setting("risk_med_pct", "40") or "40"),
        "low": int(repo.get_setting("risk_low_pct", "40") or "40"),
    })
    amounts = split_amount(monthly, split)

    return Report(
        year=year,
        month=month,
        currency=currency,
        income_cents=summary.income_cents,
        essential_cents=summary.essential_cents,
        want_cents=summary.want_cents,
        leftover_cents=summary.leftover_cents,
        needs_review_count=summary.needs_review_count,
        categories=sorted(summary.by_category.items(), key=lambda kv: kv[1], reverse=True),
        goals=[(g.name, i.required_cents, i.funded_cents)
               for g, i in zip(goal_rows, plan.items)],
        reserved_for_goals_cents=plan.total_funded_cents,
        leftover_after_goals_cents=plan.leftover_after_goals_cents,
        monthly_invest_cents=monthly,
        risk_split=split,
        risk_amounts=amounts,
    )


def export_csv(path: Path | str, report: Report) -> None:
    cur = report.currency
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["BankBot budget summary", report.period_label])
        w.writerow([])
        w.writerow(["Section", "Item", "Amount"])
        w.writerow(["Totals", "Income", format_money(report.income_cents, cur)])
        w.writerow(["Totals", "Essential", format_money(report.essential_cents, cur)])
        w.writerow(["Totals", "Wants", format_money(report.want_cents, cur)])
        w.writerow(["Totals", "Leftover", format_money(report.leftover_cents, cur)])
        w.writerow([])
        for name, cents in report.categories:
            w.writerow(["Category", name, format_money(cents, cur)])
        w.writerow([])
        for name, required, funded in report.goals:
            w.writerow(["Goal", f"{name} (needs/mo)", format_money(required, cur)])
            w.writerow(["Goal", f"{name} (funded/mo)", format_money(funded, cur)])
        w.writerow(["Goals", "Leftover after goals",
                    format_money(report.leftover_after_goals_cents, cur)])
        w.writerow([])
        w.writerow(["Investing", "Monthly amount",
                    format_money(report.monthly_invest_cents, cur)])
        for tier in ("high", "med", "low"):
            w.writerow([
                "Investing", f"{tier} risk ({report.risk_split.get(tier, 0)}%)",
                format_money(report.risk_amounts.get(tier, 0), cur),
            ])
        w.writerow([])
        w.writerow(["Disclaimer", EXPORT_DISCLAIMER])


def export_pdf(path: Path | str, report: Report) -> None:
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError(
            "PDF export requires reportlab (pip install reportlab)."
        ) from exc

    cur = report.currency
    c = canvas.Canvas(str(path), pagesize=letter)
    width, height = letter
    y = height - 60

    def line(text: str, dy: int = 16, font: str = "Helvetica", size: int = 11) -> None:
        nonlocal y
        if y < 60:
            c.showPage()
            y = height - 60
        c.setFont(font, size)
        c.drawString(60, y, text)
        y -= dy

    def money_row(label: str, cents: int) -> None:
        nonlocal y
        if y < 60:
            c.showPage()
            y = height - 60
        c.setFont("Helvetica", 11)
        c.drawString(72, y, label)
        c.drawRightString(width - 60, y, format_money(cents, cur))
        y -= 16

    line("BankBot — Budget Summary", 22, "Helvetica-Bold", 16)
    line(report.period_label, 22, "Helvetica", 12)

    line("Totals", 18, "Helvetica-Bold", 12)
    money_row("Income", report.income_cents)
    money_row("Essential spending", report.essential_cents)
    money_row("Wants", report.want_cents)
    money_row("Leftover", report.leftover_cents)
    y -= 6

    if report.categories:
        line("Spending by category", 18, "Helvetica-Bold", 12)
        for name, cents in report.categories:
            money_row(name, cents)
        y -= 6

    if report.goals:
        line("Goals (monthly contribution)", 18, "Helvetica-Bold", 12)
        for name, required, funded in report.goals:
            money_row(f"{name} — needed", required)
            money_row(f"{name} — funded", funded)
        money_row("Leftover after goals", report.leftover_after_goals_cents)
        y -= 6

    line("Investing", 18, "Helvetica-Bold", 12)
    money_row("Monthly amount", report.monthly_invest_cents)
    for tier in ("high", "med", "low"):
        money_row(f"{tier} risk ({report.risk_split.get(tier, 0)}%)",
                  report.risk_amounts.get(tier, 0))
    y -= 10

    # Wrapped disclaimer.
    c.setFont("Helvetica-Oblique", 8)
    words = EXPORT_DISCLAIMER.split()
    row = ""
    for word in words:
        if len(row) + len(word) > 95:
            c.drawString(60, y, row)
            y -= 11
            row = word
        else:
            row = f"{row} {word}".strip()
    if row:
        c.drawString(60, y, row)
    c.save()


def default_filename(report: Report, ext: str) -> str:
    return f"BankBot-{report.year}-{report.month:02d}.{ext}"
