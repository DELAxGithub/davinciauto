"""Utilities for resolving resource paths both in development and PyInstaller builds."""
from __future__ import annotations

import sys
from pathlib import Path


def resource_path(relative: str) -> Path:
    """Return absolute Path to a bundled resource.

    When running from PyInstaller (one-dir/one-file), files are extracted under
    ``sys._MEIPASS``. During development, fall back to the project root based on
    this file's location.
    """
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return (base / relative).resolve()


def default_cli_executable() -> Path:
    """Resolve the preferred CLI executable path.

    Priority order:
    1. Bundled CLI (Resources/bin/davinciauto_cli[.exe])
    2. Development environment: use current interpreter with ``-m davinciauto_core.cli``.
    """
    # 1) Bundled CLI
    for candidate in (
        resource_path("Resources/bin/davinciauto_cli"),
        resource_path("Resources/bin/davinciauto_cli.exe"),
        resource_path("MacOS/davinciauto_cli"),
    ):
        if candidate.exists():
            return candidate
    # 2) Development fallback (the caller should detect this sentinel)
    return Path(sys.executable)
