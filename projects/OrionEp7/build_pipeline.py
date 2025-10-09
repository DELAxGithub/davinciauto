#!/usr/bin/env python3
"""Convenience wrapper to run the shared TTS pipeline for Orion Ep7."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
REPO_ROOT = PROJECT_DIR.parents[2]

script = REPO_ROOT / "scripts/run_tts_pipeline.py"

cmd = [
    sys.executable,
    str(script),
    "--project",
    "OrionEp7",
    "--script-md",
    str(PROJECT_DIR / "inputs/orionep7.md"),
    "--script-csv",
    str(PROJECT_DIR / "inputs/orion_ep7_script.csv"),
    "--input-srt",
    str(PROJECT_DIR / "inputs/ep7.srt"),
    "--output-srt",
    str(PROJECT_DIR / "exports/ep7timecode.srt"),
    "--timeline-csv",
    str(PROJECT_DIR / "output/OrionEp7_timeline.csv"),
    "--timeline-xml",
    str(PROJECT_DIR / "output/OrionEp7_timeline.xml"),
    "--export-xml",
    str(PROJECT_DIR / "exports/timelines/OrionEp7_timeline.xml"),
    "--audio-dir",
    str(PROJECT_DIR / "output/audio"),
    "--sample-name",
    "OrionEp7",
    "--tts-config",
    str(PROJECT_DIR / "inputs/orionep7_tts.yaml"),
]

sys.exit(subprocess.call(cmd))
