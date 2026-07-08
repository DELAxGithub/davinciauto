#!/usr/bin/env python3
"""Create a narrated VTR timeline in the open Resolve project.

This is the generic Resolve applier for ``video_pipeline.workflows.narrated_vtr``.
It imports generated narration, optional BGM cues, and review documents into
organized bins, then creates a new timeline with narration on A1 and BGM on A4.
Subtitle track import is intentionally out of scope because Resolve scripting
does not reliably import SRT into subtitle tracks across builds.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def global_str(name: str, default: str = "") -> str:
    return str(globals().get(name, default) or default)


def global_bool(name: str, default: bool = False) -> bool:
    return bool(globals().get(name, default))


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
        if not timeline.AddTrack("audio", "stereo"):
            raise RuntimeError(f"failed to add audio track {int(timeline.GetTrackCount('audio') or 0) + 1}")


def set_track_names(timeline: Any) -> None:
    for args in [
        ("video", 1, "V1 Picture"),
        ("audio", 1, "A1 Gemini NA"),
        ("audio", 2, "A2 Spare"),
        ("audio", 3, "A3 SE / Atmos"),
        ("audio", 4, "A4 Temp BGM"),
    ]:
        try:
            timeline.SetTrackName(*args)
        except Exception:
            pass


def section_starts_from_timing(timing: dict[str, Any], ir: dict[str, Any]) -> list[tuple[str, str, float]]:
    starts: dict[str, float] = {}
    for item in timing.get("segments", []):
        starts.setdefault(item["section_id"], float(item["actual_start_sec"]))
    titles = {section["section_id"]: section["title"] for section in ir.get("sections", [])}
    return [(section_id, titles.get(section_id, ""), start) for section_id, start in starts.items()]


def add_section_markers(timeline: Any, timing: dict[str, Any], ir: dict[str, Any], fps: float, prefix: str) -> None:
    colors = ["Sky", "Mint", "Yellow", "Lavender", "Cream", "Cyan", "Rose"]
    for index, (section_id, title, start_sec) in enumerate(section_starts_from_timing(timing, ir)):
        ok = timeline.AddMarker(
            seconds_to_frame(start_sec, fps),
            colors[index % len(colors)],
            f"{section_id} {title}".strip(),
            "Generated section marker, aligned to actual narration timing",
            max(1, seconds_to_frame(1.0, fps)),
            f"{prefix}section:{section_id}",
        )
        if not ok:
            raise RuntimeError(f"failed to add section marker: {section_id}")


def resolve_bgm_paths(rows: list[dict[str, str]], catalog_roots: list[Path]) -> list[Path]:
    paths: list[Path] = []
    for row in rows:
        raw = Path(row["bgm_path"])
        candidates = [raw] if raw.is_absolute() else [root / raw for root in catalog_roots]
        found = next((path for path in candidates if path.exists()), None)
        if not found:
            raise RuntimeError(f"BGM file not found: {row['bgm_path']}")
        paths.append(found.resolve())
    return paths


def apply(resolve: Any) -> dict[str, Any]:
    project_dir = Path(global_str("PROJECT_DIR")).expanduser().resolve()
    if not project_dir:
        raise RuntimeError("PROJECT_DIR is required")
    timeline_name = global_str("TIMELINE_NAME", f"{project_dir.name}_v001")
    expected_project = global_str("EXPECTED_PROJECT", "")
    bin_name = global_str("BIN_NAME", timeline_name)
    custom_prefix = global_str("CUSTOM_PREFIX", f"{project_dir.name}:")
    bgm_plan_path = Path(global_str("BGM_PLAN", str(project_dir / "outputs/bgm/bgm_plan.actual.csv"))).expanduser()
    place_bgm = global_bool("PLACE_BGM", True)
    place_unapproved_bgm = global_bool("PLACE_UNAPPROVED_BGM", True)
    apply_changes = global_bool("APPLY", False)

    manager = resolve.GetProjectManager()
    project = manager.GetCurrentProject() if manager else None
    if not project:
        raise RuntimeError("no active Resolve project")
    if expected_project and project.GetName() != expected_project:
        raise RuntimeError(f"expected Resolve project {expected_project!r}, got {project.GetName()!r}")

    timeline_exists = timeline_name in timeline_names(project)
    if apply_changes and timeline_exists:
        raise RuntimeError(f"timeline already exists; refusing overwrite: {timeline_name}")

    ir = json.loads((project_dir / "outputs/ir/project_ir.json").read_text(encoding="utf-8"))
    timing = json.loads((project_dir / "outputs/timing/timing.json").read_text(encoding="utf-8"))
    narration_paths = [Path(item["audio_path"]).resolve() for item in timing["segments"]]
    docs_paths = [
        project_dir / "outputs/subtitles/timecoded.srt",
        project_dir / "outputs/timing/timeline.csv",
        bgm_plan_path,
    ]
    docs_paths = [path.resolve() for path in docs_paths if path.exists()]

    bgm_rows: list[dict[str, str]] = []
    bgm_paths: list[Path] = []
    if place_bgm and bgm_plan_path.exists():
        all_rows = list(csv.DictReader(bgm_plan_path.open(encoding="utf-8")))
        bgm_rows = [
            row for row in all_rows
            if place_unapproved_bgm or row.get("approved", "").strip().lower() == "yes"
        ]
        catalog_roots = [
            Path("/Users/delaxpro/Dropbox/プラッと/03_プラッとBGM"),
            Path("/Users/delaxpro/src/80_トヨタ/OrionS2_ALL/BGM解析"),
        ]
        bgm_paths = resolve_bgm_paths(bgm_rows, catalog_roots) if bgm_rows else []

    summary = {
        "project": project.GetName(),
        "timeline_name": timeline_name,
        "timeline_exists": timeline_exists,
        "dry_run": not apply_changes,
        "bin_name": bin_name,
        "narration_files": len(narration_paths),
        "bgm_files": len(bgm_paths),
        "docs": len(docs_paths),
        "duration_sec": timing["duration_sec"],
        "subtitle_track_import": "manual_or_future_step",
    }
    if not apply_changes:
        return summary

    media_pool = project.GetMediaPool()
    root = media_pool.GetRootFolder()
    base_bin = ensure_bin(media_pool, root, [bin_name])
    narration_bin = ensure_bin(media_pool, base_bin, ["01_Narration"])
    bgm_bin = ensure_bin(media_pool, base_bin, ["02_BGM"])
    docs_bin = ensure_bin(media_pool, base_bin, ["03_Subtitles_Docs"])

    narration_clips = import_paths(media_pool, root, narration_bin, narration_paths)
    bgm_clips = import_paths(media_pool, root, bgm_bin, bgm_paths) if bgm_paths else {}
    try:
        import_paths(media_pool, root, docs_bin, docs_paths)
    except Exception:
        # Resolve may ignore SRT/CSV as non-media. Files remain canonical on disk.
        pass

    timeline = media_pool.CreateEmptyTimeline(timeline_name)
    if not timeline:
        raise RuntimeError("Resolve rejected empty timeline creation")
    project.SetCurrentTimeline(timeline)
    fps = float(timeline.GetSetting("timelineFrameRate") or ir.get("fps") or 29.97)
    timeline_start = int(timeline.GetStartFrame())
    add_audio_tracks(timeline, 4)
    set_track_names(timeline)

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
    if not media_pool.AppendToTimeline(narration_items):
        raise RuntimeError("Resolve rejected narration AppendToTimeline")

    bgm_items = []
    for row, path in zip(bgm_rows, bgm_paths):
        start = parse_clock(row["start"])
        end = parse_clock(row["end"])
        source_start = float(row.get("source_start_sec") or 0)
        duration_frames = max(1, seconds_to_frame(end - start, fps))
        source_frame = seconds_to_frame(source_start, fps)
        bgm_items.append(
            {
                "mediaPoolItem": bgm_clips[str(path.resolve())],
                "startFrame": source_frame,
                "endFrame": source_frame + duration_frames,
                "recordFrame": timeline_start + seconds_to_frame(start, fps),
                "trackIndex": 4,
                "mediaType": 2,
            }
        )
    if bgm_items and not media_pool.AppendToTimeline(bgm_items):
        raise RuntimeError("Resolve rejected BGM AppendToTimeline")

    add_section_markers(timeline, timing, ir, fps, custom_prefix)
    summary.update(
        {
            "fps": fps,
            "timeline_start": timeline_start,
            "audio_track_count": timeline.GetTrackCount("audio"),
            "timeline_end_frame": timeline.GetEndFrame(),
        }
    )
    return summary


RESULT = apply(resolve)
print(json.dumps(RESULT, ensure_ascii=False, indent=2, default=str))
