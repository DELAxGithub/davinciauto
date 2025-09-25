from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from .config import ConfigManager
from .main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
