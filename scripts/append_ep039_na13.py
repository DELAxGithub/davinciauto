#!/usr/bin/env python3
"""Append missing EP039 NA13 WAV to A3 at the current A3 tail."""

from __future__ import annotations

import json
import wave
from pathlib import Path
from typing import Any


def find_timeline(project: Any, name: str) -> Any:
    for index in range(1, project.GetTimelineCount() + 1):
        timeline = project.GetTimelineByIndex(index)
        if timeline and timeline.GetName() == name:
            return timeline
    return None


def find_clip(folder: Any, name: str) -> Any:
    for clip in folder.GetClipList() or []:
        if clip.GetName() == name:
            return clip
    for sub in folder.GetSubFolderList() or []:
        found = find_clip(sub, name)
        if found:
            return found
    return None


def wav_duration_frames(path: Path, fps: float) -> int:
    with wave.open(str(path), "rb") as handle:
        return max(1, round(handle.getnframes() / handle.getframerate() * fps))


def main() -> None:
    timeline_name = str(globals().get("TIMELINE", "039編集_0619_自動カット２回目"))
    na_path = Path(globals().get("NA13_WAV", "")).expanduser()
    apply = bool(globals().get("APPLY", False))
    if not na_path.exists():
        raise RuntimeError(f"NA13 wav not found: {na_path}")

    project = resolve.GetProjectManager().GetCurrentProject()  # noqa: F821
    media_pool = project.GetMediaPool()
    timeline = find_timeline(project, timeline_name)
    if not timeline:
        raise RuntimeError(f"timeline not found: {timeline_name}")
    project.SetCurrentTimeline(timeline)

    fps = float(timeline.GetSetting("timelineFrameRate") or 24)
    items = timeline.GetItemListInTrack("audio", 3) or []
    if any(item.GetName() == "NA13.wav" for item in items):
        print(json.dumps({"ok": True, "already_present": True, "timeline": timeline_name}, ensure_ascii=False, indent=2))
        return
    record_frame = max([int(item.GetEnd()) for item in items] + [int(timeline.GetStartFrame())])
    duration = wav_duration_frames(na_path, fps)
    if not apply:
        print(
            json.dumps(
                {
                    "dry_run": True,
                    "timeline": timeline_name,
                    "record_frame": record_frame,
                    "duration_frames": duration,
                    "existing_a3_clips": len(items),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    clip = find_clip(media_pool.GetRootFolder(), na_path.name)
    if not clip:
        imported = media_pool.ImportMedia([str(na_path)]) or []
        clip = imported[0] if imported else None
    if not clip:
        raise RuntimeError("failed to import/find NA13.wav")

    result = media_pool.AppendToTimeline(
        [
            {
                "mediaPoolItem": clip,
                "startFrame": 0,
                "endFrame": duration,
                "recordFrame": record_frame,
                "trackIndex": 3,
                "mediaType": 2,
            }
        ]
    )
    if not result or len(result) != 1:
        raise RuntimeError("Resolve rejected NA13 append")
    print(json.dumps({"ok": True, "timeline": timeline_name, "record_frame": record_frame, "duration_frames": duration}, ensure_ascii=False, indent=2))


if "resolve" in globals():
    main()
