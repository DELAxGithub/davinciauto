#!/usr/bin/env python3
"""Convert Doc-to-DaVinci IR into a Resolve dry-run apply plan.

This script intentionally does not connect to DaVinci Resolve. It prepares the
last reviewable artifact before a Resolve script/MCP mutation.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_ir(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "doc_to_davinci_desired_timeline_ir.v0":
        raise SystemExit(f"Unsupported IR schema: {data.get('schema')!r}")
    return data


def frame_to_timecode(frame: int, fps: float) -> str:
    fps_int = int(round(fps))
    hours = frame // (fps_int * 3600)
    frame %= fps_int * 3600
    minutes = frame // (fps_int * 60)
    frame %= fps_int * 60
    seconds = frame // fps_int
    frames = frame % fps_int
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}"


def build_apply_plan(
    ir: dict[str, Any],
    source_timeline: str,
    output_timeline: str,
    mode: str,
) -> dict[str, Any]:
    fps = float(ir["fps"])
    placements = ir.get("placement_plan", [])
    markers = ir.get("marker_plan", [])

    placement_ops = []
    for index, item in enumerate(placements, start=1):
        record_start = int(item["record_start_frame"])
        source_in = int(item["source_in_frame"])
        duration = int(item["duration_frames"])
        placement_ops.append(
            {
                "op": "place_source_range",
                "order": index,
                "doc_row_id": item["doc_row_id"],
                "action": item["action"],
                "tracks": item["tracks"],
                "record_start_frame": record_start,
                "record_start_timecode": frame_to_timecode(record_start, fps),
                "source_in_frame": source_in,
                "source_in_timecode": frame_to_timecode(source_in, fps),
                "duration_frames": duration,
                "duration_timecode": frame_to_timecode(duration, fps),
                "speaker": item.get("speaker", ""),
                "transcript": item.get("transcript", ""),
            }
        )

    marker_ops = []
    for index, item in enumerate(markers, start=1):
        source_in = int(item["source_in_frame"])
        source_out = item.get("source_out_frame")
        duration = item.get("duration_frames")
        marker_ops.append(
            {
                "op": "add_marker",
                "order": index,
                "doc_row_id": item["doc_row_id"],
                "action": item["action"],
                "color": item["color"],
                "source_in_frame": source_in,
                "source_in_timecode": frame_to_timecode(source_in, fps),
                "source_out_frame": source_out,
                "duration_frames": duration,
                "speaker": item.get("speaker", ""),
                "note": item.get("note", ""),
            }
        )

    if mode == "target-existing":
        operations = [
            {
                "op": "assert_timeline_exists",
                "target": output_timeline,
                "reason": "Use an already-created experiment timeline; source timeline remains untouched.",
            },
        ]
    else:
        operations = [
            {
                "op": "duplicate_timeline",
                "from": source_timeline,
                "to": output_timeline,
                "reason": "V0 never mutates the source timeline directly.",
            },
        ]
    if placement_ops:
        operations.append(
            {
                "op": "clear_generated_namespace",
                "target": output_timeline,
                "custom_data_prefix": "doc-to-davinci-v0:",
                "reason": "Future placement apply step should be rerunnable without duplicate generated items.",
            }
        )
    operations.extend(marker_ops)
    operations.extend(placement_ops)

    return {
        "schema": "doc_to_davinci_resolve_apply_plan.v0",
        "source_ir_schema": ir["schema"],
        "source_csv": ir.get("source_csv"),
        "fps": fps,
        "source_timeline": source_timeline,
        "output_timeline": output_timeline,
        "mode": mode,
        "safety": {
            "mutates_resolve": False,
            "requires_duplicate_timeline": mode != "target-existing",
            "touch_existing_timeline": False,
            "next_step_requires_explicit_apply": True,
        },
        "summary": {
            "input_rows": len(ir.get("entries", [])),
            "placement_ops": len(placement_ops),
            "marker_ops": len(marker_ops),
            "classification_counts": ir.get("classification_counts", {}),
            "warnings": ir.get("warnings", []),
        },
        "operations": operations,
    }


def write_json(path: Path, plan: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_report(path: Path, plan: dict[str, Any]) -> None:
    summary = plan["summary"]
    lines = [
        "# Resolve Dry-run Apply Plan",
        "",
        f"- Source timeline: `{plan['source_timeline']}`",
        f"- Output timeline: `{plan['output_timeline']}`",
        f"- Mode: `{plan['mode']}`",
        f"- Mutates Resolve: `{plan['safety']['mutates_resolve']}`",
        f"- Input rows: {summary['input_rows']}",
        f"- Placement ops: {summary['placement_ops']}",
        f"- Marker ops: {summary['marker_ops']}",
        "",
        "## Safety",
        "",
        "- Source timeline is not mutated.",
        "- Apply step must duplicate or target a separate timeline.",
        "- Existing-timeline reconcile remains out of V0 scope.",
        "",
        "## Classification Counts",
        "",
    ]
    for label, count in summary.get("classification_counts", {}).items():
        lines.append(f"- `{label}`: {count}")

    lines.extend(["", "## First Operations", ""])
    for op in plan["operations"][:25]:
        if op["op"] == "add_marker":
            lines.append(
                f"- marker `{op['doc_row_id']}` {op['action']}/{op['color']} at {op['source_in_timecode']}"
            )
        elif op["op"] == "place_source_range":
            lines.append(
                f"- place `{op['doc_row_id']}` {op['action']} record {op['record_start_timecode']} "
                f"source {op['source_in_timecode']} duration {op['duration_timecode']}"
            )
        else:
            lines.append(f"- {op['op']}: {op}")
    if len(plan["operations"]) > 25:
        lines.append(f"- ... {len(plan['operations']) - 25} more")

    lines.extend(["", "## Warnings", ""])
    warnings = summary.get("warnings", [])
    if warnings:
        lines.extend(f"- {warning}" for warning in warnings)
    else:
        lines.append("- None")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a Resolve dry-run apply plan from Doc-to-DaVinci IR.")
    parser.add_argument("ir_json", type=Path, help="IR JSON from scripts/doc_to_davinci_ir.py")
    parser.add_argument("--source-timeline", required=True, help="Resolve source timeline name")
    parser.add_argument("--output-timeline", required=True, help="Resolve output/duplicate timeline name")
    parser.add_argument(
        "--mode",
        choices=["new-timeline", "duplicate-source", "target-existing"],
        default="duplicate-source",
        help="How the future apply step should prepare the output timeline",
    )
    parser.add_argument("--out-json", type=Path, required=True, help="Output dry-run apply plan JSON")
    parser.add_argument("--out-report", type=Path, required=True, help="Output dry-run report Markdown")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    ir = load_ir(args.ir_json)
    plan = build_apply_plan(ir, args.source_timeline, args.output_timeline, args.mode)
    write_json(args.out_json, plan)
    write_report(args.out_report, plan)
    print(f"Wrote Resolve dry-run plan: {args.out_json}")
    print(f"Wrote Resolve dry-run report: {args.out_report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
