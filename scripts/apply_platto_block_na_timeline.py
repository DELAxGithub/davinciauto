#!/usr/bin/env python3
"""Apply a block-based Platto IR to a duplicated Resolve timeline."""

from __future__ import annotations

import json
import wave
from pathlib import Path
from typing import Any


CUSTOM_DATA_PREFIX = "platto-block-na-v0:"
CLIP_COLOR_MAP = {
    "Teal": "Teal",
    "Violet": "Violet",
    "Gray": "Beige",
    "Mango": "Apricot",
    "Cerulean": "Blue",
    "Purple": "Purple",
    "Rose": "Pink",
    "Magenta": "Pink",
    "Caribbean": "Teal",
    "Iris": "Purple",
    "Blue": "Blue",
    "Forest": "Green",
    "Brown": "Brown",
    "Lavender": "Violet",
    "Tan": "Tan",
    "Yellow": "Yellow",
}


def load_ir(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "platto_block_timeline_ir.v0":
        raise RuntimeError(f"unsupported IR schema: {data.get('schema')!r}")
    return data


def find_timeline(project: Any, name: str) -> Any:
    for index in range(1, project.GetTimelineCount() + 1):
        timeline = project.GetTimelineByIndex(index)
        if timeline and timeline.GetName() == name:
            return timeline
    return None


def timeline_names(project: Any) -> set[str]:
    names = set()
    for index in range(1, project.GetTimelineCount() + 1):
        timeline = project.GetTimelineByIndex(index)
        if timeline:
            names.add(timeline.GetName())
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


def find_clip_by_path(folder: Any, path: Path) -> Any:
    target = str(path)
    for clip in folder.GetClipList() or []:
        props = clip.GetClipProperty() or {}
        if props.get("File Path") == target:
            return clip
    for sub in folder.GetSubFolderList() or []:
        found = find_clip_by_path(sub, path)
        if found:
            return found
    return None


def wav_duration_frames(path: Path, fps: float) -> int:
    with wave.open(str(path), "rb") as handle:
        return max(1, int(round((handle.getnframes() / handle.getframerate()) * fps)))


def delete_track(timeline: Any, kind: str, index: int) -> int:
    items = timeline.GetItemListInTrack(kind, index) or []
    if not items:
        return 0
    if not timeline.DeleteClips(items, False):
        raise RuntimeError(f"failed to delete {kind} track {index}")
    return len(items)


def source_segments(timeline: Any, track_index: int, timeline_start: int) -> list[dict[str, Any]]:
    segments = []
    for item in timeline.GetItemListInTrack("audio", track_index) or []:
        media = item.GetMediaPoolItem()
        if not media:
            continue
        global_start = int(item.GetStart()) - timeline_start
        global_end = int(item.GetEnd()) - timeline_start
        segments.append(
            {
                "global_start": global_start,
                "global_end": global_end,
                "source_start": int(item.GetSourceStartFrame()),
                "source_end": int(item.GetSourceEndFrame()),
                "mediaPoolItem": media,
                "name": item.GetName(),
            }
        )
    segments.sort(key=lambda item: item["global_start"])
    return segments


def convert_frames(frames: int, from_fps: float, to_fps: float) -> int:
    if round(from_fps, 3) == round(to_fps, 3):
        return int(frames)
    return int(round((int(frames) / from_fps) * to_fps))


def split_block_against_segments(
    block: dict[str, Any],
    segments: list[dict[str, Any]],
    record_base: int,
    contract_fps: float,
    timeline_fps: float,
) -> list[dict[str, Any]]:
    start = convert_frames(int(block["source_in_frame"]), contract_fps, timeline_fps)
    end = convert_frames(int(block["source_out_frame"]), contract_fps, timeline_fps)
    batches = []
    for segment in segments:
        overlap_start = max(start, int(segment["global_start"]))
        overlap_end = min(end, int(segment["global_end"]))
        if overlap_end <= overlap_start:
            continue
        local_start = int(segment["source_start"]) + convert_frames(
            overlap_start - int(segment["global_start"]),
            timeline_fps,
            contract_fps,
        )
        local_end = int(segment["source_start"]) + convert_frames(
            overlap_end - int(segment["global_start"]),
            timeline_fps,
            contract_fps,
        )
        batches.append(
            {
                "mediaPoolItem": segment["mediaPoolItem"],
                "startFrame": local_start,
                "endFrame": local_end,
                "recordFrame": record_base + (overlap_start - start),
                "mediaType": 2,
            }
        )
    covered = sum(int(item["endFrame"]) - int(item["startFrame"]) for item in batches)
    expected = int(block["source_out_frame"]) - int(block["source_in_frame"])
    if covered != expected:
        raise RuntimeError(f"block {block['event_id']} source coverage mismatch: {covered} != {expected}")
    return batches


def import_na_media(media_pool: Any, na_dir: Path) -> dict[str, Any]:
    path_objects = sorted(na_dir.glob("NA*.wav"))
    paths = [str(path) for path in path_objects]
    if paths:
        media_pool.ImportMedia(paths)
    clips = {}
    root = media_pool.GetRootFolder()
    for path in path_objects:
        name = path.name
        found = find_clip_by_path(root, path) or find_clip(root, name)
        if found:
            clips[Path(name).stem] = found
    return clips


def set_clip_color(item: Any, color: str | None) -> bool:
    if not item or not color:
        return False
    mapped = CLIP_COLOR_MAP.get(color, "Blue")
    try:
        return bool(item.SetClipColor(mapped))
    except Exception:  # noqa: BLE001
        return False


def apply(resolve: Any) -> dict[str, Any]:
    source_name = str(globals().get("SOURCE_TIMELINE", "040_オリジナル"))
    output_name = str(globals().get("OUTPUT_TIMELINE", "040_自動編集_ブロックNA"))
    ir_path = Path(str(globals().get("BLOCK_IR_JSON", ""))).expanduser()
    na_dir = Path(str(globals().get("NA_DIR", ""))).expanduser()
    report_json = str(globals().get("REPORT_JSON", "") or "")
    dry_run = not bool(globals().get("APPLY", False))

    if not ir_path:
        raise RuntimeError("BLOCK_IR_JSON global is required")
    ir = load_ir(ir_path)
    events = ir.get("events", [])

    manager = resolve.GetProjectManager()
    project = manager.GetCurrentProject() if manager else None
    if not project:
        raise RuntimeError("no active Resolve project")
    media_pool = project.GetMediaPool()
    source = find_timeline(project, source_name)
    if not source:
        raise RuntimeError(f"source timeline not found: {source_name}")
    if output_name in timeline_names(project):
        raise RuntimeError(f"output timeline already exists; refusing overwrite: {output_name}")

    timeline_fps = float(source.GetSetting("timelineFrameRate") or 0)
    contract_fps = float(globals().get("CONTRACT_FPS", 0) or ir.get("fps", 0) or timeline_fps)
    timeline_start = int(source.GetStartFrame())
    if not timeline_fps or not contract_fps:
        raise RuntimeError(f"invalid fps values: timeline={timeline_fps}, contract={contract_fps}")

    a1_segments = source_segments(source, 1, timeline_start)
    a2_segments = source_segments(source, 2, timeline_start)
    keep_events = [event for event in events if event["type"] == "KEEP_BLOCK"]
    na_events = [event for event in events if event["type"] == "NA"]
    summary = {
        "source_timeline": source_name,
        "output_timeline": output_name,
        "timeline_fps": timeline_fps,
        "contract_fps": contract_fps,
        "timeline_start": timeline_start,
        "dry_run": dry_run,
        "keep_blocks": len(keep_events),
        "na_items": len(na_events),
        "a1_source_segments": [{k: v for k, v in item.items() if k != "mediaPoolItem"} for item in a1_segments],
        "a2_source_segments": [{k: v for k, v in item.items() if k != "mediaPoolItem"} for item in a2_segments],
        "final_duration_frames": convert_frames(
            int(ir.get("summary", {}).get("final_duration_frames") or 0),
            contract_fps,
            timeline_fps,
        ),
        "final_duration_seconds": ir.get("summary", {}).get("final_duration_seconds"),
    }
    if dry_run:
        return summary

    target = source.DuplicateTimeline(output_name)
    if not target:
        raise RuntimeError("Resolve rejected timeline duplication")
    project.SetCurrentTimeline(target)
    if target.GetTrackCount("audio") < 3:
        target.AddTrack("audio")
    deleted = {}
    for track_index in range(1, int(target.GetTrackCount("audio") or 0) + 1):
        deleted[f"A{track_index}"] = delete_track(target, "audio", track_index)

    na_clips = import_na_media(media_pool, na_dir)
    batch1 = []
    batch2 = []
    block_meta1 = []
    block_meta2 = []
    na_batches = []
    na_meta = []
    for event in events:
        record = timeline_start + convert_frames(int(event["record_start_frame"]), contract_fps, timeline_fps)
        if event["type"] == "KEEP_BLOCK":
            a1_parts = split_block_against_segments(event, a1_segments, record, contract_fps, timeline_fps)
            a2_parts = split_block_against_segments(event, a2_segments, record, contract_fps, timeline_fps)
            for part in a1_parts:
                batch1.append({"trackIndex": 1, **part})
                block_meta1.append({"track": 1, "event": event})
            for part in a2_parts:
                batch2.append({"trackIndex": 2, **part})
                block_meta2.append({"track": 2, "event": event})
        elif event["type"] == "NA":
            clip = na_clips.get(str(event["speaker"]))
            wav_path = na_dir / f"{event['speaker']}.wav"
            if not clip:
                raise RuntimeError(f"NA clip not found: {event['speaker']}")
            duration = wav_duration_frames(wav_path, timeline_fps)
            na_batches.append(
                {
                    "mediaPoolItem": clip,
                    "startFrame": 0,
                    "endFrame": duration,
                    "recordFrame": record,
                    "trackIndex": 3,
                    "mediaType": 2,
                }
            )
            na_meta.append(event)

    result1 = media_pool.AppendToTimeline(batch1)
    result2 = media_pool.AppendToTimeline(batch2)
    result3 = media_pool.AppendToTimeline(na_batches)
    if batch1 and (not result1 or len(result1) != len(batch1)):
        raise RuntimeError(f"A1 append failed: expected {len(batch1)}, got {0 if not result1 else len(result1)}")
    if batch2 and (not result2 or len(result2) != len(batch2)):
        raise RuntimeError(f"A2 append failed: expected {len(batch2)}, got {0 if not result2 else len(result2)}")
    if na_batches and (not result3 or len(result3) != len(na_batches)):
        raise RuntimeError(f"A3 append failed: expected {len(na_batches)}, got {0 if not result3 else len(result3)}")

    colored = 0
    for item, meta in zip(list(result1 or []), block_meta1):
        if set_clip_color(item, meta["event"].get("color")):
            colored += 1
    for item, meta in zip(list(result2 or []), block_meta2):
        if set_clip_color(item, meta["event"].get("color")):
            colored += 1
    for item in result3 or []:
        if set_clip_color(item, "Blue"):
            colored += 1

    markers_added = 0
    for event in events:
        frame = timeline_start + convert_frames(int(event["record_start_frame"]), contract_fps, timeline_fps)
        duration = max(1, convert_frames(int(event.get("duration_frames") or 1), contract_fps, timeline_fps))
        if event["type"] == "KEEP_BLOCK":
            color = "Green"
            name = f"{event['event_id']} {event.get('color') or ''}".strip()
            note = event.get("transcript_preview", "")
        else:
            color = "Cyan"
            name = str(event["event_id"])
            note = event.get("transcript", "")
        ok = target.AddMarker(frame, color, name, note, duration, f"{CUSTOM_DATA_PREFIX}{event['event_id']}")
        if ok:
            markers_added += 1

    summary.update(
        {
            "ok": True,
            "deleted": deleted,
            "a1_appended": len(result1 or []),
            "a2_appended": len(result2 or []),
            "na_appended": len(result3 or []),
            "clip_colors_set": colored,
            "markers_added": markers_added,
        }
    )
    if report_json:
        Path(report_json).expanduser().write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    if "resolve" not in globals():
        raise RuntimeError("resolve global is required")
    print(json.dumps(apply(globals()["resolve"]), ensure_ascii=False, indent=2))


main()
