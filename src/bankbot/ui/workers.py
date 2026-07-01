"""Background workers so PDF/OCR parsing never blocks the UI thread."""
from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot

from ..core.import_service import ImportReport, import_files


class _ImportSignals(QObject):
    progress = Signal(int, int, str)      # done, total, message
    finished = Signal(object)             # ImportReport
    failed = Signal(str)


class ImportWorker(QRunnable):
    """Runs the import pipeline off the UI thread via QThreadPool."""

    def __init__(self, paths: Sequence[str], currency: str):
        super().__init__()
        self._paths = list(paths)
        self._currency = currency
        self.signals = _ImportSignals()

    @Slot()
    def run(self) -> None:
        try:
            report: ImportReport = import_files(
                self._paths,
                currency=self._currency,
                progress=lambda d, t, m: self.signals.progress.emit(d, t, m),
            )
            self.signals.finished.emit(report)
        except Exception as exc:  # noqa: BLE001 - surface, never crash the app
            self.signals.failed.emit(str(exc))


def run_import(paths: Sequence[str], currency: str, on_progress, on_finished, on_failed):
    """Convenience: wire signals and start an import on the global thread pool."""
    worker = ImportWorker(paths, currency)
    worker.signals.progress.connect(on_progress)
    worker.signals.finished.connect(on_finished)
    worker.signals.failed.connect(on_failed)
    QThreadPool.globalInstance().start(worker)
    return worker
