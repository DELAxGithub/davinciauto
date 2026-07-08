#!/usr/bin/env python3
"""Estimate script duration from Doc-to-DaVinci IR before touching Resolve."""

from __future__ import annotations

import argparse
import csv
import json
import re
import wave
from pathlib import Path
from typing import Any


def load_ir(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "doc_to_davinci_desired_timeline_ir.v0":
        raise SystemExit(f"Unsupported IR schema: {data.get('schema')!r}")
    return data


def frames_to_tc(frames: int, fps: float) -> str:
    fps_i = int(round(fps))
    hours = frames // (fps_i * 3600)
    frames %= fps_i * 3600
    minutes = frames // (fps_i * 60)
    frames %= fps_i * 60
    seconds = frames // fps_i
    ff = frames % fps_i
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{ff:02d}"


def wav_duration_frames(path: Path, fps: float) -> int | None:
    if not path.exists():
        return None
    with wave.open(str(path), "rb") as handle:
        seconds = handle.getnframes() / handle.getframerate()
    return max(1, int(round(seconds * fps)))


def text_duration_frames(text: str, fps: float, chars_per_second: float) -> int:
    stripped = re.sub(r"\s+", "", text)
    seconds = max(1.0, len(stripped) / chars_per_second)
    return max(1, int(round(seconds * fps)))


def priority_of(entry: dict[str, Any]) -> str:
    priority = str(entry.get("priority") or "").strip().upper()
    return priority if priority in {"A", "B", "C"} else ""


def instruction_text(entry: dict[str, Any]) -> str:
    return " ".join(str(entry.get(key) or "") for key in ("notes", "action")).upper()


def is_cut_if_over(entry: dict[str, Any]) -> bool:
    text = instruction_text(entry)
    return "CUT_IF_OVER" in text or "尺調整" in str(entry.get("notes") or "")


def build_events(
    ir: dict[str, Any],
    na_dir: Path | None,
    chars_per_second: float,
) -> list[dict[str, Any]]:
    fps = float(ir["fps"])
    events = []
    for entry in ir.get("entries", []):
        action = str(entry.get("action") or "")
        speaker = str(entry.get("speaker") or "")
        transcript = str(entry.get("transcript") or "")
        duration = entry.get("duration_frames")
        source_in = entry.get("source_in_frame")

        if action in {"KEEP", "RESTORE"} and duration:
            events.append(
                {
                    "type": action,
                    "doc_row_id": entry.get("doc_row_id"),
                    "priority": priority_of(entry),
                    "source_in_frame": source_in,
                    "duration_frames": int(duration),
                    "duration_source": "source_tc",
                    "speaker": speaker,
                    "transcript": transcript,
                    "cut_if_over": is_cut_if_over(entry),
                }
            )
            continue

        if speaker.startswith("NA") and transcript:
            wav_frames = wav_duration_frames(na_dir / f"{speaker}.wav", fps) if na_dir else None
            estimated = wav_frames if wav_frames is not None else text_duration_frames(transcript, fps, chars_per_second)
            events.append(
                {
                    "type": "NA",
                    "doc_row_id": entry.get("doc_row_id"),
                    "priority": priority_of(entry),
                    "source_in_frame": source_in,
                    "duration_frames": int(estimated),
                    "duration_source": "wav" if wav_frames is not None else "text_estimate",
                    "speaker": speaker,
                    "transcript": transcript,
                    "cut_if_over": False,
                }
            )
    events.sort(key=lambda item: (int(item.get("source_in_frame") or 10**12), 0 if item["type"] == "NA" else 1))
    cursor = 0
    for event in events:
        event["record_start_frame"] = cursor
        cursor += int(event["duration_frames"])
        event["record_end_frame"] = cursor
    return events


def summarize(events: list[dict[str, Any]], fps: float, target_minutes: float | None) -> dict[str, Any]:
    totals: dict[str, int] = {}
    priority_totals: dict[str, int] = {}
    for event in events:
        totals[event["type"]] = totals.get(event["type"], 0) + int(event["duration_frames"])
        priority = event.get("priority") or "none"
        priority_totals[priority] = priority_totals.get(priority, 0) + int(event["duration_frames"])
    total_frames = sum(int(event["duration_frames"]) for event in events)
    target_frames = int(round(target_minutes * 60 * fps)) if target_minutes else None
    delta_frames = total_frames - target_frames if target_frames is not None else None
    return {
        "event_count": len(events),
        "total_frames": total_frames,
        "total_tc": frames_to_tc(total_frames, fps),
        "total_seconds": round(total_frames / fps, 3),
        "target_minutes": target_minutes,
        "target_frames": target_frames,
        "target_tc": frames_to_tc(target_frames, fps) if target_frames is not None else None,
        "delta_frames": delta_frames,
        "delta_tc": frames_to_tc(abs(delta_frames), fps) if delta_frames is not None else None,
        "status": "over" if delta_frames and delta_frames > 0 else "under" if delta_frames and delta_frames < 0 else "on_target",
        "totals_by_type": totals,
        "totals_by_priority": priority_totals,
    }


def candidate_rows(events: list[dict[str, Any]], fps: float, kind: str) -> list[dict[str, Any]]:
    if kind == "restore":
        candidates = [event for event in events if event["type"] == "RESTORE"]
    else:
        candidates = [event for event in events if event.get("cut_if_over") or event.get("priority") in {"B", "C"}]
    rows = []
    for event in candidates:
        rows.append(
            {
                "type": event["type"],
                "priority": event.get("priority") or "",
                "name": event.get("speaker") or event.get("doc_row_id"),
                "doc_row_id": event.get("doc_row_id"),
                "duration_frames": event["duration_frames"],
                "duration_tc": frames_to_tc(int(event["duration_frames"]), fps),
                "transcript": str(event.get("transcript") or "")[:80],
            }
        )
    order = {"A": 0, "B": 1, "C": 2, "": 3}
    rows.sort(key=lambda row: (order.get(row["priority"], 9), -int(row["duration_frames"])))
    return rows


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csv(path: Path, events: list[dict[str, Any]], fps: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "order",
        "type",
        "speaker",
        "priority",
        "doc_row_id",
        "duration_frames",
        "duration_tc",
        "duration_source",
        "record_start_frame",
        "record_start_tc",
        "record_end_frame",
        "record_end_tc",
        "transcript",
    ]
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for index, event in enumerate(events, start=1):
            writer.writerow(
                {
                    "order": index,
                    "type": event["type"],
                    "speaker": event.get("speaker") or "",
                    "priority": event.get("priority") or "",
                    "doc_row_id": event.get("doc_row_id") or "",
                    "duration_frames": event["duration_frames"],
                    "duration_tc": frames_to_tc(int(event["duration_frames"]), fps),
                    "duration_source": event["duration_source"],
                    "record_start_frame": event["record_start_frame"],
                    "record_start_tc": frames_to_tc(int(event["record_start_frame"]), fps),
                    "record_end_frame": event["record_end_frame"],
                    "record_end_tc": frames_to_tc(int(event["record_end_frame"]), fps),
                    "transcript": event.get("transcript") or "",
                }
            )


def write_report(path: Path, payload: dict[str, Any]) -> None:
    summary = payload["summary"]
    fps = float(payload["fps"])
    lines = [
        "# Doc Duration Estimate",
        "",
        f"- IR: `{payload['ir_json']}`",
        f"- FPS: {fps:g}",
        f"- Events: {summary['event_count']}",
        f"- Estimated duration: `{summary['total_tc']}` ({summary['total_seconds']} sec)",
    ]
    if summary["target_minutes"] is not None:
        direction = "over" if summary["status"] == "over" else "under" if summary["status"] == "under" else "on target"
        lines.append(f"- Target: `{summary['target_tc']}` ({summary['target_minutes']} min)")
        lines.append(f"- Delta: `{summary['delta_tc']}` {direction}")

    lines.extend(["", "## Totals By Type", ""])
    for key, frames in sorted(summary["totals_by_type"].items()):
        lines.append(f"- `{key}`: `{frames_to_tc(int(frames), fps)}` ({frames} frames)")

    lines.extend(["", "## Restore Candidates", ""])
    restore_rows = payload["restore_candidates"]
    if restore_rows:
        for row in restore_rows[:20]:
            lines.append(f"- `{row['priority'] or '-'}` {row['name']}: `{row['duration_tc']}` {row['transcript']}")
    else:
        lines.append("- None")

    lines.extend(["", "## Cut If Over Candidates", ""])
    cut_rows = payload["cut_if_over_candidates"]
    if cut_rows:
        for row in cut_rows[:20]:
            lines.append(f"- `{row['priority'] or '-'}` {row['name']}: `{row['duration_tc']}` {row['transcript']}")
    else:
        lines.append("- None")

    lines.extend(
        [
            "",
            "## Next Loop",
            "",
            "1. If the estimate is short, mark more rows as `RESTORE` and assign `PRIORITY:A/B/C`.",
            "2. If the estimate is long, mark rows as `CUT_IF_OVER` or lower their priority.",
            "3. Regenerate IR and rerun this duration report.",
            "4. Touch DaVinci only after the script duration is close enough.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Estimate duration from Doc-to-DaVinci IR without touching Resolve.")
    parser.add_argument("ir_json", type=Path)
    parser.add_argument("--na-dir", type=Path, help="Directory containing NA*.wav. If absent, text estimate is used.")
    parser.add_argument("--target-minutes", type=float, help="Target duration in minutes.")
    parser.add_argument("--chars-per-second", type=float, default=8.0, help="Fallback NA reading speed estimate.")
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--out-report", type=Path, required=True)
    parser.add_argument("--out-csv", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    ir = load_ir(args.ir_json)
    fps = float(ir["fps"])
    events = build_events(ir, args.na_dir, args.chars_per_second)
    payload = {
        "schema": "doc_to_davinci_duration_report.v0",
        "ir_json": str(args.ir_json),
        "fps": fps,
        "na_dir": str(args.na_dir) if args.na_dir else None,
        "summary": summarize(events, fps, args.target_minutes),
        "restore_candidates": candidate_rows(events, fps, "restore"),
        "cut_if_over_candidates": candidate_rows(events, fps, "cut"),
        "events": events,
    }
    write_json(args.out_json, payload)
    write_report(args.out_report, payload)
    write_csv(args.out_csv, events, fps)
    print(f"Wrote duration JSON: {args.out_json}")
    print(f"Wrote duration report: {args.out_report}")
    print(f"Wrote duration events CSV: {args.out_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
