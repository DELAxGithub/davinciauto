#!/usr/bin/env python3
from __future__ import annotations

"""
Archive phase script: move files/folders into experiments/archive/ while
recording a manifest for safe restoration.

Default mode uses usage_audit (unused candidates). You can switch to --mode all
to archive everything except a whitelist of core folders.

Usage:
  python scripts/archive_phase.py --dry-run                 # show plan
  python scripts/archive_phase.py --mode candidates         # archive unused candidates
  python scripts/archive_phase.py --mode all                # archive everything (except whitelist)

Restore:
  python scripts/restore_from_archive.py --list             # show manifest
  python scripts/restore_from_archive.py --paths path1 path2
  python scripts/restore_from_archive.py --all
"""

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Set

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_ROOT = ROOT / "experiments" / "archive"
MANIFEST = ROOT / "experiments" / "archive_manifest.json"

# Keep list: never archive these (top-level entries)
WHITELIST = {
    ".git", ".github", ".vscode", ".venv", "__pycache__",
    "backend", "gui_steps", "minivt_pipeline", "core", "docs", "config",
    "scripts", "projects", "prompts", "experiments", "output", "thumbnails", "yaml",
    "LICENSE", "README.md", "PROJECT_INDEX.md", "CLAUDE.md", ".rgignore", ".gitignore", ".env"
}


def run_usage_audit() -> Set[Path]:
    """Return set of candidate file paths to archive (unused python modules)."""
    cmd = ["python", str(ROOT / "scripts" / "usage_audit.py"), "--format", "markdown"]
    try:
        out = subprocess.check_output(cmd, cwd=str(ROOT), text=True)
    except Exception:
        return set()
    # Parse under '## Unused Python Modules (candidate)'
    lines = out.splitlines()
    unused: Set[Path] = set()
    in_unused = False
    for ln in lines:
        if ln.strip().startswith("## Unused Python Modules"):
            in_unused = True
            continue
        if ln.strip().startswith("## ") and in_unused:
            break
        if in_unused and ln.strip().startswith("- `") and ln.strip().endswith("`"):
            rel = ln.strip()[3:-1]
            p = ROOT / rel
            if p.suffix == ".py":
                unused.add(p)
    return unused


def gather_all_targets() -> List[Path]:
    targets: List[Path] = []
    for p in ROOT.iterdir():
        if p.name in WHITELIST:
            continue
        targets.append(p)
    return targets


def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def move_path(src: Path, dst: Path, dry: bool) -> None:
    ensure_dir(dst.parent)
    if dry:
        return
    # Prefer git mv if available
    try:
        subprocess.check_call(["git", "mv", "-f", str(src), str(dst)])
    except Exception:
        if src.is_dir():
            shutil.move(str(src), str(dst))
        else:
            ensure_dir(dst.parent)
            shutil.move(str(src), str(dst))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["candidates", "all"], default="candidates")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    ensure_dir(ARCHIVE_ROOT)

    moves: Dict[str, str] = {}
    if args.mode == "candidates":
        cands = run_usage_audit()
        for p in sorted(cands):
            rel = p.relative_to(ROOT)
            dst = ARCHIVE_ROOT / rel
            print(f"ARCHIVE cand: {rel} -> {dst.relative_to(ROOT)}")
            move_path(p, dst, args.dry_run)
            moves[str(rel)] = str(dst.relative_to(ROOT))
    else:
        for p in gather_all_targets():
            rel = p.relative_to(ROOT)
            dst = ARCHIVE_ROOT / rel
            print(f"ARCHIVE all: {rel} -> {dst.relative_to(ROOT)}")
            move_path(p, dst, args.dry_run)
            moves[str(rel)] = str(dst.relative_to(ROOT))

    manifest = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "mode": args.mode,
        "dry_run": args.dry_run,
        "moves": moves,
    }
    if not args.dry_run:
        ensure_dir(MANIFEST.parent)
        MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Manifest written: {MANIFEST}")
    else:
        print("Dry-run: manifest not written.")


if __name__ == "__main__":
    main()

