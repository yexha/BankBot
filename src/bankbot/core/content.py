"""Static, transparent allocation models and plain-language reasoning.

This is a general framework similar to what robo-advisors use for diversification.
It is NOT a prediction of returns and NOT a stock pick. No API calls.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RiskTier:
    key: str
    label: str
    examples_cad: str
    examples_usd: str
    why: str


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
    ),
    "high": RiskTier(
        key="high",
        label="High risk",
        examples_cad="Equity-heavy growth / broad-market or sector equity ETFs",
        examples_usd="Equity-heavy growth / broad-market or sector equity ETFs",
        why=(
            "Holding mostly stocks has historically offered the highest long-run growth, but "
            "with the largest short-term swings. It fits long time horizons (you won't need "
            "the money for many years) where there is time to ride out downturns. Still "
            "diversified across a broad index — not individual stock bets."
        ),
    ),
}

FRAMEWORK_NOTE = (
    "These tiers map to broad, well-known diversification categories — a general "
    "framework similar to what robo-advisors use. They are examples for planning, not "
    "recommendations to buy specific securities, and not a guarantee of returns."
)
