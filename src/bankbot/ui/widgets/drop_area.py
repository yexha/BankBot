"""Drag-and-drop zone for statement files (PDF/PNG)."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QLabel

_SUPPORTED = (".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff")


class DropArea(QLabel):
    filesDropped = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("dropArea")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setWordWrap(True)
        self.setMinimumHeight(140)
        self.setText(
            "Drag & drop PDF or PNG bank statements here\n(or use the Browse button below)"
        )
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setProperty("hover", True)
            self._restyle()
        else:
            event.ignore()

    def dragLeaveEvent(self, event) -> None:
        self.setProperty("hover", False)
        self._restyle()

    def dropEvent(self, event: QDropEvent) -> None:
        self.setProperty("hover", False)
        self._restyle()
        paths = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith(_SUPPORTED):
                paths.append(path)
        if paths:
            self.filesDropped.emit(paths)
            event.acceptProposedAction()

    def _restyle(self) -> None:
        # Force a style refresh so the [hover="true"] QSS rule applies.
        self.style().unpolish(self)
        self.style().polish(self)
