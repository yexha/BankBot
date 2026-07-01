"""Text-based PDF extraction via pdfplumber (lazy import)."""
from __future__ import annotations

from pathlib import Path


class ParsingDependencyError(RuntimeError):
    """Raised when an optional parsing dependency is not installed."""


def extract_text(path: Path | str) -> str:
    """Extract text from a text-based PDF. Returns '' if there is no text layer."""
    try:
        import pdfplumber
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise ParsingDependencyError(
            "pdfplumber is required to read PDF statements (pip install pdfplumber)."
        ) from exc

    chunks: list[str] = []
    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            if text.strip():
                chunks.append(text)
    return "\n".join(chunks)


def has_text_layer(text: str) -> bool:
    """Heuristic: enough extracted text to attempt a text parse."""
    return len(text.strip()) >= 40
