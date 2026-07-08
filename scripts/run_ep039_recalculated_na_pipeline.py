#!/usr/bin/env python3
"""Convenience runner for the EP039 recalculated-NA Resolve pipeline."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESOLVE_CLI = Path("/Users/delaxpro/src/claude-config/skills/davinci-resolve/scripts/resolve_cli.py")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the EP039 recalculated-NA DaVinci pipeline.")
    parser.add_argument("--apply", action="store_true", help="Create the Resolve timeline. Without this, dry-run only.")
    parser.add_argument("--output-timeline", default="039編集_0619_NA込み再計算")
    parser.add_argument("--source-timeline", default="039編集_0619")
    parser.add_argument("--reference-timeline", default="039編集_0619 自動カット済み")
    parser.add_argument("--ir-json", type=Path, default=REPO_ROOT / "output/ep039_auto_cut_2/desired_timeline_ir_24fps.json")
    parser.add_argument("--na-dir", type=Path, default=REPO_ROOT / "output/ep039_auto_cut_2/na_wav")
    parser.add_argument("--out-dir", type=Path, default=REPO_ROOT / "output/ep039_recalculated_na")
    parser.add_argument("--resolve-cli", type=Path, default=DEFAULT_RESOLVE_CLI)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    script = REPO_ROOT / "scripts/apply_ep039_recalculated_na_timeline.py"
    args.out_dir.mkdir(parents=True, exist_ok=True)

    globals_json = {
        "SOURCE_TIMELINE": args.source_timeline,
        "REFERENCE_TIMELINE": args.reference_timeline,
        "OUTPUT_TIMELINE": args.output_timeline,
        "IR_JSON": str(args.ir_json),
        "NA_DIR": str(args.na_dir),
        "APPLY": bool(args.apply),
    }
    if args.apply:
        globals_json.update(
            {
                "REPORT_JSON": str(args.out_dir / "apply_report.json"),
                "MAPPING_CSV": str(args.out_dir / "tc_mapping.csv"),
            }
        )

    cmd = [
        sys.executable,
        str(args.resolve_cli),
        "run-script",
        "--script",
        str(script),
        "--globals-json",
        json.dumps(globals_json, ensure_ascii=False),
        "--apply",
    ]
    return subprocess.run(cmd, cwd=REPO_ROOT).returncode


if __name__ == "__main__":
    raise SystemExit(main())
