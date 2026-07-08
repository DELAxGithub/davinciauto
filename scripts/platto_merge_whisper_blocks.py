#!/usr/bin/env python3
"""Merge Platto Whisper rows into review-friendly utterance blocks."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


HEADER = ["Speaker Name", "イン点", "アウト点", "文字起こし", "色選択"]
TC_RE = re.compile(r"^(\d+):([0-5]\d):([0-5]\d):(\d+)$")


def tc_to_seconds(value: str, fps: float) -> float:
    match = TC_RE.match(value.strip())
    if not match:
        raise ValueError(f"unsupported timecode: {value}")
    hours, minutes, seconds, frames = map(int, match.groups())
    return hours * 3600 + minutes * 60 + seconds + frames / fps


def read_rows(path: Path, fps: float) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != HEADER:
            raise ValueError(f"{path}: expected {HEADER}, got {reader.fieldnames}")
        rows = []
        for index, row in enumerate(reader, start=1):
            row["_index"] = str(index)
            row["_start"] = str(tc_to_seconds(row["イン点"], fps))
            row["_end"] = str(tc_to_seconds(row["アウト点"], fps))
            rows.append(row)
        return rows


def should_merge(
    current: dict[str, str],
    row: dict[str, str],
    *,
    max_gap: float,
    max_duration: float,
    max_chars: int,
) -> bool:
    if row["Speaker Name"] != current["Speaker Name"]:
        return False
    gap = float(row["_start"]) - float(current["_end"])
    if gap < -0.05 or gap > max_gap:
        return False
    duration = float(row["_end"]) - float(current["_start"])
    if duration > max_duration:
        return False
    text_len = len(current["文字起こし"]) + len(row["文字起こし"])
    if text_len > max_chars:
        return False
    return True


def join_text(left: str, right: str) -> str:
    left = left.strip()
    right = right.strip()
    if not left:
        return right
    if not right:
        return left
    if left[-1] in "。！？!?」』":
        return left + right
    return left + " " + right


def merge_rows(
    rows: list[dict[str, str]],
    *,
    max_gap: float,
    max_duration: float,
    max_chars: int,
) -> list[dict[str, str]]:
    blocks: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for row in rows:
        if current and should_merge(
            current,
            row,
            max_gap=max_gap,
            max_duration=max_duration,
            max_chars=max_chars,
        ):
            current["アウト点"] = row["アウト点"]
            current["_end"] = row["_end"]
            current["文字起こし"] = join_text(current["文字起こし"], row["文字起こし"])
            continue
        if current:
            blocks.append(current)
        current = dict(row)
    if current:
        blocks.append(current)
    return blocks


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(HEADER)
        for row in rows:
            writer.writerow([row[column] for column in HEADER])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_csv", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--fps", type=float, default=24.0)
    parser.add_argument("--max-gap", type=float, default=1.0)
    parser.add_argument("--max-duration", type=float, default=18.0)
    parser.add_argument("--max-chars", type=int, default=160)
    args = parser.parse_args()

    rows = read_rows(args.input_csv, args.fps)
    blocks = merge_rows(
        rows,
        max_gap=args.max_gap,
        max_duration=args.max_duration,
        max_chars=args.max_chars,
    )
    write_rows(args.out, blocks)
    print(f"{args.input_csv}: {len(rows)} rows -> {len(blocks)} blocks")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
