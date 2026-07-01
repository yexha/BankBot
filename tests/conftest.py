"""Shared pytest fixtures. A fresh temp SQLite DB is created per test that needs it."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from bankbot.core import db


@pytest.fixture()
def database(tmp_path, monkeypatch):
    """Initialize a clean, seeded database in a temp dir."""
    monkeypatch.setenv("BANKBOT_DATA_DIR", str(tmp_path))
    db.init_engine(tmp_path / "test.db")
    yield db
    db._engine = None
    db._Session = None


def make_txn(**kwargs):
    """A lightweight transaction-like object for pure-logic tests."""
    defaults = dict(
        normalized_desc="",
        description="",
        direction="debit",
        amount_cents=0,
        currency="CAD",
        essential_want=None,
        is_income=False,
        review_status="auto",
        category=None,
    )
    defaults.update(kwargs)
    if not defaults["normalized_desc"] and defaults["description"]:
        defaults["normalized_desc"] = defaults["description"].upper()
    return SimpleNamespace(**defaults)
