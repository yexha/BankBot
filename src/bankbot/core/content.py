"""Static, transparent allocation models and plain-language reasoning.

This is a general framework similar to what robo-advisors use for diversification.
It is NOT a prediction of returns and NOT a stock pick. No API calls.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Fund:
    ticker: str
    name: str


@dataclass(frozen=True)
class RiskTier:
    key: str
    label: str
    examples_cad: str
    examples_usd: str
    why: str
    funds_cad: tuple[Fund, ...] = ()
    funds_usd: tuple[Fund, ...] = ()

    def funds(self, currency: str) -> tuple[Fund, ...]:
        return self.funds_cad if currency.upper() == "CAD" else self.funds_usd


RISK_TIERS: dict[str, RiskTier] = {
    "low": RiskTier(
        key="low",
        label="Low risk",
        examples_cad="Broad bond ETFs (e.g. aggregate-bond index), GICs, high-interest savings",
        examples_usd="Broad bond ETFs (e.g. total-bond index), CDs, high-yield savings",
        why=(
            "Capital stability matters most here. Bonds, GICs/CDs and savings have low "
            "price volatility and predictable interest, so they cushion the portfolio and "
            "suit short time horizons or money you can't afford to see drop. The trade-off "
            "is lower expected long-run growth."
        ),
        funds_cad=(
            Fund("VAB", "Vanguard Canadian Aggregate Bond Index ETF"),
            Fund("ZAG", "BMO Aggregate Bond Index ETF"),
            Fund("CASH", "High-interest savings ETF"),
        ),
        funds_usd=(
            Fund("BND", "Vanguard Total Bond Market ETF"),
            Fund("AGG", "iShares Core U.S. Aggregate Bond ETF"),
            Fund("SGOV", "iShares 0-3 Month Treasury Bond ETF"),
        ),
    ),
    "med": RiskTier(
        key="med",
        label="Medium risk",
        examples_cad="Diversified balanced index ETFs (e.g. 60/40 asset-allocation ETF)",
        examples_usd="Diversified balanced index ETFs (e.g. 60/40 target-allocation fund)",
        why=(
            "A single balanced index fund spreads money across thousands of stocks and bonds "
            "worldwide. Diversification smooths out the ups and downs of any one company or "
            "country, aiming for steady medium-term growth with moderate volatility — a "
            "middle ground for multi-year horizons."
        ),
        funds_cad=(
            Fund("VBAL", "Vanguard Balanced ETF Portfolio (60/40)"),
            Fund("XBAL", "iShares Core Balanced ETF Portfolio (60/40)"),
        ),
        funds_usd=(
            Fund("AOR", "iShares Core Growth Allocation ETF (60/40)"),
            Fund("AOM", "iShares Core Moderate Allocation ETF (40/60)"),
        ),
    ),
    "high": RiskTier(
        key="high",
        label="High risk",
        examples_cad="Equity-heavy growth / broad-market equity ETFs",
        examples_usd="Equity-heavy growth / broad-market equity ETFs",
        why=(
            "Holding mostly stocks has historically offered the highest long-run growth, but "
            "with the largest short-term swings. It fits long time horizons (you won't need "
            "the money for many years) where there is time to ride out downturns. Still "
            "diversified across a broad index — not individual stock bets."
        ),
        funds_cad=(
            Fund("VEQT", "Vanguard All-Equity ETF Portfolio"),
            Fund("XEQT", "iShares Core All-Equity ETF Portfolio"),
            Fund("VGRO", "Vanguard Growth ETF Portfolio (80/20)"),
        ),
        funds_usd=(
            Fund("VTI", "Vanguard Total U.S. Stock Market ETF"),
            Fund("VT", "Vanguard Total World Stock ETF"),
        ),
    ),
}

FRAMEWORK_NOTE = (
    "These tiers map to broad, well-known diversification categories — a general "
    "framework similar to what robo-advisors use. They are examples for planning, not "
    "recommendations to buy specific securities, and not a guarantee of returns."
)
