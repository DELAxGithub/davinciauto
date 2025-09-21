from __future__ import annotations

"""
Canonical project folder structure and naming helpers for DaVinci Resolve bin mirroring.

Project root layout (example: OrionEp1):
  OrionEp1/
    テロップ類/
      SRT/
      CSV/
    サウンド類/
      Narration/
      BGM/
      SE/
    映像類/
      Stock/
      Recordings/
      CG/
    inputs/

These physical folders map directly to Resolve bins on import.
"""

from pathlib import Path


# Top-level categories (Japanese labels)
C_TELOP = "テロップ類"
C_SOUND = "サウンド類"
C_VIDEO = "映像類"


# Subfolders
TELOP_SRT = f"{C_TELOP}/SRT"
TELOP_CSV = f"{C_TELOP}/CSV"

SOUND_NARR = f"{C_SOUND}/Narration"
SOUND_BGM = f"{C_SOUND}/BGM"
SOUND_SE = f"{C_SOUND}/SE"

VIDEO_STOCK = f"{C_VIDEO}/Stock"
VIDEO_REC = f"{C_VIDEO}/Recordings"
VIDEO_CG = f"{C_VIDEO}/CG"


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def telop_srt_file(project_dir: Path, project_name: str, source: str = "follow") -> Path:
    return project_dir / TELOP_SRT / f"{project_name}_Sub_{source}.srt"


def telop_csv_file(project_dir: Path, project_name: str, variant: str = "vertical") -> Path:
    return project_dir / TELOP_CSV / f"{project_name}_TEL_{variant}.csv"


def narration_dir(project_dir: Path) -> Path:
    return project_dir / SOUND_NARR


def bgm_dir(project_dir: Path) -> Path:
    return project_dir / SOUND_BGM


def se_dir(project_dir: Path) -> Path:
    return project_dir / SOUND_SE

