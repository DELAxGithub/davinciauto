#!/usr/bin/env python3
"""Guarded Resolve apply entrypoint for Doc-to-DaVinci plans.

Default CLI mode is dry-run only and does not import Resolve modules. For real
Resolve mutation, run this through the guarded resolve_cli.py run-script path
with APPLY=true. Placement ops are intentionally refused until source media
mapping is implemented.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


SCHEMA = "doc_to_davinci_resolve_apply_plan.v0"
CUSTOM_DATA_PREFIX = "doc-to-davinci-v0:"


def load_plan(path: Path) -> dict[str, Any]:
    plan = json.loads(path.read_text(encoding="utf-8"))
    if plan.get("schema") != SCHEMA:
        raise SystemExit(f"Unsupported plan schema: {plan.get('schema')!r}")
    return plan


def operation_counts(plan: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for op in plan.get("operations", []):
        name = op.get("op", "<missing>")
        counts[name] = counts.get(name, 0) + 1
    return dict(sorted(counts.items()))


def unsupported_ops(plan: dict[str, Any]) -> list[str]:
    unsupported = []
    for op in plan.get("operations", []):
        if op.get("op") == "place_source_range":
            unsupported.append(f"{op.get('doc_row_id')}: place_source_range")
        if op.get("op") == "clear_generated_namespace":
            unsupported.append("clear_generated_namespace")
    return unsupported


def dry_run_payload(plan: dict[str, Any]) -> dict[str, Any]:
    unsupported = unsupported_ops(plan)
    return {
        "dry_run": True,
        "schema": plan.get("schema"),
        "source_timeline": plan.get("source_timeline"),
        "output_timeline": plan.get("output_timeline"),
        "safety": plan.get("safety", {}),
        "summary": plan.get("summary", {}),
        "operation_counts": operation_counts(plan),
        "unsupported_for_apply": unsupported,
        "apply_ready": not unsupported,
        "next_step": (
            "Implement placement and namespace clearing before --apply."
            if unsupported
            else "Run through resolve_cli.py run-script with APPLY=true."
        ),
    }


def print_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, default=str))


def find_timeline(project: Any, name: str) -> Any:
    for index in range(1, project.GetTimelineCount() + 1):
        timeline = project.GetTimelineByIndex(index)
        if timeline and timeline.GetName() == name:
            return timeline
    return None


def timeline_names(project: Any) -> list[str]:
    names = []
    for index in range(1, project.GetTimelineCount() + 1):
        timeline = project.GetTimelineByIndex(index)
        if timeline:
            names.append(timeline.GetName())
    return names


def generated_marker_count(timeline: Any) -> int:
    markers = timeline.GetMarkers() or {}
    count = 0
    for marker in markers.values():
        custom_data = ""
        if isinstance(marker, dict):
            custom_data = str(marker.get("customData") or marker.get("custom_data") or "")
        if custom_data.startswith(CUSTOM_DATA_PREFIX):
            count += 1
    return count


def apply_marker_only(resolve: Any, plan: dict[str, Any], allow_marker_only: bool) -> dict[str, Any]:
    unsupported = unsupported_ops(plan)
    if unsupported and not allow_marker_only:
        raise SystemExit(
            "Plan contains unsupported apply ops. Refusing mutation: " + ", ".join(unsupported[:10])
        )

    manager = resolve.GetProjectManager()
    project = manager.GetCurrentProject() if manager else None
    if not project:
        raise SystemExit("No active Resolve project.")

    source_name = plan["source_timeline"]
    output_name = plan["output_timeline"]
    source = find_timeline(project, source_name)
    if not source:
        raise SystemExit(f"Source timeline not found: {source_name}")

    ops = plan.get("operations", [])
    uses_existing = any(op.get("op") == "assert_timeline_exists" for op in ops)
    if uses_existing:
        target = find_timeline(project, output_name)
        if not target:
            raise SystemExit(f"Output timeline not found: {output_name}")
    else:
        if output_name in timeline_names(project):
            raise SystemExit(f"Output timeline already exists; refusing overwrite: {output_name}")
        target = source.DuplicateTimeline(output_name)
        if not target:
            raise SystemExit("Resolve rejected timeline duplication.")

    existing_generated_markers = generated_marker_count(target)
    if existing_generated_markers:
        raise SystemExit(
            f"Target already has {existing_generated_markers} generated markers; refusing duplicate apply."
        )
    project.SetCurrentTimeline(target)

    added_markers = 0
    for op in plan.get("operations", []):
        if op.get("op") != "add_marker":
            continue
        frame = int(op["source_in_frame"])
        duration = int(op.get("duration_frames") or 1)
        name = f"{op.get('action', 'DOC')} {op.get('doc_row_id', '')}".strip()
        note = op.get("note") or ""
        custom_data = f"{CUSTOM_DATA_PREFIX}{op.get('doc_row_id', added_markers)}"
        ok = target.AddMarker(
            frame,
            op.get("color", "Yellow"),
            name,
            note,
            max(1, duration),
            custom_data,
        )
        if not ok:
            raise SystemExit(f"Resolve rejected marker: {op.get('doc_row_id')}")
        added_markers += 1

    return {
        "ok": True,
        "mode": "marker-only",
        "target_mode": "target-existing" if uses_existing else "duplicate-source",
        "source_timeline": source_name,
        "output_timeline": output_name,
        "added_markers": added_markers,
        "skipped_unsupported_ops": unsupported,
    }


def cli_main() -> int:
    parser = argparse.ArgumentParser(description="Dry-run or guarded marker-only apply of a Resolve apply plan.")
    parser.add_argument("plan_json", type=Path)
    parser.add_argument("--apply", action="store_true", help="Only valid when run inside Resolve via resolve_cli.py")
    parser.add_argument(
        "--allow-marker-only",
        action="store_true",
        help="Allow marker-only mutation even when placement ops are still unsupported.",
    )
    args = parser.parse_args()
    plan = load_plan(args.plan_json)
    if not args.apply:
        print_json(dry_run_payload(plan))
        return 0
    if "resolve" not in globals():
        raise SystemExit("--apply must be run through resolve_cli.py run-script so Resolve is injected.")
    print_json(apply_marker_only(globals()["resolve"], plan, args.allow_marker_only))
    return 0


def resolve_script_entry() -> None:
    plan_path = Path(globals().get("PLAN_JSON", "")).expanduser()
    if not plan_path:
        raise SystemExit("PLAN_JSON global is required.")
    plan = load_plan(plan_path)
    apply = bool(globals().get("APPLY", False))
    allow_marker_only = bool(globals().get("ALLOW_MARKER_ONLY", False))
    if not apply:
        print_json(dry_run_payload(plan))
        return
    if "resolve" not in globals():
        raise SystemExit("resolve global is required for APPLY.")
    print_json(apply_marker_only(globals()["resolve"], plan, allow_marker_only))


if "PLAN_JSON" in globals():
    resolve_script_entry()
elif __name__ == "__main__":
    raise SystemExit(cli_main())
