#!/usr/bin/env python3
"""Extract Platto SEG color blocks from a script PDF/text file.

This is a pre-fine-cut planning step. It turns a color-coded script such as
`## SEG02 | #2 Rose | 00:03:01:10 -> 00:04:11:10 | 1:00` into a machine-readable
block plan that can be used to create/color a coarse Resolve timeline before
line-level filler cuts.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
from pathlib import Path
from typing import Any


COLOR_MAP = {
    "rose": "Pink",
    "mango": "Orange",
    "yellow": "Yellow",
    "lavender": "Violet",
    "caribbean": "Teal",
    "tan": "Tan",
    "forest": "Green",
    "blue": "Blue",
    "purple": "Purple",
    "teal": "Teal",
    "cerulean": "Blue",
    "violet": "Violet",
}


TIMECODE_RE = re.compile(r"\d{2}:\d{2}:\d{2}[:;]\d{2}")


def read_input(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        result = subprocess.run(
            ["pdftotext", str(path), "-"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            raise SystemExit((result.stderr or result.stdout or "pdftotext failed").strip())
        return result.stdout
    return path.read_text(encoding="utf-8")


def normalize_timecode(value: str) -> str:
    return value.strip().replace(";", ":")


def timecode_to_frames(value: str, fps: float) -> int:
    hh, mm, ss, ff = [int(part) for part in normalize_timecode(value).split(":")]
    return int(round((hh * 3600 + mm * 60 + ss) * fps + ff))


def color_from_label(label: str) -> tuple[str | None, str]:
    # Labels are often like "#2 Rose" or "#14 改札/入管".
    lowered = label.lower()
    for key, resolve_color in COLOR_MAP.items():
        if key in lowered:
            return key.title(), resolve_color
    return None, "Tan"


def parse_blocks(text: str, fps: float) -> list[dict[str, Any]]:
    blocks = []
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if "##" not in line:
            continue
        timecodes = TIMECODE_RE.findall(line)
        if len(timecodes) < 2:
            continue
        parts = [part.strip() for part in re.split(r"[｜|]", line) if part.strip()]
        if len(parts) < 2:
            continue
        seg = re.sub(r"^[^\w〔【#]*##\s*", "", parts[0]).strip()
        label = parts[1].strip()
        script_color, resolve_color = color_from_label(label)
        source_in_tc = normalize_timecode(timecodes[0])
        source_out_tc = normalize_timecode(timecodes[1])
        source_in = timecode_to_frames(source_in_tc, fps)
        source_out = timecode_to_frames(source_out_tc, fps)
        if source_out <= source_in:
            continue
        blocks.append(
            {
                "block_id": "",
                "seg": seg,
                "label": label,
                "script_color": script_color,
                "resolve_color": resolve_color,
                "source_in_timecode": source_in_tc,
                "source_out_timecode": source_out_tc,
                "source_in_frame": source_in,
                "source_out_frame": source_out,
                "duration_frames": source_out - source_in,
                "duration_text": parts[3] if len(parts) > 3 else "",
                "source_line": line_number,
                "raw": line,
            }
        )
    blocks.sort(key=lambda block: (int(block["source_in_frame"]), int(block["source_out_frame"])))
    for index, block in enumerate(blocks, start=1):
        block["block_id"] = f"block-{index:03d}"
    return blocks


def frames_to_tc(frames: int, fps: float) -> str:
    fps_i = int(round(fps))
    hours = frames // (fps_i * 3600)
    frames %= fps_i * 3600
    minutes = frames // (fps_i * 60)
    frames %= fps_i * 60
    seconds = frames // fps_i
    ff = frames % fps_i
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{ff:02d}"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csv(path: Path, blocks: list[dict[str, Any]], fps: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "block_id",
        "seg",
        "label",
        "script_color",
        "resolve_color",
        "source_in_timecode",
        "source_out_timecode",
        "duration_timecode",
        "duration_frames",
        "duration_text",
        "raw",
    ]
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for block in blocks:
            writer.writerow(
                {
                    **{key: block.get(key, "") for key in fieldnames},
                    "duration_timecode": frames_to_tc(int(block["duration_frames"]), fps),
                }
            )


def write_report(path: Path, payload: dict[str, Any]) -> None:
    fps = float(payload["fps"])
    blocks = payload["blocks"]
    total = sum(int(block["duration_frames"]) for block in blocks)
    lines = [
        "# Platto Block Color Plan",
        "",
        f"- Source: `{payload['source']}`",
        f"- FPS: {fps:g}",
        f"- Blocks: {len(blocks)}",
        f"- Block total duration: `{frames_to_tc(total, fps)}`",
        "",
        "## Blocks",
        "",
    ]
    for block in blocks:
        lines.append(
            f"- `{block['block_id']}` {block['seg']} / {block['label']} / "
            f"{block['source_in_timecode']} -> {block['source_out_timecode']} / "
            f"{block['resolve_color']}"
        )
    lines.extend(
        [
            "",
            "## Pipeline Note",
            "",
            "Use this before line-level filler cuts. The goal is to create or color coarse SEG blocks first,",
            "then do precise cuts only after the script/block structure is approved.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract SEG block color plan from Platto script PDF/text.")
    parser.add_argument("script", type=Path)
    parser.add_argument("--fps", type=float, default=24.0)
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--out-csv", type=Path, required=True)
    parser.add_argument("--out-report", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    text = read_input(args.script)
    blocks = parse_blocks(text, args.fps)
    payload = {
        "schema": "platto_block_color_plan.v0",
        "source": str(args.script),
        "fps": args.fps,
        "color_map": COLOR_MAP,
        "blocks": blocks,
    }
    write_json(args.out_json, payload)
    write_csv(args.out_csv, blocks, args.fps)
    write_report(args.out_report, payload)
    print(f"Wrote block color plan JSON: {args.out_json}")
    print(f"Wrote block color plan CSV: {args.out_csv}")
    print(f"Wrote block color report: {args.out_report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
