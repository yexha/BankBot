"""Currency conversion via a stored rate."""
from __future__ import annotations

from bankbot.core.fx import convert


def test_same_currency_unchanged():
    assert convert(10000, "CAD", "CAD", 1.35) == 10000


def test_usd_to_cad():
    assert convert(10000, "USD", "CAD", 1.35) == 13500


def test_cad_to_usd():
    assert convert(13500, "CAD", "USD", 1.35) == 10000


def test_invalid_rate_returns_unchanged():
    assert convert(10000, "USD", "CAD", 0) == 10000


def test_unknown_pair_unchanged():
    assert convert(10000, "EUR", "CAD", 1.35) == 10000
