"""TFSA/FHSA account-optimization suggestions."""
from __future__ import annotations

from bankbot.core.accounts import suggest_accounts

# Monthly room at 2026 limits: TFSA 7000/12 = 583, FHSA 8000/12 = 666 (floor).
TFSA_MONTHLY = 7000 * 100 // 12
FHSA_MONTHLY = 8000 * 100 // 12


def test_fhsa_first_when_saving_for_home():
    s = suggest_accounts(50000, 7000, 8000, saving_for_home=True)
    assert s[0].account == "FHSA"
    assert s[0].monthly_cents == min(50000, FHSA_MONTHLY)


def test_tfsa_first_when_not_saving_for_home():
    s = suggest_accounts(50000, 7000, 8000, saving_for_home=False)
    assert s[0].account == "TFSA"


def test_overflow_goes_to_taxable():
    big = (7000 + 8000) * 100  # more than both annual limits combined (monthly basis)
    s = suggest_accounts(big, 7000, 8000)
    assert s[-1].account == "Taxable / other"
    # Suggestions never allocate more than the input.
    assert sum(x.monthly_cents for x in s) == big


def test_amounts_never_exceed_room():
    s = suggest_accounts(100000, 7000, 8000, saving_for_home=True)
    total = sum(x.monthly_cents for x in s)
    assert total == 100000
    fhsa = next(x for x in s if x.account == "FHSA")
    assert fhsa.monthly_cents <= FHSA_MONTHLY


def test_zero_investment_no_suggestions():
    assert suggest_accounts(0, 7000, 8000) == []
