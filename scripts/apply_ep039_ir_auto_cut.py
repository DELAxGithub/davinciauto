#!/usr/bin/env python3
"""Apply EP039 Doc-to-DaVinci IR as an auto-cut Resolve timeline.

Run through resolve_cli.py run-script. This is project-specific and intentionally
guarded: it duplicates the source timeline, rebuilds A1/A2 from IR placement
ranges, optionally places generated NA WAVs on A3, and adds review markers.
"""

from __future__ import annotations

import json
import wave
from pathlib import Path
from typing import Any


CUSTOM_DATA_PREFIX = "doc-to-davinci-v0:"


def load_ir(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "doc_to_davinci_desired_timeline_ir.v0":
        raise RuntimeError(f"unsupported IR schema: {data.get('schema')!r}")
    return data


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
        seconds = handle.getnframes() / handle.getframerate()
    return max(1, int(round(seconds * fps)))


def existing_generated_marker_count(timeline: Any) -> int:
    markers = timeline.GetMarkers() or {}
    total = 0
    for marker in markers.values():
        if isinstance(marker, dict) and str(marker.get("customData") or "").startswith(CUSTOM_DATA_PREFIX):
            total += 1
    return total


def delete_audio_track(timeline: Any, track_index: int) -> int:
    items = timeline.GetItemListInTrack("audio", track_index) or []
    if not items:
        return 0
    ok = timeline.DeleteClips(items, False)
    if not ok:
        raise RuntimeError(f"failed to delete audio track {track_index}")
    return len(items)


def import_na_media(media_pool: Any, na_dir: Path) -> dict[str, Any]:
    paths = [str(path) for path in sorted(na_dir.glob("NA*.wav"))]
    if not paths:
        return {}
    imported = media_pool.ImportMedia(paths) or []
    clips = {}
    for item in imported:
        if item:
            clips[Path(item.GetName()).stem] = item
    # ImportMedia may return existing/renamed items inconsistently, so search too.
    root = media_pool.GetRootFolder()
    for path in paths:
        stem = Path(path).stem
        found = find_clip(root, Path(path).name)
        if found:
            clips[stem] = found
    return clips


def build_na_batches(ir: dict[str, Any], na_clips: dict[str, Any], na_dir: Path, fps: float, timeline_start: int) -> list[dict[str, Any]]:
    batches = []
    record_cursor = 0
    for entry in ir.get("entries", []):
        action = entry.get("action")
        duration = entry.get("duration_frames")
        if action in {"KEEP", "RESTORE"} and duration:
            record_cursor += int(duration)
            continue
        speaker = str(entry.get("speaker") or "")
        if not speaker.startswith("NA"):
            continue
        clip = na_clips.get(speaker)
        wav_path = na_dir / f"{speaker}.wav"
        if not clip or not wav_path.exists():
            continue
        duration_frames = wav_duration_frames(wav_path, fps)
        batches.append(
            {
                "mediaPoolItem": clip,
                "startFrame": 0,
                "endFrame": duration_frames,
                "recordFrame": timeline_start + record_cursor,
                "trackIndex": 3,
                "mediaType": 2,
            }
        )
    return batches


def apply(
    resolve: Any,
    ir_path: Path,
    source_name: str,
    output_name: str,
    na_dir: Path | None,
    dry_run: bool,
    use_existing_target: bool,
) -> dict[str, Any]:
    ir = load_ir(ir_path)
    ir_fps = float(ir["fps"])
    placements = ir.get("placement_plan", [])
    markers = ir.get("marker_plan", [])

    manager = resolve.GetProjectManager()
    project = manager.GetCurrentProject() if manager else None
    if not project:
        raise RuntimeError("no active Resolve project")
    media_pool = project.GetMediaPool()
    source = find_timeline(project, source_name)
    if not source:
        raise RuntimeError(f"source timeline not found: {source_name}")

    output_exists = output_name in timeline_names(project)
    if output_exists and not use_existing_target:
        raise RuntimeError(f"output timeline already exists; refusing overwrite: {output_name}")

    timeline_fps = float(source.GetSetting("timelineFrameRate") or 0)
    timeline_start = int(source.GetStartFrame())
    fps_warning = None
    if round(timeline_fps, 3) != round(ir_fps, 3):
        fps_warning = f"IR fps {ir_fps} != Resolve timeline fps {timeline_fps}; refusing apply until confirmed"

    summary = {
        "source_timeline": source_name,
        "output_timeline": output_name,
        "ir_fps": ir_fps,
        "resolve_timeline_fps": timeline_fps,
        "timeline_start": timeline_start,
        "placement_ops": len(placements),
        "marker_ops": len(markers),
        "na_dir": str(na_dir) if na_dir else None,
        "target_exists": output_exists,
        "use_existing_target": use_existing_target,
        "fps_warning": fps_warning,
        "dry_run": dry_run,
    }
    if dry_run or fps_warning:
        return summary

    if use_existing_target:
        target = find_timeline(project, output_name)
        if not target:
            raise RuntimeError(f"target timeline not found: {output_name}")
    else:
        target = source.DuplicateTimeline(output_name)
        if not target:
            raise RuntimeError("Resolve rejected timeline duplication")
    project.SetCurrentTimeline(target)
    if existing_generated_marker_count(target):
        raise RuntimeError("target already has generated markers after duplication; refusing")

    tr1_name = str(globals().get("TR1_CLIP", "260605_001_Tr1.WAV"))
    tr2_name = str(globals().get("TR2_CLIP", "260605_001_Tr2.WAV"))
    tr1 = find_clip(media_pool.GetRootFolder(), tr1_name)
    tr2 = find_clip(media_pool.GetRootFolder(), tr2_name)
    if not tr1 or not tr2:
        raise RuntimeError(f"source WAV clips not found: {tr1_name}={bool(tr1)}, {tr2_name}={bool(tr2)}")

    deleted = {f"A{track}": delete_audio_track(target, track) for track in (1, 2)}
    if na_dir:
        deleted["A3"] = delete_audio_track(target, 3)

    batch1 = []
    batch2 = []
    for item in placements:
        start = int(item["source_in_frame"])
        duration = int(item["duration_frames"])
        record = timeline_start + int(item["record_start_frame"])
        common = {
            "startFrame": start,
            "endFrame": start + duration,
            "recordFrame": record,
            "mediaType": 2,
        }
        batch1.append({"mediaPoolItem": tr1, "trackIndex": 1, **common})
        batch2.append({"mediaPoolItem": tr2, "trackIndex": 2, **common})

    result1 = media_pool.AppendToTimeline(batch1)
    result2 = media_pool.AppendToTimeline(batch2)
    if batch1 and (not result1 or len(result1) != len(batch1)):
        raise RuntimeError(f"A1 append failed: expected {len(batch1)}, got {0 if not result1 else len(result1)}")
    if batch2 and (not result2 or len(result2) != len(batch2)):
        raise RuntimeError(f"A2 append failed: expected {len(batch2)}, got {0 if not result2 else len(result2)}")

    na_appended = 0
    if na_dir:
        na_clips = import_na_media(media_pool, na_dir)
        na_batches = build_na_batches(ir, na_clips, na_dir, ir_fps, timeline_start)
        na_result = media_pool.AppendToTimeline(na_batches)
        if na_batches and (not na_result or len(na_result) != len(na_batches)):
            raise RuntimeError(f"NA append failed: expected {len(na_batches)}, got {0 if not na_result else len(na_result)}")
        na_appended = len(na_result or [])

    placement_by_id = {str(item.get("doc_row_id")): item for item in placements}
    added_markers = 0
    skipped_unplaced_markers = 0
    for marker in markers:
        placement = placement_by_id.get(str(marker.get("doc_row_id")))
        if not placement:
            skipped_unplaced_markers += 1
            continue
        frame = timeline_start + int(placement["record_start_frame"])
        duration = max(1, int(placement.get("duration_frames") or marker.get("duration_frames") or 1))
        name = f"{marker.get('action', 'DOC')} {marker.get('doc_row_id', '')}".strip()
        ok = target.AddMarker(
            frame,
            marker.get("color", "Yellow"),
            name,
            str(marker.get("note") or ""),
            duration,
            f"{CUSTOM_DATA_PREFIX}{marker.get('doc_row_id', added_markers)}",
        )
        if not ok:
            raise RuntimeError(f"Resolve rejected marker: {marker.get('doc_row_id')}")
        added_markers += 1

    summary.update(
        {
            "ok": True,
            "deleted": deleted,
            "a1_appended": len(result1 or []),
            "a2_appended": len(result2 or []),
            "na_appended": na_appended,
            "markers_added": added_markers,
            "skipped_unplaced_markers": skipped_unplaced_markers,
        }
    )
    return summary


def print_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, default=str))


def resolve_script_entry() -> None:
    ir_path = Path(globals().get("IR_JSON", "")).expanduser()
    if not ir_path:
        raise RuntimeError("IR_JSON global is required")
    source = str(globals().get("SOURCE_TIMELINE", "039編集_0619"))
    output = str(globals().get("OUTPUT_TIMELINE", "039編集_0619_自動カット２回目"))
    na_dir_raw = str(globals().get("NA_DIR", "") or "")
    na_dir = Path(na_dir_raw).expanduser() if na_dir_raw else None
    dry_run = not bool(globals().get("APPLY", False))
    use_existing_target = bool(globals().get("USE_EXISTING_TARGET", False))
    if "resolve" not in globals():
        raise RuntimeError("resolve global is required")
    print_json(apply(globals()["resolve"], ir_path, source, output, na_dir, dry_run, use_existing_target))


if "IR_JSON" in globals():
    resolve_script_entry()
