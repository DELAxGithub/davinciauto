#!/usr/bin/env python3
"""Create the JAL Kumojo Shosai pilot timeline in the open Resolve project."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


CUSTOM_PREFIX = "jal-kumojo-pilot-v0:"


def find_subfolder(parent: Any, name: str) -> Any:
    for folder in parent.GetSubFolderList() or []:
        if folder.GetName() == name:
            return folder
    return None


def ensure_bin(media_pool: Any, root: Any, path: list[str]) -> Any:
    parent = root
    for name in path:
        found = find_subfolder(parent, name)
        if not found:
            found = media_pool.AddSubFolder(parent, name)
            if not found:
                raise RuntimeError(f"failed to create bin: {'/'.join(path)}")
        parent = found
    return parent


def walk_clips(folder: Any) -> list[Any]:
    clips = list(folder.GetClipList() or [])
    for child in folder.GetSubFolderList() or []:
        clips.extend(walk_clips(child))
    return clips


def find_clip_by_path(folder: Any, path: Path) -> Any:
    target = str(path.resolve())
    for clip in walk_clips(folder):
        props = clip.GetClipProperty() or {}
        if props.get("File Path") == target:
            return clip
    return None


def timeline_names(project: Any) -> set[str]:
    names = set()
    for index in range(1, project.GetTimelineCount() + 1):
        timeline = project.GetTimelineByIndex(index)
        if timeline:
            names.add(timeline.GetName())
    return names


def seconds_to_frame(seconds: float, fps: float) -> int:
    return int(round(seconds * fps))


def import_paths(media_pool: Any, root: Any, folder: Any, paths: list[Path]) -> dict[str, Any]:
    media_pool.SetCurrentFolder(folder)
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise RuntimeError(f"missing media files: {missing[:5]}")
    media_pool.ImportMedia([str(path.resolve()) for path in paths])
    clips: dict[str, Any] = {}
    for path in paths:
        clip = find_clip_by_path(root, path)
        if not clip:
            raise RuntimeError(f"imported clip not found in media pool: {path}")
        clips[str(path.resolve())] = clip
    return clips


def add_audio_tracks(timeline: Any, count: int) -> None:
    while int(timeline.GetTrackCount("audio") or 0) < count:
        # Resolve accepts a subtype for audio tracks; stereo is a safe default.
        if not timeline.AddTrack("audio", "stereo"):
            raise RuntimeError(f"failed to add audio track {int(timeline.GetTrackCount('audio') or 0) + 1}")


def add_section_markers(timeline: Any, sections: list[dict[str, Any]], fps: float) -> None:
    colors = ["Sky", "Mint", "Yellow", "Lavender", "Cream"]
    for index, section in enumerate(sections):
        frame = seconds_to_frame(float(section["start_sec"]), fps)
        ok = timeline.AddMarker(
            frame,
            colors[index % len(colors)],
            f"{section['section_id']} {section['title']}",
            "Generated section marker",
            max(1, seconds_to_frame(1.0, fps)),
            f"{CUSTOM_PREFIX}section:{section['section_id']}",
        )
        if not ok:
            raise RuntimeError(f"failed to add section marker: {section['section_id']}")


def apply(resolve: Any) -> dict[str, Any]:
    project_dir = Path(str(globals().get("PROJECT_DIR", ""))).expanduser().resolve()
    timeline_name = str(globals().get("TIMELINE_NAME", "JAL_雲上書斎_Pilot_v001"))
    apply_changes = bool(globals().get("APPLY", False))
    if not project_dir:
        raise RuntimeError("PROJECT_DIR is required")

    manager = resolve.GetProjectManager()
    project = manager.GetCurrentProject() if manager else None
    if not project:
        raise RuntimeError("no active Resolve project")
    if project.GetName() != "JAL":
        raise RuntimeError(f"expected Resolve project 'JAL', got {project.GetName()!r}")
    if timeline_name in timeline_names(project):
        raise RuntimeError(f"timeline already exists; refusing overwrite: {timeline_name}")

    ir = json.loads((project_dir / "outputs/ir/project_ir.json").read_text(encoding="utf-8"))
    timing = json.loads((project_dir / "outputs/timing/timing.json").read_text(encoding="utf-8"))
    bgm_plan = list(csv.DictReader((project_dir / "outputs/bgm/bgm_plan.actual.csv").open(encoding="utf-8")))

    narration_paths = [Path(item["audio_path"]).resolve() for item in timing["segments"]]
    subtitle_path = (project_dir / "outputs/subtitles/timecoded.srt").resolve()
    docs_paths = [
        subtitle_path,
        (project_dir / "outputs/timing/timeline.csv").resolve(),
        (project_dir / "outputs/bgm/bgm_plan.actual.csv").resolve(),
    ]
    catalog_roots = {
        "Platto": Path("/Users/delaxpro/Dropbox/プラッと/03_プラッとBGM"),
        "Orion": Path("/Users/delaxpro/src/80_トヨタ/OrionS2_ALL/BGM解析"),
    }
    bgm_paths: list[Path] = []
    for row in bgm_plan:
        rel = Path(row["bgm_path"])
        candidates = [root / rel for root in catalog_roots.values()]
        found = next((path for path in candidates if path.exists()), None)
        if not found:
            raise RuntimeError(f"BGM file not found: {row['bgm_path']}")
        bgm_paths.append(found.resolve())

    summary = {
        "project": project.GetName(),
        "timeline_name": timeline_name,
        "dry_run": not apply_changes,
        "narration_files": len(narration_paths),
        "bgm_files": len(bgm_paths),
        "subtitle_docs": len(docs_paths),
        "duration_sec": timing["duration_sec"],
    }
    if not apply_changes:
        return summary

    media_pool = project.GetMediaPool()
    root = media_pool.GetRootFolder()
    base_bin = ensure_bin(media_pool, root, ["JAL_雲上書斎_Pilot"])
    narration_bin = ensure_bin(media_pool, base_bin, ["01_Narration"])
    bgm_bin = ensure_bin(media_pool, base_bin, ["02_BGM"])
    docs_bin = ensure_bin(media_pool, base_bin, ["03_Subtitles_Docs"])

    narration_clips = import_paths(media_pool, root, narration_bin, narration_paths)
    bgm_clips = import_paths(media_pool, root, bgm_bin, bgm_paths)
    # Importing SRT/CSV may fail depending on Resolve build; keep them in the
    # filesystem as canonical even if Media Pool ignores non-media files.
    try:
        import_paths(media_pool, root, docs_bin, [path for path in docs_paths if path.exists()])
    except Exception:
        pass

    timeline = media_pool.CreateEmptyTimeline(timeline_name)
    if not timeline:
        raise RuntimeError("Resolve rejected empty timeline creation")
    project.SetCurrentTimeline(timeline)
    fps = float(timeline.GetSetting("timelineFrameRate") or ir.get("fps") or 29.97)
    timeline_start = int(timeline.GetStartFrame())
    add_audio_tracks(timeline, 4)

    narration_items = []
    for item in timing["segments"]:
        audio_path = str(Path(item["audio_path"]).resolve())
        duration_frames = max(1, seconds_to_frame(float(item["actual_duration_sec"]), fps))
        narration_items.append(
            {
                "mediaPoolItem": narration_clips[audio_path],
                "startFrame": 0,
                "endFrame": duration_frames,
                "recordFrame": timeline_start + seconds_to_frame(float(item["actual_start_sec"]), fps),
                "trackIndex": 1,
                "mediaType": 2,
            }
        )
    appended = media_pool.AppendToTimeline(narration_items)
    if not appended:
        raise RuntimeError("Resolve rejected narration AppendToTimeline")

    bgm_items = []
    for row, path in zip(bgm_plan, bgm_paths):
        start = parse_clock(row["start"])
        end = parse_clock(row["end"])
        duration_frames = max(1, seconds_to_frame(end - start, fps))
        bgm_items.append(
            {
                "mediaPoolItem": bgm_clips[str(path.resolve())],
                "startFrame": seconds_to_frame(float(row.get("source_start_sec") or 0), fps),
                "endFrame": seconds_to_frame(float(row.get("source_start_sec") or 0), fps) + duration_frames,
                "recordFrame": timeline_start + seconds_to_frame(start, fps),
                "trackIndex": 4,
                "mediaType": 2,
            }
        )
    if bgm_items:
        if not media_pool.AppendToTimeline(bgm_items):
            raise RuntimeError("Resolve rejected BGM AppendToTimeline")

    add_section_markers(timeline, ir["sections"], fps)
    summary.update(
        {
            "fps": fps,
            "timeline_start": timeline_start,
            "audio_track_count": timeline.GetTrackCount("audio"),
            "timeline_end_frame": timeline.GetEndFrame(),
        }
    )
    return summary


def parse_clock(value: str) -> float:
    parts = value.strip().replace(",", ".").split(":")
    if len(parts) == 3:
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = float(parts[2])
        return hours * 3600 + minutes * 60 + seconds
    if len(parts) == 2:
        return int(parts[0]) * 60 + float(parts[1])
    return float(value)


RESULT = apply(resolve)
print(json.dumps(RESULT, ensure_ascii=False, indent=2, default=str))
