#!/usr/bin/env python3
"""Generate QC and asset reports for a narrated VTR Resolve timeline."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def global_str(name: str, default: str = "") -> str:
    return str(globals().get(name, default) or default)


def find_timeline(project: Any, name: str) -> Any:
    for index in range(1, project.GetTimelineCount() + 1):
        timeline = project.GetTimelineByIndex(index)
        if timeline and timeline.GetName() == name:
            return timeline
    return None


def walk_bins(folder: Any, prefix: str = "") -> list[dict[str, Any]]:
    path = f"{prefix}/{folder.GetName()}" if prefix else folder.GetName()
    rows = [{"path": path, "name": folder.GetName(), "clips": folder.GetClipList() or []}]
    for child in folder.GetSubFolderList() or []:
        rows.extend(walk_bins(child, path))
    return rows


def clip_props(clip: Any) -> dict[str, str]:
    try:
        return dict(clip.GetClipProperty() or {})
    except Exception:
        return {}


def item_media_path(item: Any) -> str:
    media = item.GetMediaPoolItem()
    if not media:
        return ""
    return clip_props(media).get("File Path", "")


def timeline_items(timeline: Any, kind: str, track_index: int, timeline_start: int) -> list[dict[str, Any]]:
    rows = []
    for index, item in enumerate(timeline.GetItemListInTrack(kind, track_index) or [], start=1):
        start = int(item.GetStart()) - timeline_start
        end = int(item.GetEnd()) - timeline_start
        rows.append(
            {
                "track_type": kind,
                "track_index": track_index,
                "item_index": index,
                "name": item.GetName(),
                "start_frame": start,
                "end_frame": end,
                "duration_frames": end - start,
                "media_path": item_media_path(item),
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def frame_clock(frames: int, fps: float) -> str:
    seconds = frames / fps if fps else 0
    ms = int(round((seconds - int(seconds)) * 1000))
    total = int(seconds)
    return f"{total//3600:02d}:{(total%3600)//60:02d}:{total%60:02d}.{ms:03d}"


def detect_gaps(items: list[dict[str, Any]], min_frames: int = 1) -> list[dict[str, Any]]:
    gaps = []
    prev_end = 0
    for item in sorted(items, key=lambda row: row["start_frame"]):
        if int(item["start_frame"]) - prev_end >= min_frames:
            gaps.append(
                {
                    "start_frame": prev_end,
                    "end_frame": int(item["start_frame"]),
                    "duration_frames": int(item["start_frame"]) - prev_end,
                }
            )
        prev_end = max(prev_end, int(item["end_frame"]))
    return gaps


def apply(resolve: Any) -> dict[str, Any]:
    project_dir = Path(global_str("PROJECT_DIR")).expanduser().resolve()
    timeline_name = global_str("TIMELINE_NAME")
    if not project_dir or not timeline_name:
        raise RuntimeError("PROJECT_DIR and TIMELINE_NAME are required")

    manager = resolve.GetProjectManager()
    project = manager.GetCurrentProject() if manager else None
    if not project:
        raise RuntimeError("no active Resolve project")
    timeline = find_timeline(project, timeline_name)
    if not timeline:
        raise RuntimeError(f"timeline not found: {timeline_name}")
    project.SetCurrentTimeline(timeline)

    timeline_start = int(timeline.GetStartFrame())
    fps = float(timeline.GetSetting("timelineFrameRate") or 24)
    ignore_a1_gap_sec = float(global_str("IGNORE_A1_GAP_SEC", "1.5"))
    video_items = timeline_items(timeline, "video", 1, timeline_start)
    na_items = timeline_items(timeline, "audio", 1, timeline_start)
    bgm_items = timeline_items(timeline, "audio", 4, timeline_start)
    subtitle_items = timeline_items(timeline, "subtitle", 1, timeline_start)
    markers = [{"frame": int(frame), **data} for frame, data in sorted((timeline.GetMarkers() or {}).items())]

    media_pool = project.GetMediaPool()
    root = media_pool.GetRootFolder()
    asset_rows = []
    used_paths = {row["media_path"] for row in video_items + na_items + bgm_items if row["media_path"]}
    for bin_info in walk_bins(root):
        for clip in bin_info["clips"]:
            props = clip_props(clip)
            file_path = props.get("File Path", "")
            asset_rows.append(
                {
                    "asset_id": Path(file_path).stem if file_path else clip.GetName(),
                    "filename": clip.GetName(),
                    "bin_path": bin_info["path"],
                    "file_path": file_path,
                    "used_in_timeline": "yes" if file_path in used_paths else "no",
                    "notes": "",
                }
            )

    qc_dir = project_dir / "outputs/qc"
    qc_dir.mkdir(parents=True, exist_ok=True)
    write_csv(
        qc_dir / "timeline_items.csv",
        video_items + na_items + bgm_items + subtitle_items,
        ["track_type", "track_index", "item_index", "name", "start_frame", "end_frame", "duration_frames", "media_path"],
    )
    write_csv(
        qc_dir / "resolve_asset_log.csv",
        asset_rows,
        ["asset_id", "filename", "bin_path", "file_path", "used_in_timeline", "notes"],
    )
    write_csv(
        project_dir / "assets/asset_log.csv",
        asset_rows,
        ["asset_id", "filename", "bin_path", "file_path", "used_in_timeline", "notes"],
    )

    v1_gaps = detect_gaps(video_items)
    na_gaps = detect_gaps(na_items)
    review_na_gaps = [
        gap for gap in na_gaps
        if gap["duration_frames"] >= max(1, int(round(ignore_a1_gap_sec * fps)))
    ]
    issues = []
    warnings = []
    if len(na_items) != len(subtitle_items):
        issues.append(f"NA/subtitle count mismatch: {len(na_items)} vs {len(subtitle_items)}")
    if not bgm_items:
        issues.append("No BGM clips on A4")
    if v1_gaps:
        issues.append(f"V1 has {len(v1_gaps)} gap(s)")
    if review_na_gaps:
        warnings.append(f"A1 narration has {len(review_na_gaps)} gap(s) longer than {ignore_a1_gap_sec:.1f}s")
    elif na_gaps:
        warnings.append(f"A1 narration has {len(na_gaps)} short intentional pause gap(s)")

    summary = {
        "schema": "delax_video_qc_report.v0",
        "project": project.GetName(),
        "timeline": timeline_name,
        "fps": fps,
        "tracks": {
            "video_1_clips": len(video_items),
            "audio_1_na_clips": len(na_items),
            "audio_4_bgm_clips": len(bgm_items),
            "subtitle_1_clips": len(subtitle_items),
        },
        "markers": len(markers),
        "assets": {
            "total": len(asset_rows),
            "used": sum(1 for row in asset_rows if row["used_in_timeline"] == "yes"),
            "unused": sum(1 for row in asset_rows if row["used_in_timeline"] == "no"),
        },
        "gaps": {
            "v1": [
                {**gap, "start": frame_clock(gap["start_frame"], fps), "end": frame_clock(gap["end_frame"], fps)}
                for gap in v1_gaps
            ],
            "a1": [
                {**gap, "start": frame_clock(gap["start_frame"], fps), "end": frame_clock(gap["end_frame"], fps)}
                for gap in na_gaps
            ],
            "a1_review_threshold_sec": ignore_a1_gap_sec,
        },
        "issues": issues,
        "warnings": warnings,
    }
    (qc_dir / "qc_report.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md = [
        f"# QC Report: {timeline_name}",
        "",
        f"- Resolve project: `{project.GetName()}`",
        f"- FPS: {fps}",
        f"- V1 clips: {len(video_items)}",
        f"- A1 NA clips: {len(na_items)}",
        f"- A4 BGM clips: {len(bgm_items)}",
        f"- Subtitle clips: {len(subtitle_items)}",
        f"- Markers: {len(markers)}",
        f"- Assets: {summary['assets']['total']} total / {summary['assets']['used']} used / {summary['assets']['unused']} unused",
        "",
        "## Issues",
        "",
    ]
    if issues:
        md.extend([f"- {issue}" for issue in issues])
    else:
        md.append("- No blocking structural issues found.")
    md.extend(["", "## Warnings", ""])
    if warnings:
        md.extend([f"- {warning}" for warning in warnings])
    else:
        md.append("- None.")
    md.extend(["", "## Files", "", "- `timeline_items.csv`", "- `resolve_asset_log.csv`", "- `qc_report.json`"])
    (qc_dir / "qc_report.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
    return summary


RESULT = apply(resolve)
