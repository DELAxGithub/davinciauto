#!/usr/bin/env python3
from __future__ import annotations

"""
Restore files from experiments/archive using the archive_manifest.json.

Usage:
  python scripts/restore_from_archive.py --list
  python scripts/restore_from_archive.py --paths path1 path2
  python scripts/restore_from_archive.py --all
"""

import argparse
import json
import shutil
from pathlib import Path
from typing import Dict

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_ROOT = ROOT / "experiments" / "archive"
MANIFEST = ROOT / "experiments" / "archive_manifest.json"


def load_manifest() -> Dict[str, str]:
    if not MANIFEST.exists():
        raise SystemExit("Manifest not found: experiments/archive_manifest.json")
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return data.get("moves", {})


def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def restore_path(rel: str) -> None:
    src = ARCHIVE_ROOT / rel
    dst = ROOT / rel
    if not src.exists():
        print(f"[skip] no archived source: {rel}")
        return
    ensure_dir(dst.parent)
    try:
        # Try git mv if available
        import subprocess
        subprocess.check_call(["git", "mv", "-f", str(src), str(dst)])
    except Exception:
        shutil.move(str(src), str(dst))
    print(f"restored: {rel}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--paths", nargs="*")
    args = ap.parse_args()

    moves = load_manifest()

    if args.list:
        print("Archived entries (relative paths):")
        for rel in sorted(moves.keys()):
            print(" ", rel)
        return

    if args.all:
        for rel in sorted(moves.keys()):
            restore_path(rel)
        return

    if args.paths:
        for rel in args.paths:
            restore_path(rel)
        return

    print("Specify --list, --all or --paths ...")


if __name__ == "__main__":
    main()

