"""OCR fallback for scanned PDFs and PNG statements (pytesseract + pdf2image).

Tesseract and poppler are bundled into the packaged .exe. Path resolution order:
  1. ``BANKBOT_TESSERACT`` / ``BANKBOT_POPPLER`` env overrides
  2. bundled binaries next to a frozen executable (PyInstaller ``sys._MEIPASS``)
  3. system PATH (developer machines)
All calls are guarded so a missing dependency yields a clear message, never a crash.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from .pdf_text import ParsingDependencyError


def _bundle_dir() -> Path | None:
    base = getattr(sys, "_MEIPASS", None)
    return Path(base) if base else None


def _resolve_tesseract() -> str | None:
    override = os.environ.get("BANKBOT_TESSERACT")
    if override and Path(override).exists():
        return override
    bundle = _bundle_dir()
    if bundle:
        for name in ("tesseract.exe", "tesseract"):
            cand = bundle / "tesseract" / name
            if cand.exists():
                return str(cand)
    return None  # fall back to PATH


def _poppler_path() -> str | None:
    override = os.environ.get("BANKBOT_POPPLER")
    if override and Path(override).exists():
        return override
    bundle = _bundle_dir()
    if bundle and (bundle / "poppler" / "bin").exists():
        return str(bundle / "poppler" / "bin")
    return None  # fall back to PATH


def _configure_tesseract() -> "object":
    try:
        import pytesseract
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise ParsingDependencyError(
            "pytesseract is required for OCR (pip install pytesseract) and Tesseract "
            "must be installed or bundled."
        ) from exc
    resolved = _resolve_tesseract()
    if resolved:
        pytesseract.pytesseract.tesseract_cmd = resolved
    return pytesseract


def ocr_image(path: Path | str) -> str:
    """OCR a PNG/JPG statement image to text."""
    try:
        from PIL import Image
    except ImportError as exc:  # pragma: no cover
        raise ParsingDependencyError("Pillow is required to read PNG statements.") from exc
    pytesseract = _configure_tesseract()
    with Image.open(str(path)) as img:
        return pytesseract.image_to_string(img)


def ocr_pdf(path: Path | str) -> str:
    """Rasterize a scanned PDF and OCR each page."""
    try:
        from pdf2image import convert_from_path
    except ImportError as exc:  # pragma: no cover
        raise ParsingDependencyError(
            "pdf2image + poppler are required to OCR scanned PDFs."
        ) from exc
    pytesseract = _configure_tesseract()
    kwargs = {"dpi": 300}
    poppler = _poppler_path()
    if poppler:
        kwargs["poppler_path"] = poppler
    pages = convert_from_path(str(path), **kwargs)
    return "\n".join(pytesseract.image_to_string(page) for page in pages)
