"""Import orchestration: file -> text (with OCR fallback) -> ParsedTxn list.

Every failure mode is captured into ``ExtractResult.error`` with a user-facing
message so the UI can show it and let the user skip the file — the pipeline never
raises out to the caller.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

from . import column_parser
from .base import ParsedTxn, detect_year
from .ocr import ocr_image, ocr_pdf
from .pdf_text import extract_text, extract_words_by_page, has_text_layer
from .profiles import choose_profile

_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}


@dataclass
class ExtractResult:
    path: str
    filename: str
    file_hash: str = ""
    bank_profile: str = "generic"
    used_ocr: bool = False
    transactions: list[ParsedTxn] = field(default_factory=list)
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


def file_sha256(path: Path | str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def _extract(path: Path, year_hint_text: str = "") -> tuple[str, list[list[dict]], bool]:
    """Return (text, word_pages, used_ocr).

    ``word_pages`` carries per-word coordinates for the column parser and is empty
    for OCR/image sources (no reliable coordinates there).
    """
    ext = path.suffix.lower()
    if ext in _IMAGE_EXTS:
        return ocr_image(path), [], True
    if ext == ".pdf":
        text = extract_text(path)
        if has_text_layer(text):
            return text, extract_words_by_page(path), False
        return ocr_pdf(path), [], True  # scanned PDF fallback
    raise ValueError(f"Unsupported file type: {ext or 'unknown'}")


def extract_file(path: Path | str, currency: str = "CAD") -> ExtractResult:
    """Parse a single statement file, capturing any error into the result."""
    p = Path(path)
    result = ExtractResult(path=str(p), filename=p.name)
    if not p.exists():
        result.error = "File not found."
        return result
    try:
        result.file_hash = file_sha256(p)
        text, word_pages, used_ocr = _extract(p)
        result.used_ocr = used_ocr
        if not text.strip():
            result.error = "No readable text found (the file may be blank or corrupted)."
            return result
        profile = choose_profile(text)
        result.bank_profile = profile.name
        year = detect_year(text)

        # Prefer the column-aware parser (correctly separates deposits from
        # withdrawals); fall back to the generic line parser if there are no
        # column headers or no word coordinates (e.g. OCR).
        txns = column_parser.parse_pages(word_pages, year) if word_pages else []
        if not txns:
            txns = profile.parse(text, year)

        for t in txns:
            t.currency = currency
            if not t.dedupe_hash:
                t.finalize()
        result.transactions = txns
        if not txns:
            result.error = (
                "Couldn't find any transactions in this file. It may be an unsupported "
                "layout — you can skip it."
            )
    except Exception as exc:  # noqa: BLE001 - deliberately broad; report, never crash
        result.error = f"Could not read this file: {exc}"
    return result
