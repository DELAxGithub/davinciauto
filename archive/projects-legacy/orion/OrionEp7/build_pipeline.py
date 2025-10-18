#!/usr/bin/env python3
"""Legacy wrapper kept for convenience; delegates to the shared Orion pipeline."""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
REPO_ROOT = PROJECT_DIR.parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.append(str(SCRIPTS_DIR))

from orion_pipeline import main as run_pipeline_cli


if __name__ == "__main__":
    run_pipeline_cli(["OrionEp7"])
