#!/usr/bin/env python3
"""Build an EP039 timeline with recalculated record TC including NA clips.

The source TC remains the contract for A1/A2 material. The record TC is
recomputed from zero by summing kept interview ranges and generated narration
WAV durations in script order. Run via davinci-resolve resolve_cli.py.
"""

from __future__ import annotations

import json
import wave
from pathlib import Path
from typing import Any


CUSTOM_DATA_PREFIX = "ep039-recalc-na-v0:"


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


def load_ir(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "doc_to_davinci_desired_timeline_ir.v0":
        raise RuntimeError(f"unsupported IR schema: {data.get('schema')!r}")
    return data


def import_na_media(media_pool: Any, na_dir: Path) -> dict[str, Any]:
    paths = [str(path) for path in sorted(na_dir.glob("NA*.wav"))]
    if paths:
        media_pool.ImportMedia(paths)
    clips: dict[str, Any] = {}
    root = media_pool.GetRootFolder()
    for path in paths:
        name = Path(path).name
        found = find_clip(root, name)
        if found:
            clips[Path(name).stem] = found
    return clips


def keep_ranges_from_reference(reference_timeline: Any) -> list[tuple[int, int]]:
    items = reference_timeline.GetItemListInTrack("audio", 1) or []
    ranges: list[tuple[int, int]] = []
    for item in items:
        start = int(item.GetSourceStartFrame())
        end = int(item.GetSourceEndFrame())
        if end > start:
            ranges.append((start, end))
    ranges.sort()
    return ranges


def na_events_from_ir(ir: dict[str, Any], na_dir: Path, fps: float) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    last_out: int | None = None
    for index, entry in enumerate(ir.get("entries", [])):
        source_out = entry.get("source_out_frame")
        if source_out is not None:
            last_out = int(source_out)

        speaker = str(entry.get("speaker") or "")
        if not speaker.startswith("NA"):
            continue

        next_in: int | None = None
        for later in ir.get("entries", [])[index + 1 :]:
            value = later.get("source_in_frame")
            if value is not None:
                next_in = int(value)
                break

        wav_path = na_dir / f"{speaker}.wav"
        duration = wav_duration_frames(wav_path, fps) if wav_path.exists() else None
        anchor = last_out if last_out is not None else (next_in or 0)
        events.append(
            {
                "type": "NA",
                "speaker": speaker,
                "doc_row_id": entry.get("doc_row_id"),
                "source_anchor_frame": int(anchor),
                "next_source_in_frame": next_in,
                "duration_frames": duration,
                "wav_path": str(wav_path),
                "transcript": entry.get("transcript", ""),
                "missing_wav": duration is None,
            }
        )
    return events


def build_recalculated_plan(
    keep_ranges: list[tuple[int, int]],
    na_events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    source_events: list[dict[str, Any]] = []
    for index, (start, end) in enumerate(keep_ranges, start=1):
        source_events.append(
            {
                "type": "KEEP",
                "keep_index": index,
                "source_in_frame": start,
                "source_out_frame": end,
                "source_anchor_frame": start,
                "duration_frames": end - start,
            }
        )
    source_events.extend(event for event in na_events if not event.get("missing_wav"))

    def sort_key(event: dict[str, Any]) -> tuple[int, int, int]:
        anchor = int(event["source_anchor_frame"])
        # If an NA and KEEP share the same source boundary, place NA first.
        kind_order = 0 if event["type"] == "NA" else 1
        keep_index = int(event.get("keep_index") or 0)
        return (anchor, kind_order, keep_index)

    record_cursor = 0
    plan = []
    for event in sorted(source_events, key=sort_key):
        duration = int(event["duration_frames"])
        planned = dict(event)
        planned["record_start_frame"] = record_cursor
        planned["record_end_frame"] = record_cursor + duration
        record_cursor += duration
        plan.append(planned)
    return plan


def tc_from_offset(timeline_start: int, offset: int, fps: float) -> str:
    total = timeline_start + offset
    fps_i = int(round(fps))
    hh = total // (3600 * fps_i)
    rem = total % (3600 * fps_i)
    mm = rem // (60 * fps_i)
    rem %= 60 * fps_i
    ss = rem // fps_i
    ff = rem % fps_i
    return f"{hh:02d}:{mm:02d}:{ss:02d}:{ff:02d}"


def apply(resolve: Any) -> dict[str, Any]:
    source_name = str(globals().get("SOURCE_TIMELINE", "039編集_0619"))
    reference_name = str(globals().get("REFERENCE_TIMELINE", "039編集_0619 自動カット済み"))
    output_name = str(globals().get("OUTPUT_TIMELINE", "039編集_0619_NA込み再計算"))
    ir_path = Path(str(globals().get("IR_JSON", "output/ep039_auto_cut_2/desired_timeline_ir_24fps.json"))).expanduser()
    na_dir = Path(str(globals().get("NA_DIR", "output/ep039_auto_cut_2/na_wav"))).expanduser()
    report_json = str(globals().get("REPORT_JSON", "") or "")
    mapping_csv = str(globals().get("MAPPING_CSV", "") or "")
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
    keep_ranges = keep_ranges_from_reference(reference)
    ir = load_ir(ir_path)
    na_events = na_events_from_ir(ir, na_dir, fps)
    plan = build_recalculated_plan(keep_ranges, na_events)
    missing_na = [event for event in na_events if event.get("missing_wav")]
    final_duration = max((int(item["record_end_frame"]) for item in plan), default=0)

    mapping_rows = []
    for item in plan:
        row = {
            "type": item["type"],
            "name": item.get("speaker") or f"KEEP{item.get('keep_index')}",
            "source_in_frame": item.get("source_in_frame"),
            "source_out_frame": item.get("source_out_frame"),
            "source_anchor_frame": item.get("source_anchor_frame"),
            "record_start_frame": item["record_start_frame"],
            "record_end_frame": item["record_end_frame"],
            "record_start_tc": tc_from_offset(timeline_start, int(item["record_start_frame"]), fps),
            "record_end_tc": tc_from_offset(timeline_start, int(item["record_end_frame"]), fps),
            "duration_frames": item["duration_frames"],
            "doc_row_id": item.get("doc_row_id"),
        }
        mapping_rows.append(row)

    summary: dict[str, Any] = {
        "source_timeline": source_name,
        "reference_timeline": reference_name,
        "output_timeline": output_name,
        "fps": fps,
        "timeline_start": timeline_start,
        "keep_ranges": len(keep_ranges),
        "keep_frames": sum(end - start for start, end in keep_ranges),
        "na_items": len(na_events),
        "na_missing_wav": len(missing_na),
        "plan_items": len(plan),
        "final_duration_frames": final_duration,
        "final_duration_seconds": round(final_duration / fps, 3) if fps else None,
        "final_end_tc": tc_from_offset(timeline_start, final_duration, fps),
        "dry_run": dry_run,
        "first_plan_items": mapping_rows[:12],
        "last_plan_items": mapping_rows[-8:],
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
    na_clips = import_na_media(media_pool, na_dir)

    batch1 = []
    batch2 = []
    na_batches = []
    for item in plan:
        record = timeline_start + int(item["record_start_frame"])
        duration = int(item["duration_frames"])
        if item["type"] == "KEEP":
            common = {
                "startFrame": int(item["source_in_frame"]),
                "endFrame": int(item["source_out_frame"]),
                "recordFrame": record,
                "mediaType": 2,
            }
            batch1.append({"mediaPoolItem": tr1, "trackIndex": 1, **common})
            batch2.append({"mediaPoolItem": tr2, "trackIndex": 2, **common})
        else:
            clip = na_clips.get(str(item["speaker"]))
            if not clip:
                raise RuntimeError(f"NA clip not found in media pool: {item['speaker']}")
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

    result1 = media_pool.AppendToTimeline(batch1)
    result2 = media_pool.AppendToTimeline(batch2)
    na_result = media_pool.AppendToTimeline(na_batches)
    if batch1 and (not result1 or len(result1) != len(batch1)):
        raise RuntimeError(f"A1 append failed: expected {len(batch1)}, got {0 if not result1 else len(result1)}")
    if batch2 and (not result2 or len(result2) != len(batch2)):
        raise RuntimeError(f"A2 append failed: expected {len(batch2)}, got {0 if not result2 else len(result2)}")
    if na_batches and (not na_result or len(na_result) != len(na_batches)):
        raise RuntimeError(f"NA append failed: expected {len(na_batches)}, got {0 if not na_result else len(na_result)}")

    for item in plan:
        frame = timeline_start + int(item["record_start_frame"])
        duration = max(1, int(item["duration_frames"]))
        if item["type"] == "NA":
            name = str(item["speaker"])
            note = str(item.get("transcript") or "")
            color = "Cyan"
            custom = f"{CUSTOM_DATA_PREFIX}{item.get('doc_row_id') or name}"
        else:
            name = f"KEEP{item.get('keep_index')}"
            note = f"source {item['source_in_frame']}->{item['source_out_frame']}"
            color = "Green"
            custom = f"{CUSTOM_DATA_PREFIX}keep-{item.get('keep_index')}"
        target.AddMarker(frame, color, name, note, duration, custom)

    if report_json:
        Path(report_json).expanduser().write_text(json.dumps({**summary, "plan": mapping_rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    if mapping_csv:
        import csv

        with Path(mapping_csv).expanduser().open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(mapping_rows[0].keys()))
            writer.writeheader()
            writer.writerows(mapping_rows)

    summary.update(
        {
            "ok": True,
            "deleted": deleted,
            "a1_appended": len(result1 or []),
            "a2_appended": len(result2 or []),
            "na_appended": len(na_result or []),
            "markers_added": len(plan),
        }
    )
    return summary


def main() -> None:
    if "resolve" not in globals():
        raise RuntimeError("resolve global is required")
    print(json.dumps(apply(globals()["resolve"]), ensure_ascii=False, indent=2))


main()
