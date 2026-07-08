#!/usr/bin/env python3
"""Set the current Resolve timeline by name."""

from __future__ import annotations

import json
from typing import Any


def find_timeline(project: Any, name: str) -> Any:
    for index in range(1, project.GetTimelineCount() + 1):
        timeline = project.GetTimelineByIndex(index)
        if timeline and timeline.GetName() == name:
            return timeline
    return None


timeline_name = str(globals().get("TIMELINE_NAME", ""))
manager = resolve.GetProjectManager()
project = manager.GetCurrentProject() if manager else None
if not project:
    raise RuntimeError("no active Resolve project")
timeline = find_timeline(project, timeline_name)
if not timeline:
    raise RuntimeError(f"timeline not found: {timeline_name}")
if not project.SetCurrentTimeline(timeline):
    raise RuntimeError(f"failed to set current timeline: {timeline_name}")
print(json.dumps({"ok": True, "timeline": timeline_name}, ensure_ascii=False))
