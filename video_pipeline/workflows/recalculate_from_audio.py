#!/usr/bin/env python3
"""Recalculate narrated VTR timing from generated audio durations."""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
from pathlib import Path
from typing import Iterable


def audio_duration_sec(path: Path) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip())
    return float(proc.stdout.strip())


def clock(seconds: float, sep: str = ".") -> str:
    ms = int(round((seconds - int(seconds)) * 1000))
    total = int(seconds)
    hours = total // 3600
    minutes = (total % 3600) // 60
    secs = total % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}{sep}{ms:03d}"


def write_srt(path: Path, segments: list[dict]) -> None:
    lines: list[str] = []
    for index, segment in enumerate(segments, start=1):
        lines.append(str(index))
        lines.append(f"{clock(segment['actual_start_sec'], ',')} --> {clock(segment['actual_end_sec'], ',')}")
        lines.append(segment["text"])
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_timeline_csv(path: Path, segments: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        "segment_id",
        "audio_filename",
        "start",
        "end",
        "duration_sec",
        "section_id",
        "text",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for segment in segments:
            writer.writerow(
                {
                    "segment_id": segment["segment_id"],
                    "audio_filename": Path(segment["audio_path"]).name,
                    "start": clock(segment["actual_start_sec"]),
                    "end": clock(segment["actual_end_sec"]),
                    "duration_sec": f"{segment['actual_duration_sec']:.3f}",
                    "section_id": segment["section_id"],
                    "text": segment["text"],
                }
            )


def recalculate(project_dir: Path, project_id: str, audio_dir: Path) -> dict:
    ir_path = project_dir / "outputs/ir/project_ir.json"
    ir = json.loads(ir_path.read_text(encoding="utf-8"))
    segments = [segment for section in ir["sections"] for segment in section["narration"]]
    cursor = 0.0
    actual_segments: list[dict] = []
    missing: list[str] = []

    for index, segment in enumerate(segments, start=1):
        audio_path = audio_dir / f"{project_id}_{index:03d}.mp3"
        if not audio_path.exists():
            missing.append(str(audio_path))
            continue
        duration = audio_duration_sec(audio_path)
        actual = dict(segment)
        actual["audio_path"] = str(audio_path)
        actual["actual_start_sec"] = cursor
        actual["actual_duration_sec"] = duration
        actual["actual_end_sec"] = cursor + duration
        actual_segments.append(actual)
        cursor = actual["actual_end_sec"] + float(segment.get("pause_after_sec", 0.35))

    if missing:
        raise SystemExit("Missing audio files:\n" + "\n".join(missing[:20]))

    recalculated = {
        "schema": "delax_video_recalculated_timing.v0",
        "project_id": project_id,
        "source_ir": str(ir_path),
        "audio_dir": str(audio_dir),
        "duration_sec": cursor,
        "segments": actual_segments,
    }
    out_dir = project_dir / "outputs/timing"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "timing.json").write_text(
        json.dumps(recalculated, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_srt(project_dir / "outputs/subtitles/timecoded.srt", actual_segments)
    write_timeline_csv(project_dir / "outputs/timing/timeline.csv", actual_segments)

    resolve_plan = json.loads((project_dir / "outputs/resolve/resolve_apply_plan.json").read_text(encoding="utf-8"))
    resolve_plan["timeline"]["estimated_duration_sec"] = cursor
    resolve_plan["operations"] = [
        op for op in resolve_plan["operations"] if op.get("op") != "place_narration_clip"
    ] + [
        {
            "op": "place_narration_clip",
            "segment_id": segment["segment_id"],
            "record_start_sec": segment["actual_start_sec"],
            "record_end_sec": segment["actual_end_sec"],
            "audio_path": segment["audio_path"],
            "text": segment["text"],
        }
        for segment in actual_segments
    ]
    (project_dir / "outputs/resolve/resolve_apply_plan.actual.json").write_text(
        json.dumps(resolve_plan, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return recalculated


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Recalculate timing from generated narration audio.")
    parser.add_argument("--project-dir", required=True, type=Path)
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--audio-dir", required=True, type=Path)
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    result = recalculate(args.project_dir, args.project_id, args.audio_dir)
    print(f"Recalculated duration: {result['duration_sec']:.3f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

