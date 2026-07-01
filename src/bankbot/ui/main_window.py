"""Main window: sidebar navigation, stacked pages, and the always-visible
disclaimer banner (a hard requirement)."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..config import DISCLAIMER
from ..core import repository as repo
from .pages.goals_page import GoalsPage
from .pages.import_page import ImportPage
from .pages.invest_page import InvestPage
from .pages.review_page import ReviewPage
from .pages.settings_page import SettingsPage
from .pages.summary_page import SummaryPage

_NAV = ["Import", "Review", "Summary", "Goals", "Invest", "Settings"]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BankBot — Personal Finance & Allocation")
        self.resize(1024, 720)

        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        body = QHBoxLayout()
        root.addLayout(body, 1)

        self._nav = QListWidget()
        self._nav.setObjectName("navList")
        self._nav.setFixedWidth(180)
        for name in _NAV:
            self._nav.addItem(QListWidgetItem(name))
        self._nav.currentRowChanged.connect(self._on_nav)
        body.addWidget(self._nav)

        self._stack = QStackedWidget()
        self._import = ImportPage()
        self._review = ReviewPage()
        self._summary = SummaryPage()
        self._goals = GoalsPage()
        self._invest = InvestPage()
        self._settings = SettingsPage()
        self._pages = [
            self._import, self._review, self._summary,
            self._goals, self._invest, self._settings,
        ]
        for page in self._pages:
            self._stack.addWidget(page)
        body.addWidget(self._stack, 1)

        # Disclaimer banner — always visible.
        banner = QLabel(DISCLAIMER)
        banner.setObjectName("disclaimerBanner")
        banner.setWordWrap(True)
        root.addWidget(banner)

        self.setCentralWidget(central)

        # Data-change wiring: any mutation refreshes the derived pages.
        for page in (self._import, self._review, self._goals, self._settings):
            page.dataChanged.connect(self._on_data_changed)

        self._nav.setCurrentRow(0)
        self._update_review_badge()

    def _on_nav(self, row: int) -> None:
        if 0 <= row < len(self._pages):
            self._stack.setCurrentIndex(row)
            page = self._pages[row]
            if hasattr(page, "refresh"):
                page.refresh()

    def _on_data_changed(self) -> None:
        # Refresh everything derived so views never drift out of sync.
        for page in (self._review, self._summary, self._goals, self._invest):
            page.refresh()
        self._update_review_badge()

    def _update_review_badge(self) -> None:
        try:
            count = len(repo.review_queue())
        except Exception:
            count = 0
        label = "Review" if not count else f"Review ({count})"
        self._nav.item(_NAV.index("Review")).setText(label)
