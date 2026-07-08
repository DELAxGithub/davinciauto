#!/usr/bin/env python3
"""Polish the generated JAL Kumojo Shosai timeline after initial placement."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


CUSTOM_PREFIX = "jal-kumojo-pilot-v0:"


def find_timeline(project: Any, name: str) -> Any:
    for index in range(1, project.GetTimelineCount() + 1):
        timeline = project.GetTimelineByIndex(index)
        if timeline and timeline.GetName() == name:
            return timeline
    return None


def seconds_to_frame(seconds: float, fps: float) -> int:
    return int(round(seconds * fps))


def apply(resolve: Any) -> dict[str, Any]:
    project_dir = Path(str(globals().get("PROJECT_DIR", ""))).expanduser().resolve()
    timeline_name = str(globals().get("TIMELINE_NAME", "JAL_雲上書斎_Pilot_v001"))
    apply_changes = bool(globals().get("APPLY", False))
    manager = resolve.GetProjectManager()
    project = manager.GetCurrentProject() if manager else None
    if not project:
        raise RuntimeError("no active Resolve project")
    timeline = find_timeline(project, timeline_name)
    if not timeline:
        raise RuntimeError(f"timeline not found: {timeline_name}")
    timing = json.loads((project_dir / "outputs/timing/timing.json").read_text(encoding="utf-8"))
    ir = json.loads((project_dir / "outputs/ir/project_ir.json").read_text(encoding="utf-8"))
    fps = float(timeline.GetSetting("timelineFrameRate") or 24)

    section_starts: dict[str, float] = {}
    for item in timing["segments"]:
        section_starts.setdefault(item["section_id"], float(item["actual_start_sec"]))
    section_titles = {section["section_id"]: section["title"] for section in ir["sections"]}

    summary = {
        "timeline": timeline_name,
        "dry_run": not apply_changes,
        "fps": fps,
        "section_markers": len(section_starts),
    }
    if not apply_changes:
        return summary

    project.SetCurrentTimeline(timeline)
    for frame, marker in list((timeline.GetMarkers() or {}).items()):
        data = marker.get("customData") or marker.get("custom_data") or ""
        if isinstance(data, str) and data.startswith(CUSTOM_PREFIX):
            timeline.DeleteMarkerAtFrame(frame)

    colors = ["Sky", "Mint", "Yellow", "Lavender", "Cream"]
    for index, (section_id, start_sec) in enumerate(section_starts.items()):
        frame = seconds_to_frame(start_sec, fps)
        timeline.AddMarker(
            frame,
            colors[index % len(colors)],
            f"{section_id} {section_titles.get(section_id, '')}",
            "Generated section marker, aligned to actual narration timing",
            max(1, seconds_to_frame(1.0, fps)),
            f"{CUSTOM_PREFIX}section:{section_id}",
        )

    # Track naming is best-effort; older Resolve builds may not expose it.
    for args in [
        ("audio", 1, "A1 Gemini NA"),
        ("audio", 2, "A2 Spare"),
        ("audio", 3, "A3 SE / Atmos"),
        ("audio", 4, "A4 Temp BGM"),
        ("video", 1, "V1 Picture"),
    ]:
        try:
            timeline.SetTrackName(*args)
        except Exception:
            pass

    return summary


RESULT = apply(resolve)
print(json.dumps(RESULT, ensure_ascii=False, indent=2, default=str))
