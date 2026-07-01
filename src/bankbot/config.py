"""Application paths and constants.

All financial data is stored locally only. On Windows the data dir is
``%APPDATA%/BankBot``; on other platforms a sensible per-user fallback is used so
the core logic and tests run anywhere. ``BANKBOT_DATA_DIR`` overrides the location
(used by tests to point at a temp dir).
"""
from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "BankBot"


def data_dir() -> Path:
    """Return the per-user data directory, creating it if needed."""
    override = os.environ.get("BANKBOT_DATA_DIR")
    if override:
        base = Path(override)
    elif os.name == "nt":  # Windows
        base = Path(os.environ.get("APPDATA", Path.home())) / APP_NAME
    elif "XDG_DATA_HOME" in os.environ:
        base = Path(os.environ["XDG_DATA_HOME"]) / APP_NAME
    else:
        base = Path.home() / ".local" / "share" / APP_NAME
    base.mkdir(parents=True, exist_ok=True)
    return base


def db_path() -> Path:
    """Path to the local SQLite database file."""
    return data_dir() / "bankbot.db"


# --- Defaults seeded into the settings table on first run ----------------------
DEFAULT_SETTINGS = {
    "currency": "CAD",
    "manual_fx_rate": "1.35",          # CAD per 1 USD; user-editable, no paid FX API
    "fx_rate_cached_at": "",
    "theme": "light",
    # Canadian tax-advantaged account limits — editable; verified 2026.
    "tfsa_limit": "7000",
    "fhsa_annual_limit": "8000",
    "fhsa_lifetime_limit": "40000",
    "limits_verified_on": "2026",
    # Investment allocation state.
    "monthly_invest_pct": "50",
    "risk_high_pct": "20",
    "risk_med_pct": "40",
    "risk_low_pct": "40",
    "schema_version": "1",
}

# Visible-everywhere disclaimer (hard requirement).
DISCLAIMER = (
    "BankBot provides general budgeting and allocation guidance based on your own "
    "data and general financial principles. It is not personalized financial, "
    "investment, or tax advice, and it cannot predict market performance. Consult a "
    "licensed financial advisor for investment decisions."
)
