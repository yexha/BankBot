"""Development entry point: ``python run.py``.

Adds ``src`` to the path and launches the PySide6 application. Kept tiny so the
real bootstrap lives in :mod:`bankbot.app`.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from bankbot.app import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
