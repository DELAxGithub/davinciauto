#!/usr/bin/env python3
"""Build an EP039 non-compacted NA experiment timeline in Resolve.

This script is intended to be run via the davinci-resolve resolve_cli.py
run-script command. It uses the known-good compact cut timeline only as a source
of keep ranges, then places those ranges back at their original source TC
positions on a duplicate of the original timeline. Generated NA WAV files are
placed on A3 without ripple-compacting the interview audio.
"""

from __future__ import annotations

import json
import wave
from pathlib import Path
from typing import Any


CUSTOM_DATA_PREFIX = "ep039-noncompact-na-v0:"


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


def delete_audio_track(timeline: Any, track_index: int) -> int:
    items = timeline.GetItemListInTrack("audio", track_index) or []
    if not items:
        return 0
    ok = timeline.DeleteClips(items, False)
    if not ok:
        raise RuntimeError(f"failed to delete audio track {track_index}")
    return len(items)


def wav_duration_frames(path: Path, fps: float) -> int:
    with wave.open(str(path), "rb") as handle:
        seconds = handle.getnframes() / handle.getframerate()
    return max(1, int(round(seconds * fps)))


def import_na_media(media_pool: Any, na_dir: Path) -> dict[str, Any]:
    paths = [str(path) for path in sorted(na_dir.glob("NA*.wav"))]
    if not paths:
        return {}
    media_pool.ImportMedia(paths)
    clips: dict[str, Any] = {}
    root = media_pool.GetRootFolder()
    for path in paths:
        name = Path(path).name
        found = find_clip(root, name)
        if found:
            clips[Path(name).stem] = found
    return clips


def load_ir(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "doc_to_davinci_desired_timeline_ir.v0":
        raise RuntimeError(f"unsupported IR schema: {data.get('schema')!r}")
    return data


def keep_ranges_from_reference(reference_timeline: Any) -> list[tuple[int, int]]:
    items = reference_timeline.GetItemListInTrack("audio", 1) or []
    ranges = []
    for item in items:
        start = int(item.GetSourceStartFrame())
        end = int(item.GetSourceEndFrame())
        if end > start:
            ranges.append((start, end))
    ranges.sort()
    return ranges


def gaps_from_keep_ranges(keep_ranges: list[tuple[int, int]], source_duration: int) -> list[tuple[int, int]]:
    gaps = []
    cursor = 0
    for start, end in keep_ranges:
        if start > cursor:
            gaps.append((cursor, start))
        cursor = max(cursor, end)
    if cursor < source_duration:
        gaps.append((cursor, source_duration))
    return gaps


def choose_gap(gaps: list[tuple[int, int]], anchor: int) -> tuple[int, int] | None:
    for start, end in gaps:
        if start <= anchor < end:
            return (start, end)
    for start, end in gaps:
        if start >= anchor:
            return (start, end)
    return gaps[-1] if gaps else None


def na_plan_from_ir(
    ir: dict[str, Any],
    na_dir: Path,
    fps: float,
    keep_ranges: list[tuple[int, int]],
    source_duration: int,
) -> list[dict[str, Any]]:
    entries = ir.get("entries", [])
    gaps = gaps_from_keep_ranges(keep_ranges, source_duration)
    plan: list[dict[str, Any]] = []
    last_out: int | None = None
    for index, entry in enumerate(entries):
        source_out = entry.get("source_out_frame")
        if source_out is not None:
            last_out = int(source_out)

        speaker = str(entry.get("speaker") or "")
        if not speaker.startswith("NA"):
            continue

        next_in: int | None = None
        for later in entries[index + 1 :]:
            value = later.get("source_in_frame")
            if value is not None:
                next_in = int(value)
                break

        wav_path = na_dir / f"{speaker}.wav"
        if not wav_path.exists():
            plan.append(
                {
                    "speaker": speaker,
                    "doc_row_id": entry.get("doc_row_id"),
                    "status": "missing_wav",
                    "wav": str(wav_path),
                }
            )
            continue

        duration = wav_duration_frames(wav_path, fps)
        anchor = last_out if last_out is not None else (next_in or 0)
        chosen_gap = choose_gap(gaps, int(anchor))
        if chosen_gap:
            gap_start, gap_end = chosen_gap
            if gap_end - gap_start >= duration:
                record_offset = max(gap_start, min(int(anchor), gap_end - duration))
            else:
                record_offset = gap_start
            gap_remaining = gap_end - record_offset
        else:
            gap_start = gap_end = int(anchor)
            record_offset = int(anchor)
            gap_remaining = None
        plan.append(
            {
                "speaker": speaker,
                "doc_row_id": entry.get("doc_row_id"),
                "raw_anchor_frame": int(anchor),
                "record_offset_frame": int(record_offset),
                "duration_frames": duration,
                "chosen_gap_start_frame": gap_start,
                "chosen_gap_end_frame": gap_end,
                "chosen_gap_frames": gap_end - gap_start,
                "gap_remaining_frames": gap_remaining,
                "next_source_in_frame": next_in,
                "overflows_chosen_gap": bool(gap_remaining is not None and duration > gap_remaining),
                "transcript": entry.get("transcript", ""),
            }
        )
    return plan


def apply(resolve: Any) -> dict[str, Any]:
    source_name = str(globals().get("SOURCE_TIMELINE", "039編集_0619"))
    reference_name = str(globals().get("REFERENCE_TIMELINE", "039編集_0619 自動カット済み"))
    output_name = str(globals().get("OUTPUT_TIMELINE", "039編集_0619_非詰めNA実験"))
    ir_path = Path(str(globals().get("IR_JSON", "output/ep039_auto_cut_2/desired_timeline_ir_24fps.json"))).expanduser()
    na_dir = Path(str(globals().get("NA_DIR", "output/ep039_auto_cut_2/na_wav"))).expanduser()
    report_json = str(globals().get("REPORT_JSON", "") or "")
    dry_run = not bool(globals().get("APPLY", False))
    tr1_name = str(globals().get("TR1_CLIP", "260605_001_Tr1.WAV"))
    tr2_name = str(globals().get("TR2_CLIP", "260605_001_Tr2.WAV"))

    manager = resolve.GetProjectManager()
    project = manager.GetCurrentProject() if manager else None
    if not project:
        raise RuntimeError("no active Resolve project")
    media_pool = project.GetMediaPool()

    source = find_timeline(project, source_name)
    reference = find_timeline(project, reference_name)
    if not source:
        raise RuntimeError(f"source timeline not found: {source_name}")
    if not reference:
        raise RuntimeError(f"reference timeline not found: {reference_name}")
    if output_name in timeline_names(project):
        raise RuntimeError(f"output timeline already exists; refusing overwrite: {output_name}")

    fps = float(source.GetSetting("timelineFrameRate") or 0)
    timeline_start = int(source.GetStartFrame())
    timeline_end = int(source.GetEndFrame())
    keep_ranges = keep_ranges_from_reference(reference)
    ir = load_ir(ir_path)
    source_duration = timeline_end - timeline_start
    na_plan = na_plan_from_ir(ir, na_dir, fps, keep_ranges, source_duration)

    summary: dict[str, Any] = {
        "source_timeline": source_name,
        "reference_timeline": reference_name,
        "output_timeline": output_name,
        "fps": fps,
        "timeline_start": timeline_start,
        "timeline_end": timeline_end,
        "source_duration_frames": source_duration,
        "keep_ranges": len(keep_ranges),
        "keep_frames": sum(end - start for start, end in keep_ranges),
        "na_items_planned": len([item for item in na_plan if item.get("duration_frames")]),
        "na_items_missing_wav": len([item for item in na_plan if item.get("status") == "missing_wav"]),
        "na_items_overflow_gap": len([item for item in na_plan if item.get("overflows_chosen_gap")]),
        "dry_run": dry_run,
        "na_plan": na_plan,
    }
    if dry_run:
        return summary

    target = source.DuplicateTimeline(output_name)
    if not target:
        raise RuntimeError("Resolve rejected timeline duplication")
    project.SetCurrentTimeline(target)

    deleted = {f"A{index}": delete_audio_track(target, index) for index in (1, 2, 3)}
    tr1 = find_clip(media_pool.GetRootFolder(), tr1_name)
    tr2 = find_clip(media_pool.GetRootFolder(), tr2_name)
    if not tr1 or not tr2:
        raise RuntimeError(f"source WAV clips not found: {tr1_name}={bool(tr1)}, {tr2_name}={bool(tr2)}")

    batch1 = []
    batch2 = []
    for start, end in keep_ranges:
        common = {
            "startFrame": start,
            "endFrame": end,
            "recordFrame": timeline_start + start,
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

    na_clips = import_na_media(media_pool, na_dir)
    na_batches = []
    for item in na_plan:
        duration = item.get("duration_frames")
        clip = na_clips.get(str(item.get("speaker")))
        if not duration or not clip:
            continue
        na_batches.append(
            {
                "mediaPoolItem": clip,
                "startFrame": 0,
                "endFrame": int(duration),
                "recordFrame": timeline_start + int(item["record_offset_frame"]),
                "trackIndex": 3,
                "mediaType": 2,
            }
        )

    na_result = media_pool.AppendToTimeline(na_batches)
    if na_batches and (not na_result or len(na_result) != len(na_batches)):
        raise RuntimeError(f"NA append failed: expected {len(na_batches)}, got {0 if not na_result else len(na_result)}")

    for item in na_plan:
        if not item.get("duration_frames"):
            continue
        frame = timeline_start + int(item["record_offset_frame"])
        target.AddMarker(
            frame,
            "Cyan",
            str(item["speaker"]),
            str(item.get("transcript") or ""),
            max(1, int(item["duration_frames"])),
            f"{CUSTOM_DATA_PREFIX}{item.get('doc_row_id') or item['speaker']}",
        )

    summary.update(
        {
            "ok": True,
            "deleted": deleted,
            "a1_appended": len(result1 or []),
            "a2_appended": len(result2 or []),
            "na_appended": len(na_result or []),
        }
    )
    if report_json:
        Path(report_json).expanduser().write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    if "resolve" not in globals():
        raise RuntimeError("resolve global is required")
    print(json.dumps(apply(globals()["resolve"]), ensure_ascii=False, indent=2))


main()
