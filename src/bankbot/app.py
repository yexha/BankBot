"""QApplication bootstrap. Keep heavy work out of here; pages own their logic."""
from __future__ import annotations

import sys


def main() -> int:
    # Imported lazily so `import bankbot` (and the core tests) never require Qt.
    from PySide6.QtWidgets import QApplication

    from .core import db
    from .ui.main_window import MainWindow
    from .ui.theme import apply_theme

    db.init_engine()  # create + seed the local database on first run

    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("BankBot")
    app.setOrganizationName("BankBot")

    apply_theme(app)

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
