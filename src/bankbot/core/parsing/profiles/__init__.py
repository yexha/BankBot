"""Bank profile registry.

Each profile detects its bank by header keywords and parses transactions. Without
real sample statements the profiles currently reuse the robust generic line parser
and mainly record the source bank; per-bank layout overrides can be added as
sample formats become available. The generic fallback guarantees unknown banks
still parse.
"""
from __future__ import annotations

from ..base import BankProfile


class GenericProfile(BankProfile):
    name = "generic"
    display = "Generic / Unknown bank"


class RBCProfile(BankProfile):
    name = "rbc"
    display = "RBC Royal Bank"
    keywords = ("RBC", "ROYAL BANK", "RBC ROYAL BANK")


class TDProfile(BankProfile):
    name = "td"
    display = "TD Canada Trust"
    keywords = ("TD CANADA TRUST", "TD BANK", "TORONTO-DOMINION")


class ScotiaProfile(BankProfile):
    name = "scotia"
    display = "Scotiabank"
    keywords = ("SCOTIABANK", "BANK OF NOVA SCOTIA", "SCOTIA")


class CIBCProfile(BankProfile):
    name = "cibc"
    display = "CIBC"
    keywords = ("CIBC", "CANADIAN IMPERIAL BANK")


class BMOProfile(BankProfile):
    name = "bmo"
    display = "BMO Bank of Montreal"
    keywords = ("BMO", "BANK OF MONTREAL")


class TangerineProfile(BankProfile):
    name = "tangerine"
    display = "Tangerine"
    keywords = ("TANGERINE",)


class WealthsimpleProfile(BankProfile):
    name = "wealthsimple"
    display = "Wealthsimple"
    keywords = ("WEALTHSIMPLE", "WEALTHSIMPLE CASH")


# Order matters only for detection; generic is the fallback (checked last).
_SPECIFIC: list[BankProfile] = [
    RBCProfile(), TDProfile(), ScotiaProfile(), CIBCProfile(),
    BMOProfile(), TangerineProfile(), WealthsimpleProfile(),
]
GENERIC = GenericProfile()


def choose_profile(text: str) -> BankProfile:
    """Return the first bank profile that matches the text, else the generic one."""
    for profile in _SPECIFIC:
        try:
            if profile.detect(text):
                return profile
        except Exception:
            continue
    return GENERIC


def all_profiles() -> list[BankProfile]:
    return [*_SPECIFIC, GENERIC]
