"""Console entry points for the DaVinci Auto pipeline."""

__all__ = ["__version__"]

try:  # pragma: no cover - defensive fallback
    from importlib.metadata import version

    __version__ = version("davinciauto-core")
except Exception:  # pragma: no cover - during editable installs
    __version__ = "0.0.0"
