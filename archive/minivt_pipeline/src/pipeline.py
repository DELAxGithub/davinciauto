"""Backward-compatible CLI wrapper for the legacy pipeline entry point."""

from davinciauto_core.cli import main

if __name__ == "__main__":  # pragma: no cover - legacy CLI entry
    raise SystemExit(main())
