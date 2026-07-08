#!/usr/bin/env python3
"""Prepare a review render job for the current narrated VTR timeline.

Run through the guarded Resolve CLI. The script only adds a render queue job
when ADD_JOB=true; otherwise it reports the settings it would apply.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def global_str(name: str, default: str = "") -> str:
    return str(globals().get(name, default) or default)


def global_bool(name: str, default: bool = False) -> bool:
    return bool(globals().get(name, default))


def find_timeline(project: Any, name: str) -> Any:
    for index in range(1, project.GetTimelineCount() + 1):
        timeline = project.GetTimelineByIndex(index)
        if timeline and timeline.GetName() == name:
            return timeline
    return None


def apply(resolve: Any) -> dict[str, Any]:
    project_dir = Path(global_str("PROJECT_DIR")).expanduser().resolve()
    timeline_name = global_str("TIMELINE_NAME")
    target_dir = Path(global_str("TARGET_DIR", str(project_dir / "deliverables/review"))).expanduser().resolve()
    custom_name = global_str("CUSTOM_NAME", f"{timeline_name}_review")
    add_job = global_bool("ADD_JOB", False)

    if not timeline_name:
        raise RuntimeError("TIMELINE_NAME is required")

    manager = resolve.GetProjectManager()
    project = manager.GetCurrentProject() if manager else None
    if not project:
        raise RuntimeError("no active Resolve project")

    expected_project = global_str("EXPECTED_PROJECT", "")
    if expected_project and project.GetName() != expected_project:
        raise RuntimeError(f"expected Resolve project {expected_project!r}, got {project.GetName()!r}")

    timeline = find_timeline(project, timeline_name)
    if not timeline:
        raise RuntimeError(f"timeline not found: {timeline_name}")
    project.SetCurrentTimeline(timeline)
    target_dir.mkdir(parents=True, exist_ok=True)

    settings = {
        "SelectAllFrames": True,
        "TargetDir": str(target_dir),
        "CustomName": custom_name,
    }
    summary = {
        "project": project.GetName(),
        "timeline": timeline_name,
        "target_dir": str(target_dir),
        "custom_name": custom_name,
        "add_job": add_job,
    }
    if not add_job:
        return {**summary, "dry_run_settings": settings}

    if not project.SetRenderSettings(settings):
        raise RuntimeError(f"failed to apply render settings: {settings}")
    job_id = project.AddRenderJob()
    if not job_id:
        raise RuntimeError("failed to add render job")
    return {**summary, "job_id": job_id}


RESULT = apply(resolve)
print(json.dumps(RESULT, ensure_ascii=False, indent=2, default=str))
