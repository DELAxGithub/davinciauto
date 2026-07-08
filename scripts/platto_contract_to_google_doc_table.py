#!/usr/bin/env python3
"""Convert a Platto DaVinci contract CSV into a Google Doc review table CSV."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


OUTPUT_COLUMNS = ["カット候補", "Speaker Name", "素材イン点&ナレーション", "文字起こし"]


def normalize_instruction(value: str) -> str:
    return (value or "").strip()


def cut_candidate_value(instruction: str) -> str:
    upper = instruction.upper()
    if upper.startswith("CUT"):
        return "CUT"
    if upper.startswith("RESTORE"):
        return "RESTORE"
    if upper.startswith("CUT_IF_OVER"):
        return "CUT_IF_OVER"
    return ""


def is_narration_row(speaker: str, instruction: str, in_tc: str, out_tc: str) -> bool:
    speaker_upper = (speaker or "").strip().upper()
    instruction_upper = (instruction or "").strip().upper()
    return (
        speaker_upper.startswith("NA")
        or instruction_upper.startswith("NOTE:NA")
        or (not in_tc.strip() and not out_tc.strip() and speaker_upper.startswith("N"))
    )


def convert_row(row: dict[str, str]) -> dict[str, str]:
    instruction = normalize_instruction(row.get("編集指示", ""))
    speaker = (row.get("Speaker Name", "") or "").strip()
    in_tc = (row.get("イン点", "") or "").strip()
    out_tc = (row.get("アウト点", "") or "").strip()
    transcript = row.get("文字起こし", "") or ""

    if is_narration_row(speaker, instruction, in_tc, out_tc):
        material_or_na = transcript.strip()
        transcript_out = ""
    else:
        material_or_na = in_tc
        transcript_out = transcript.strip()

    return {
        "カット候補": cut_candidate_value(instruction),
        "Speaker Name": speaker,
        "素材イン点&ナレーション": material_or_na,
        "文字起こし": transcript_out,
    }


def move_na_after_next_block(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Move leading NA rows to the end of the following talk block.

    EP40's DaVinci event order places provisional NA before the block it leads
    into, while the Google Doc review table is easier to read when that NA sits
    after the preceding talk block. This keeps all non-NA rows in their original
    order and moves each pending NA just before the next NA starts.
    """

    output: list[dict[str, str]] = []
    pending_na: list[dict[str, str]] = []

    for row in rows:
        instruction = normalize_instruction(row.get("編集指示", ""))
        speaker = (row.get("Speaker Name", "") or "").strip()
        in_tc = (row.get("イン点", "") or "").strip()
        out_tc = (row.get("アウト点", "") or "").strip()

        if is_narration_row(speaker, instruction, in_tc, out_tc):
            if pending_na:
                output.extend(pending_na)
            pending_na = [row]
            continue

        output.append(row)

    if pending_na:
        output.extend(pending_na)

    return output


def move_na_after_next_color_block(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Move each pending NA after the next contiguous color block."""

    output: list[dict[str, str]] = []
    pending_na: list[dict[str, str]] = []
    current_color: str | None = None
    wrote_block_after_pending = False

    def flush_pending() -> None:
        nonlocal pending_na, wrote_block_after_pending
        if pending_na:
            output.extend(pending_na)
            pending_na = []
        wrote_block_after_pending = False

    for row in rows:
        instruction = normalize_instruction(row.get("編集指示", ""))
        speaker = (row.get("Speaker Name", "") or "").strip()
        in_tc = (row.get("イン点", "") or "").strip()
        out_tc = (row.get("アウト点", "") or "").strip()

        if is_narration_row(speaker, instruction, in_tc, out_tc):
            flush_pending()
            pending_na = [row]
            current_color = None
            continue

        color = (row.get("色選択", "") or "").strip()
        if pending_na and wrote_block_after_pending and color != current_color:
            flush_pending()

        output.append(row)
        if pending_na:
            wrote_block_after_pending = True
            current_color = color

    flush_pending()
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_csv")
    parser.add_argument("--out-csv", required=True)
    parser.add_argument(
        "--na-position",
        choices=("source", "after-next-block", "after-next-color-block"),
        default="source",
        help="source keeps CSV order. after-next-block moves each NA row after the following non-NA block for Google Doc review tables.",
    )
    args = parser.parse_args()

    input_path = Path(args.input_csv)
    out_path = Path(args.out_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with input_path.open("r", encoding="utf-8-sig", newline="") as src:
        reader = csv.DictReader(src)
        source_rows = list(reader)

    if args.na_position == "after-next-block":
        source_rows = move_na_after_next_block(source_rows)
    elif args.na_position == "after-next-color-block":
        source_rows = move_na_after_next_color_block(source_rows)

    rows = [convert_row(row) for row in source_rows]

    with out_path.open("w", encoding="utf-8-sig", newline="") as dst:
        writer = csv.DictWriter(dst, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    print(
        {
            "input": str(input_path),
            "out_csv": str(out_path),
            "na_position": args.na_position,
            "rows": len(rows),
            "columns": OUTPUT_COLUMNS,
        }
    )


if __name__ == "__main__":
    main()
