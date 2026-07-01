"""Canadian tax-advantaged account guidance (TFSA / FHSA).

General educational guidance only — not personalized tax advice. Limits are read
from editable settings (seeded with 2026 values) so they stay correct offline.
"""
from __future__ import annotations

from dataclasses import dataclass

from .money import to_cents


@dataclass
class AccountSuggestion:
    account: str
    monthly_cents: int
    note: str


def suggest_accounts(
    monthly_invest_cents: int,
    tfsa_annual_limit: float | str,
    fhsa_annual_limit: float | str,
    saving_for_home: bool = True,
) -> list[AccountSuggestion]:
    """Spread the monthly contribution across FHSA then TFSA up to annual room.

    When saving for a first home, FHSA is filled first (contributions are tax-
    deductible and withdrawals for a home are tax-free); otherwise TFSA leads.
    Anything above both annual limits is flagged as a taxable/other account.
    """
    monthly = max(0, int(monthly_invest_cents))
    tfsa_monthly_room = to_cents(tfsa_annual_limit) // 12
    fhsa_monthly_room = to_cents(fhsa_annual_limit) // 12

    order = (
        [("FHSA", fhsa_monthly_room), ("TFSA", tfsa_monthly_room)]
        if saving_for_home
        else [("TFSA", tfsa_monthly_room), ("FHSA", fhsa_monthly_room)]
    )

    suggestions: list[AccountSuggestion] = []
    remaining = monthly
    for name, room in order:
        amt = min(remaining, room)
        if amt > 0:
            note = {
                "FHSA": "tax-deductible contributions; tax-free for a first home",
                "TFSA": "tax-free growth and withdrawals, flexible for any goal",
            }[name]
            suggestions.append(AccountSuggestion(name, amt, note))
            remaining -= amt
    if remaining > 0:
        suggestions.append(
            AccountSuggestion(
                "Taxable / other",
                remaining,
                "above this year's registered room — consider an RRSP or non-registered account",
            )
        )
    return suggestions


DISCLAIMER = (
    "General educational information based on current account rules — not personalized "
    "financial or tax advice. Verify current contribution limits and your own room."
)
