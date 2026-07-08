#!/usr/bin/env python3
"""Build a Doc/CSV derived desired-state IR for DaVinci automation.

V0 intentionally stops before mutating Resolve. It converts the EP39/EP40
editing table contract into frame-based JSON and a review report.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


REQUIRED_HEADERS = ["編集指示", "Speaker Name", "イン点", "アウト点", "文字起こし"]
OPTIONAL_COLOR_HEADER = "色選択"
HEADER_ALIASES = {
    "編集指示": ["編集指示"],
    "Speaker Name": ["Speaker Name", "スピーカーネーム"],
    "イン点": ["イン点"],
    "アウト点": ["アウト点"],
    "文字起こし": ["文字起こし", "スピーカーAの文字起こし", "スピーカーBの文字起こし", "AやB以外"],
}
PLACEMENT_ACTIONS = {"KEEP", "RESTORE"}
AUTO_CLASS = "自動反映可能"
SEMI_CLASS = "半自動"
MANUAL_CLASS = "手作業必須"
MARKER_COLORS = {
    "KEEP": "Green",
    "RESTORE": "Blue",
    "CUT": "Red",
    "MOVE": "Purple",
    "NOTE": "Yellow",
    "SOURCE": "Yellow",
}


@dataclass
class IrEntry:
    doc_row_id: str
    action: str
    automation_classification: str
    priority: str | None
    source_in_frame: int | None
    source_out_frame: int | None
    record_start_frame: int | None
    duration_frames: int | None
    tracks: list[str]
    speaker: str
    transcript: str
    notes: str
    source_in_timecode: str
    source_out_timecode: str
    color: str | None
    issues: list[str]


def normalize_timecode(value: str) -> str:
    return value.strip().replace(";", ":")


def timecode_to_frames(value: str, fps: float) -> int:
    tc = normalize_timecode(value)
    parts = tc.split(":")
    if len(parts) != 4:
        raise ValueError(f"invalid timecode: {value!r}")
    hours, minutes, seconds, frames = [int(part or 0) for part in parts]
    return int(round((hours * 3600 + minutes * 60 + seconds) * fps + frames))


def stable_row_id(row_index: int, row: dict[str, str]) -> str:
    material = "\u241f".join((row.get(header) or "").strip() for header in REQUIRED_HEADERS)
    digest = hashlib.sha1(material.encode("utf-8")).hexdigest()[:8]
    return f"row-{row_index:04d}-{digest}"


def extract_priority(instruction: str) -> str | None:
    match = re.search(r"\bPRIORITY:([ABC])\b", instruction, flags=re.IGNORECASE)
    if match:
        return match.group(1).upper()
    match = re.search(r"優先度[:：]?\s*([ABCＡＢＣ])", instruction, flags=re.IGNORECASE)
    if match:
        table = str.maketrans("ＡＢＣ", "ABC")
        return match.group(1).translate(table).upper()
    return None


def extract_note(instruction: str) -> str:
    match = re.search(r"\bNOTE:(.*)", instruction, flags=re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return instruction.strip()


def normalize_action(instruction: str, color: str | None, color_policy: str) -> str:
    text = instruction.strip()
    upper = text.upper()

    for action in ("RESTORE", "KEEP", "CUT"):
        if re.search(rf"\b{action}\b", upper):
            return action
    if "MOVE_AFTER:" in upper:
        return "MOVE"

    if any(token in text for token in ("復活", "戻す", "戻し")):
        return "RESTORE"
    if any(token in text for token in ("カット", "削除", "落とし", "落とす", "不要")):
        return "CUT"
    if any(token in text for token in ("残し", "残す", "キープ", "使用")):
        return "KEEP"
    if any(token in text for token in ("移動", "ラストへ", "後ろへ")):
        return "MOVE"

    if color_policy == "keep" and color and color.strip():
        return "KEEP"
    if color_policy == "keep" and not text:
        return "CUT"
    if not text:
        return "SOURCE"
    return "NOTE"


def classify_entry(action: str, duration_frames: int | None, issues: list[str]) -> str:
    if issues:
        return MANUAL_CLASS
    if action in PLACEMENT_ACTIONS and duration_frames:
        return AUTO_CLASS
    return SEMI_CLASS


def resolve_header(headers: list[str], canonical: str) -> str | None:
    for candidate in HEADER_ALIASES[canonical]:
        if candidate in headers:
            return candidate
    return None


def normalize_raw_row(raw: dict[str, str], header_map: dict[str, str | None]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for canonical in REQUIRED_HEADERS:
        source = header_map.get(canonical)
        if canonical == "文字起こし":
            parts = []
            for candidate in HEADER_ALIASES[canonical]:
                value = (raw.get(candidate) or "").strip()
                if value:
                    parts.append(value)
            normalized[canonical] = " / ".join(parts)
        else:
            normalized[canonical] = (raw.get(source or "") or "").strip()
    if OPTIONAL_COLOR_HEADER in raw:
        normalized[OPTIONAL_COLOR_HEADER] = (raw.get(OPTIONAL_COLOR_HEADER) or "").strip()
    return normalized


def read_rows(csv_path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with csv_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        headers = reader.fieldnames or []
        header_map = {canonical: resolve_header(headers, canonical) for canonical in REQUIRED_HEADERS}
        missing = [
            header
            for header, resolved in header_map.items()
            if resolved is None and header != "編集指示"
        ]
        if missing:
            raise SystemExit(f"Missing required headers: {', '.join(missing)}")
        rows = [normalize_raw_row({key: (value or "") for key, value in row.items()}, header_map) for row in reader]
    return rows, headers


def build_ir(
    rows: Iterable[dict[str, str]],
    fps: float,
    tracks: list[str],
    compact_record: bool,
    color_policy: str,
) -> tuple[list[IrEntry], list[str]]:
    entries: list[IrEntry] = []
    warnings: list[str] = []
    record_cursor = 0

    for row_number, row in enumerate(rows, start=1):
        instruction = (row.get("編集指示") or "").strip()
        color = (row.get(OPTIONAL_COLOR_HEADER) or "").strip() or None
        in_tc = normalize_timecode(row.get("イン点") or "")
        out_tc = normalize_timecode(row.get("アウト点") or "")
        action = normalize_action(instruction, color, color_policy)
        priority = extract_priority(instruction)

        source_in_frame: int | None = None
        source_out_frame: int | None = None
        duration_frames: int | None = None
        record_start_frame: int | None = None
        row_issues: list[str] = []

        if in_tc and out_tc:
            try:
                source_in_frame = timecode_to_frames(in_tc, fps)
                source_out_frame = timecode_to_frames(out_tc, fps)
                duration_frames = source_out_frame - source_in_frame
                if duration_frames <= 0:
                    row_issues.append("out timecode is not after in timecode")
                    duration_frames = None
            except ValueError as exc:
                row_issues.append(str(exc))
        elif action in PLACEMENT_ACTIONS:
            row_issues.append("placement action without complete in/out timecode")

        if action in PLACEMENT_ACTIONS and duration_frames:
            record_start_frame = record_cursor if compact_record else source_in_frame
            record_cursor += duration_frames

        warnings.extend(f"row {row_number}: {issue}" for issue in row_issues)

        entries.append(
            IrEntry(
                doc_row_id=stable_row_id(row_number, row),
                action=action,
                automation_classification=classify_entry(action, duration_frames, row_issues),
                priority=priority,
                source_in_frame=source_in_frame,
                source_out_frame=source_out_frame,
                record_start_frame=record_start_frame,
                duration_frames=duration_frames,
                tracks=tracks,
                speaker=(row.get("Speaker Name") or "").strip(),
                transcript=(row.get("文字起こし") or "").strip(),
                notes=extract_note(instruction),
                source_in_timecode=in_tc,
                source_out_timecode=out_tc,
                color=color,
                issues=row_issues,
            )
        )

    return entries, warnings


def action_counts(entries: Iterable[IrEntry]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for entry in entries:
        counts[entry.action] = counts.get(entry.action, 0) + 1
    return dict(sorted(counts.items()))


def classification_counts(entries: Iterable[IrEntry]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for entry in entries:
        counts[entry.automation_classification] = counts.get(entry.automation_classification, 0) + 1
    return {key: counts.get(key, 0) for key in (AUTO_CLASS, SEMI_CLASS, MANUAL_CLASS)}


def build_placement_plan(entries: Iterable[IrEntry]) -> list[dict[str, object]]:
    plan: list[dict[str, object]] = []
    for entry in entries:
        if entry.automation_classification != AUTO_CLASS:
            continue
        if entry.record_start_frame is None or entry.source_in_frame is None or entry.duration_frames is None:
            continue
        plan.append(
            {
                "doc_row_id": entry.doc_row_id,
                "action": entry.action,
                "record_start_frame": entry.record_start_frame,
                "source_in_frame": entry.source_in_frame,
                "duration_frames": entry.duration_frames,
                "tracks": entry.tracks,
                "speaker": entry.speaker,
                "transcript": entry.transcript,
            }
        )
    return plan


def build_marker_plan(entries: Iterable[IrEntry]) -> list[dict[str, object]]:
    plan: list[dict[str, object]] = []
    for entry in entries:
        if entry.source_in_frame is None:
            continue
        plan.append(
            {
                "doc_row_id": entry.doc_row_id,
                "action": entry.action,
                "color": MARKER_COLORS.get(entry.action, "Yellow"),
                "source_in_frame": entry.source_in_frame,
                "source_out_frame": entry.source_out_frame,
                "duration_frames": entry.duration_frames,
                "speaker": entry.speaker,
                "note": entry.notes,
            }
        )
    return plan


def write_json(
    path: Path,
    csv_path: Path,
    headers: list[str],
    fps: float,
    entries: list[IrEntry],
    warnings: list[str],
    color_policy: str,
) -> None:
    payload = {
        "schema": "doc_to_davinci_desired_timeline_ir.v0",
        "source_csv": str(csv_path),
        "fps": fps,
        "color_policy": color_policy,
        "required_headers": REQUIRED_HEADERS,
        "optional_headers_present": [OPTIONAL_COLOR_HEADER] if OPTIONAL_COLOR_HEADER in headers else [],
        "action_counts": action_counts(entries),
        "classification_counts": classification_counts(entries),
        "warnings": warnings,
        "placement_plan": build_placement_plan(entries),
        "marker_plan": build_marker_plan(entries),
        "entries": [asdict(entry) for entry in entries],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_report(path: Path, csv_path: Path, entries: list[IrEntry], warnings: list[str], color_policy: str) -> None:
    counts = action_counts(entries)
    class_counts = classification_counts(entries)
    placement_plan = build_placement_plan(entries)
    marker_plan = build_marker_plan(entries)
    total_frames = sum(int(item["duration_frames"]) for item in placement_plan)
    lines = [
        "# Doc to DaVinci IR Report",
        "",
        f"- Source CSV: `{csv_path}`",
        f"- Color policy: `{color_policy}`",
        f"- Rows: {len(entries)}",
        f"- Auto placement rows: {len(placement_plan)}",
        f"- Placement frames: {total_frames}",
        f"- Marker rows: {len(marker_plan)}",
        "",
        "## Action Counts",
        "",
    ]
    for action, count in counts.items():
        lines.append(f"- `{action}`: {count}")

    lines.extend(["", "## Automation Classification", ""])
    for label, count in class_counts.items():
        lines.append(f"- `{label}`: {count}")

    lines.extend(["", "## Placement Plan", ""])
    if placement_plan:
        for item in placement_plan[:20]:
            lines.append(
                "- `{doc_row_id}` {action}: record {record_start_frame}, source {source_in_frame}, "
                "duration {duration_frames}, tracks {tracks}".format(
                    **{**item, "tracks": ",".join(str(track) for track in item["tracks"])}
                )
            )
        if len(placement_plan) > 20:
            lines.append(f"- ... {len(placement_plan) - 20} more")
    else:
        lines.append("- None")

    lines.extend(["", "## Marker Plan", ""])
    if marker_plan:
        for item in marker_plan[:20]:
            lines.append(
                "- `{doc_row_id}` {action}/{color}: source {source_in_frame}-{source_out_frame}".format(**item)
            )
        if len(marker_plan) > 20:
            lines.append(f"- ... {len(marker_plan) - 20} more")
    else:
        lines.append("- None")

    lines.extend(["", "## Warnings", ""])
    if warnings:
        lines.extend(f"- {warning}" for warning in warnings)
    else:
        lines.append("- None")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_edit_template(path: Path, entries: list[IrEntry]) -> None:
    """Write a clean table for humans to add machine-readable edit decisions."""
    fieldnames = [
        "編集指示",
        "Speaker Name",
        "イン点",
        "アウト点",
        "文字起こし",
        "色選択",
        "doc_row_id",
        "現在の判定",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for entry in entries:
            writer.writerow(
                {
                    "編集指示": "",
                    "Speaker Name": entry.speaker,
                    "イン点": entry.source_in_timecode,
                    "アウト点": entry.source_out_timecode,
                    "文字起こし": entry.transcript,
                    "色選択": entry.color or "",
                    "doc_row_id": entry.doc_row_id,
                    "現在の判定": entry.action,
                }
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build DaVinci desired-state IR from an EP39/EP40 editing CSV.")
    parser.add_argument("csv", type=Path, help="CSV exported from the Google Doc editing table")
    parser.add_argument("--fps", type=float, default=24.0, help="Timeline/source fps used for frame conversion")
    parser.add_argument("--tracks", default="A1,A2", help="Comma-separated target tracks for placements")
    parser.add_argument("--out-json", type=Path, required=True, help="Output desired-state IR JSON")
    parser.add_argument("--out-report", type=Path, required=True, help="Output Markdown limit/report file")
    parser.add_argument(
        "--record-mode",
        choices=["compact", "source"],
        default="compact",
        help="compact places kept ranges consecutively; source preserves source frame positions",
    )
    parser.add_argument(
        "--color-policy",
        choices=["hint", "keep"],
        default="hint",
        help="hint keeps color as metadata only; keep treats colored rows as KEEP and blank rows as CUT",
    )
    parser.add_argument(
        "--out-edit-template",
        type=Path,
        help="Optional clean CSV for adding edit instructions without using prose headings as input",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows, headers = read_rows(args.csv)
    tracks = [track.strip() for track in args.tracks.split(",") if track.strip()]
    entries, warnings = build_ir(
        rows,
        args.fps,
        tracks,
        compact_record=args.record_mode == "compact",
        color_policy=args.color_policy,
    )
    write_json(args.out_json, args.csv, headers, args.fps, entries, warnings, args.color_policy)
    write_report(args.out_report, args.csv, entries, warnings, args.color_policy)
    if args.out_edit_template:
        write_edit_template(args.out_edit_template, entries)
        print(f"Wrote edit template: {args.out_edit_template}")
    print(f"Wrote IR: {args.out_json}")
    print(f"Wrote report: {args.out_report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
