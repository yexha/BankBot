"""Description normalization, shared by parsing and categorization."""
from __future__ import annotations

import re

_CARD_RE = re.compile(r"\b\d{4,}\b")        # long digit runs (card/ref numbers)
_REF_RE = re.compile(r"#?\s*ref(?:erence)?[:\s]*\S+", re.IGNORECASE)
_WS_RE = re.compile(r"\s+")


def normalize_description(raw: str) -> str:
    """Uppercase, strip reference/card numbers and extra whitespace for matching."""
    if not raw:
        return ""
    text = raw.upper()
    text = _REF_RE.sub(" ", text)
    text = _CARD_RE.sub(" ", text)
    text = text.replace("*", " ")
    text = _WS_RE.sub(" ", text)
    return text.strip()
