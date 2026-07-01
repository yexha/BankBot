"""Light/dark theming via Qt stylesheets loaded from assets/styles."""
from __future__ import annotations

from pathlib import Path

from ..core import repository as repo

_STYLES_DIR = Path(__file__).resolve().parents[3] / "assets" / "styles"


def _load(name: str) -> str:
    path = _STYLES_DIR / f"{name}.qss"
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def apply_theme(app, theme: str | None = None) -> None:
    """Apply the given theme (or the saved setting) to the application."""
    theme = theme or repo.get_setting("theme", "light") or "light"
    if theme not in ("light", "dark"):
        theme = "light"
    app.setStyleSheet(_load(theme))


def toggle_theme(app) -> str:
    """Flip light/dark, persist it, and re-apply. Returns the new theme name."""
    current = repo.get_setting("theme", "light") or "light"
    new = "dark" if current == "light" else "light"
    repo.set_setting("theme", new)
    apply_theme(app, new)
    return new
