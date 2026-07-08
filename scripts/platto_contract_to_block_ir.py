#!/usr/bin/env python3
"""Build block-based Platto edit IR from a DaVinci contract CSV.

Consecutive KEEP rows are grouped into editable blocks.  This avoids creating a
timeline made of hundreds of tiny filler-level clips.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import wave
from pathlib import Path
from typing import Any


REQUIRED_HEADERS = ["編集指示", "Speaker Name", "イン点", "アウト点", "文字起こし"]
COLOR_HEADER = "色選択"


def normalize_timecode(value: str) -> str:
    return value.strip().replace(";", ":")


def timecode_to_frames(value: str, fps: float) -> int:
    parts = normalize_timecode(value).split(":")
    if len(parts) != 4:
        raise ValueError(f"invalid timecode: {value!r}")
    hh, mm, ss, ff = [int(part or 0) for part in parts]
    return int(round((hh * 3600 + mm * 60 + ss) * fps + ff))


def frames_to_tc(frames: int, fps: float) -> str:
    fps_i = int(round(fps))
    hh = frames // (fps_i * 3600)
    frames %= fps_i * 3600
    mm = frames // (fps_i * 60)
    frames %= fps_i * 60
    ss = frames // fps_i
    ff = frames % fps_i
    return f"{hh:02d}:{mm:02d}:{ss:02d}:{ff:02d}"


def stable_row_id(row_index: int, row: dict[str, str]) -> str:
    material = "\u241f".join((row.get(header) or "").strip() for header in REQUIRED_HEADERS)
    digest = hashlib.sha1(material.encode("utf-8")).hexdigest()[:8]
    return f"row-{row_index:04d}-{digest}"


def normalize_action(instruction: str) -> str:
    text = instruction.strip()
    upper = text.upper()
    for action in ("RESTORE", "KEEP", "CUT"):
        if re.search(rf"\b{action}\b", upper):
            return action
    if str(text).upper().startswith("NOTE:"):
        return "NOTE"
    if any(token in text for token in ("カット", "削除", "落とし", "落とす", "不要")):
        return "CUT"
    if any(token in text for token in ("残し", "残す", "キープ", "使用")):
        return "KEEP"
    return "NOTE" if text else "SOURCE"


def wav_duration_frames(path: Path, fps: float) -> int | None:
    if not path.exists():
        return None
    with wave.open(str(path), "rb") as handle:
        seconds = handle.getnframes() / handle.getframerate()
    return max(1, int(round(seconds * fps)))


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        headers = reader.fieldnames or []
        missing = [header for header in REQUIRED_HEADERS if header not in headers]
        if missing:
            raise SystemExit(f"missing required headers: {', '.join(missing)}")
        return [{key: (value or "").strip() for key, value in row.items()} for row in reader]


def keep_event_from_row(row_index: int, row: dict[str, str], fps: float) -> dict[str, Any]:
    source_in = timecode_to_frames(row["イン点"], fps)
    source_out = timecode_to_frames(row["アウト点"], fps)
    if source_out <= source_in:
        raise ValueError(f"row {row_index}: out <= in")
    return {
        "type": "KEEP_ROW",
        "doc_row_id": stable_row_id(row_index, row),
        "row_index": row_index,
        "speaker": row.get("Speaker Name", ""),
        "source_in_frame": source_in,
        "source_out_frame": source_out,
        "duration_frames": source_out - source_in,
        "source_in_timecode": normalize_timecode(row["イン点"]),
        "source_out_timecode": normalize_timecode(row["アウト点"]),
        "transcript": row.get("文字起こし", ""),
        "color": row.get(COLOR_HEADER, "") or None,
        "instruction": row.get("編集指示", ""),
    }


def should_merge(current: dict[str, Any], row_event: dict[str, Any], max_gap_frames: int) -> bool:
    if current.get("color") != row_event.get("color"):
        return False
    gap = int(row_event["source_in_frame"]) - int(current["source_out_frame"])
    return 0 <= gap <= max_gap_frames


def flush_block(block: dict[str, Any] | None, events: list[dict[str, Any]], fps: float) -> None:
    if not block:
        return
    block["duration_frames"] = int(block["source_out_frame"]) - int(block["source_in_frame"])
    block["source_in_timecode"] = frames_to_tc(int(block["source_in_frame"]), fps)
    block["source_out_timecode"] = frames_to_tc(int(block["source_out_frame"]), fps)
    block["speaker_summary"] = ",".join(sorted(set(block["speakers"])))
    block["transcript_preview"] = " ".join(block["transcripts"])[:180]
    del block["speakers"]
    del block["transcripts"]
    events.append(block)


def build_events(rows: list[dict[str, str]], fps: float, na_dir: Path | None, max_gap_frames: int) -> tuple[list[dict[str, Any]], list[str]]:
    events: list[dict[str, Any]] = []
    warnings: list[str] = []
    current: dict[str, Any] | None = None
    block_index = 0

    for row_index, row in enumerate(rows, start=1):
        speaker = row.get("Speaker Name", "")
        action = normalize_action(row.get("編集指示", ""))
        transcript = row.get("文字起こし", "")

        if speaker.startswith("NA"):
            flush_block(current, events, fps)
            current = None
            wav = na_dir / f"{speaker}.wav" if na_dir else None
            duration = wav_duration_frames(wav, fps) if wav else None
            events.append(
                {
                    "type": "NA",
                    "event_id": speaker,
                    "doc_row_id": stable_row_id(row_index, row),
                    "row_index": row_index,
                    "speaker": speaker,
                    "duration_frames": duration,
                    "duration_source": "wav" if duration else "missing_wav",
                    "wav_path": str(wav) if wav else "",
                    "transcript": transcript,
                    "notes": row.get("編集指示", ""),
                    "color": "Blue",
                }
            )
            if duration is None:
                warnings.append(f"row {row_index}: missing NA wav for {speaker}")
            continue

        if action != "KEEP":
            flush_block(current, events, fps)
            current = None
            continue

        try:
            row_event = keep_event_from_row(row_index, row, fps)
        except Exception as exc:  # noqa: BLE001
            warnings.append(str(exc))
            flush_block(current, events, fps)
            current = None
            continue

        if current and should_merge(current, row_event, max_gap_frames):
            current["source_out_frame"] = max(int(current["source_out_frame"]), int(row_event["source_out_frame"]))
            current["row_end"] = row_index
            current["row_ids"].append(row_event["doc_row_id"])
            current["speakers"].append(row_event["speaker"])
            current["transcripts"].append(row_event["transcript"])
            continue

        flush_block(current, events, fps)
        block_index += 1
        current = {
            "type": "KEEP_BLOCK",
            "event_id": f"B{block_index:03d}",
            "block_index": block_index,
            "row_start": row_index,
            "row_end": row_index,
            "row_ids": [row_event["doc_row_id"]],
            "source_in_frame": row_event["source_in_frame"],
            "source_out_frame": row_event["source_out_frame"],
            "color": row_event.get("color"),
            "speakers": [row_event["speaker"]],
            "transcripts": [row_event["transcript"]],
        }

    flush_block(current, events, fps)
    record_cursor = 0
    for event in events:
        duration = int(event.get("duration_frames") or 0)
        event["record_start_frame"] = record_cursor
        event["record_end_frame"] = record_cursor + duration
        event["record_start_timecode"] = frames_to_tc(record_cursor, fps)
        event["record_end_timecode"] = frames_to_tc(record_cursor + duration, fps)
        record_cursor += duration
    return events, warnings


def write_report(path: Path, payload: dict[str, Any]) -> None:
    summary = payload["summary"]
    lines = [
        "# Platto Block Timeline IR",
        "",
        f"- Source CSV: `{payload['source_csv']}`",
        f"- FPS: {payload['fps']}",
        f"- KEEP blocks: {summary['keep_blocks']}",
        f"- NA items: {summary['na_items']}",
        f"- Final duration: `{summary['final_duration_timecode']}` ({summary['final_duration_seconds']} sec)",
        f"- Average rows per block: {summary['avg_rows_per_block']}",
        "",
        "## Warnings",
        "",
    ]
    lines.extend([f"- {warning}" for warning in payload["warnings"]] or ["- None"])
    lines.extend(["", "## First Events", ""])
    for event in payload["events"][:20]:
        label = event["event_id"]
        if event["type"] == "KEEP_BLOCK":
            lines.append(
                f"- `{label}` {event['source_in_timecode']}-{event['source_out_timecode']} "
                f"rows {event['row_start']}-{event['row_end']} color={event.get('color') or '-'}"
            )
        else:
            lines.append(f"- `{label}` NA duration={event.get('duration_frames')}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", type=Path)
    parser.add_argument("--fps", type=float, default=24.0)
    parser.add_argument("--na-dir", type=Path)
    parser.add_argument("--max-gap-frames", type=int, default=1)
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--out-report", type=Path, required=True)
    args = parser.parse_args()

    rows = read_rows(args.csv)
    events, warnings = build_events(rows, args.fps, args.na_dir, args.max_gap_frames)
    keep_blocks = [event for event in events if event["type"] == "KEEP_BLOCK"]
    na_items = [event for event in events if event["type"] == "NA"]
    final_frames = max((int(event["record_end_frame"]) for event in events), default=0)
    payload = {
        "schema": "platto_block_timeline_ir.v0",
        "source_csv": str(args.csv),
        "fps": args.fps,
        "na_dir": str(args.na_dir) if args.na_dir else None,
        "warnings": warnings,
        "summary": {
            "source_rows": len(rows),
            "events": len(events),
            "keep_blocks": len(keep_blocks),
            "na_items": len(na_items),
            "final_duration_frames": final_frames,
            "final_duration_timecode": frames_to_tc(final_frames, args.fps),
            "final_duration_seconds": round(final_frames / args.fps, 3),
            "avg_rows_per_block": round(sum(len(event["row_ids"]) for event in keep_blocks) / max(len(keep_blocks), 1), 2),
        },
        "events": events,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_report(args.out_report, payload)
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
