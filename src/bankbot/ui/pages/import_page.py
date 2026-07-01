"""Statement import page: drag-drop / browse, background parse, result summary."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...core import repository as repo
from ..widgets.drop_area import DropArea
from ..workers import run_import

_FILTER = "Statements (*.pdf *.png *.jpg *.jpeg *.bmp *.tif *.tiff)"


class ImportPage(QWidget):
    dataChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._paths: list[str] = []
        self._busy = False
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<h2>Import bank statements</h2>"))
        layout.addWidget(QLabel(
            "Your files are read locally and never uploaded. PDF and PNG are supported, "
            "including multiple files from multiple banks."
        ))

        self._drop = DropArea()
        self._drop.filesDropped.connect(self._add_paths)
        layout.addWidget(self._drop)

        buttons = QHBoxLayout()
        self._browse = QPushButton("Browse…")
        self._browse.clicked.connect(self._browse_files)
        self._import = QPushButton("Import")
        self._import.setDefault(True)
        self._import.setEnabled(False)
        self._import.clicked.connect(self._start_import)
        self._clear = QPushButton("Clear list")
        self._clear.clicked.connect(self._clear_list)
        buttons.addWidget(self._browse)
        buttons.addStretch(1)
        buttons.addWidget(self._clear)
        buttons.addWidget(self._import)
        layout.addLayout(buttons)

        self._file_list = QListWidget()
        layout.addWidget(self._file_list, 1)

        self._progress = QProgressBar()
        self._progress.setVisible(False)
        layout.addWidget(self._progress)

        self._status = QLabel("")
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

    # --- file selection -------------------------------------------------------
    def _browse_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, "Select statements", "", _FILTER)
        if paths:
            self._add_paths(paths)

    def _add_paths(self, paths: list[str]) -> None:
        for p in paths:
            if p not in self._paths:
                self._paths.append(p)
                self._file_list.addItem(p)
        self._import.setEnabled(bool(self._paths) and not self._busy)

    def _clear_list(self) -> None:
        self._paths.clear()
        self._file_list.clear()
        self._import.setEnabled(False)
        self._status.setText("")

    # --- import ---------------------------------------------------------------
    def _start_import(self) -> None:
        if self._busy or not self._paths:
            return
        self._busy = True
        self._set_controls_enabled(False)
        self._progress.setVisible(True)
        self._progress.setRange(0, len(self._paths))
        self._progress.setValue(0)
        self._status.setText("Reading statements…")
        currency = repo.get_setting("currency", "CAD") or "CAD"
        run_import(
            list(self._paths), currency,
            on_progress=self._on_progress,
            on_finished=self._on_finished,
            on_failed=self._on_failed,
        )

    def _on_progress(self, done: int, total: int, message: str) -> None:
        self._progress.setMaximum(total)
        self._progress.setValue(done)
        self._status.setText(message)

    def _on_finished(self, report) -> None:
        self._busy = False
        self._progress.setVisible(False)
        parts = [
            f"Imported {report.total_added} new transaction(s).",
            f"{report.total_duplicates} duplicate(s) skipped." if report.total_duplicates else "",
        ]
        if report.errors:
            parts.append("Some files could not be read:")
            for f in report.errors:
                parts.append(f"  • {f.filename}: {f.error}")
        self._status.setText("\n".join(p for p in parts if p))
        self._clear_list()
        self._set_controls_enabled(True)
        self.dataChanged.emit()

    def _on_failed(self, message: str) -> None:
        self._busy = False
        self._progress.setVisible(False)
        self._status.setText(f"Import failed: {message}")
        self._set_controls_enabled(True)

    def _set_controls_enabled(self, enabled: bool) -> None:
        self._browse.setEnabled(enabled)
        self._clear.setEnabled(enabled)
        self._import.setEnabled(enabled and bool(self._paths))

    def refresh(self) -> None:  # symmetry with other pages
        pass
