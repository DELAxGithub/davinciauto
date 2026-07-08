#!/usr/bin/env python3
"""Read-only Resolve timeline audio clip inspection."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def find_timeline(project: Any, name: str) -> Any:
    for index in range(1, project.GetTimelineCount() + 1):
        timeline = project.GetTimelineByIndex(index)
        if timeline and timeline.GetName() == name:
            return timeline
    return None


def clip_summary(item: Any) -> dict[str, Any]:
    media = item.GetMediaPoolItem()
    props = media.GetClipProperty() if media else {}
    return {
        "name": item.GetName(),
        "timeline_start": int(item.GetStart()),
        "timeline_end": int(item.GetEnd()),
        "source_start": int(item.GetSourceStartFrame()),
        "source_end": int(item.GetSourceEndFrame()),
        "media_name": media.GetName() if media else None,
        "file_path": props.get("File Path") if isinstance(props, dict) else None,
    }


def main() -> None:
    if "resolve" not in globals():
        raise RuntimeError("resolve global is required")
    timeline_name = str(globals().get("TIMELINE_NAME", ""))
    if not timeline_name:
        raise RuntimeError("TIMELINE_NAME global is required")

    manager = resolve.GetProjectManager()
    project = manager.GetCurrentProject() if manager else None
    if not project:
        raise RuntimeError("no active Resolve project")
    timeline = find_timeline(project, timeline_name)
    if not timeline:
        raise RuntimeError(f"timeline not found: {timeline_name}")

    payload = {
        "timeline": timeline_name,
        "fps": float(timeline.GetSetting("timelineFrameRate") or 0),
        "start_frame": int(timeline.GetStartFrame()),
        "tracks": {},
    }
    for index in range(1, timeline.GetTrackCount("audio") + 1):
        items = timeline.GetItemListInTrack("audio", index) or []
        payload["tracks"][f"A{index}"] = [clip_summary(item) for item in items]
    output_json = str(globals().get("OUTPUT_JSON", ""))
    if output_json:
        path = Path(output_json)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


main()
