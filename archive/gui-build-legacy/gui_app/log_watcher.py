"""Incremental JSONL log reader running on a QThread."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, QThread, QTimer, Signal


class LogWatcher(QObject):
    line = Signal(dict)
    error = Signal(str)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._log_path: Optional[Path] = None
        self._offset = 0
        self._buffer = b""
        self._timer: Optional[QTimer] = None

    def start(self, log_path: Path, interval_ms: int = 150) -> None:
        self._log_path = log_path
        self._offset = 0
        self._buffer = b""
        if self._timer:
            self._timer.stop()
        self._timer = QTimer(self)
        self._timer.setInterval(interval_ms)
        self._timer.timeout.connect(self._poll)
        self._timer.start()

    def stop(self) -> None:
        if self._timer:
            self._timer.stop()
            self._timer.deleteLater()
            self._timer = None
        self._log_path = None
        self._offset = 0
        self._buffer = b""

    def _poll(self) -> None:
        if not self._log_path or not self._log_path.exists():
            return
        try:
            with self._log_path.open("rb") as handle:
                handle.seek(self._offset)
                chunk = handle.read()
        except Exception as exc:  # pragma: no cover
            self.error.emit(f"log read failed: {exc}")
            return
        if not chunk:
            return
        self._offset += len(chunk)
        self._buffer += chunk
        lines = self._buffer.split(b"\n")
        self._buffer = lines.pop()  # keep tail
        for raw in lines:
            raw = raw.strip()
            if not raw:
                continue
            try:
                payload = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                continue
            self.line.emit(payload)


class LogWatcherThread(QThread):
    def __init__(self, watcher: LogWatcher, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._watcher = watcher

    def run(self) -> None:  # pragma: no cover - event loop handled by QTimer
        self.exec()
