from __future__ import annotations

from PySide6.QtGui import QColor, QTextCursor
from PySide6.QtWidgets import QPlainTextEdit


class LogViewer(QPlainTextEdit):
    MAX_LINES = 5000

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setLineWrapMode(QPlainTextEdit.NoWrap)

    def append_event(self, event: dict) -> None:
        level = str(event.get("level", "info")).upper()
        code = event.get("code") or event.get("type") or ""
        message = event.get("message") or event.get("msg") or ""
        if not message:
            parts = []
            for key in (
                "stage",
                "mode",
                "items",
                "segments",
                "index",
                "total",
                "output_root",
                "path",
                "reason",
                "suggested_concurrency",
            ):
                value = event.get(key)
                if value not in (None, ""):
                    parts.append(f"{key}={value}")
            if progress := event.get("progress"):
                parts.append(f"progress={progress}")
            if not parts and (payload := event.get("payload")):
                parts.append(f"payload={payload}")
            message = ", ".join(str(p) for p in parts)

        line = f"[{level:>7}] {code}"
        if message:
            line += f": {message}"
        self.appendPlainText(line)
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.setTextCursor(cursor)
        self._trim_lines()

    def append_text(self, text: str) -> None:
        self.appendPlainText(text)
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.setTextCursor(cursor)
        self._trim_lines()

    def _trim_lines(self) -> None:
        doc = self.document()
        if doc.blockCount() <= self.MAX_LINES:
            return
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        for _ in range(doc.blockCount() - self.MAX_LINES):
            cursor.select(QTextCursor.SelectionType.LineUnderCursor)
            cursor.removeSelectedText()
            cursor.deleteChar()
