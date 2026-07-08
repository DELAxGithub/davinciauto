#!/usr/bin/env python3
"""Create a lightweight pre-TTS script review for narrated VTR projects."""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict
from pathlib import Path
from typing import Iterable

from video_pipeline.workflows.narrated_vtr import all_segments, parse_script


def clock(seconds: float) -> str:
    total = int(round(seconds))
    return f"{total//3600:02d}:{(total%3600)//60:02d}:{total%60:02d}"


def review_script(
    script: Path,
    project_dir: Path,
    project_id: str,
    title: str,
    fps: float,
    target_duration_sec: float | None = None,
) -> dict:
    ir = parse_script(script, project_id, title, fps)
    segments = all_segments(ir)
    total_chars = sum(len(segment.text) for segment in segments)
    low_tempo_sec = (total_chars / 280.0) * 60.0 if total_chars else 0.0
    normal_tempo_sec = (total_chars / 330.0) * 60.0 if total_chars else 0.0
    long_segments = [
        {
            "segment_id": segment.segment_id,
            "section_id": segment.section_id,
            "chars": len(segment.text),
            "text": segment.text,
        }
        for segment in segments
        if len(segment.text) >= 55
    ]
    section_rows = []
    for section in ir.sections:
        section_segments = section.narration
        section_rows.append(
            {
                "section_id": section.section_id,
                "title": section.title,
                "marker_start_sec": section.start_sec,
                "marker_end_sec": section.end_sec,
                "segments": len(section_segments),
                "chars": sum(len(segment.text) for segment in section_segments),
            }
        )

    warnings: list[str] = []
    if not segments:
        warnings.append("No narration segments found.")
    if long_segments:
        warnings.append(f"{len(long_segments)} segment(s) are 55+ chars; consider splitting before TTS.")
    first_text = segments[0].text if segments else ""
    last_text = segments[-1].text if segments else ""
    if "遠く地平線の彼方" not in first_text:
        warnings.append("Fixed opening phrase was not found in the first narration segment.")
    if "今日の一冊" not in last_text:
        warnings.append("Fixed closing phrase was not found in the last narration segment.")
    if target_duration_sec:
        delta_low = low_tempo_sec - target_duration_sec
        if abs(delta_low) > 20:
            warnings.append(
                f"Estimated low-tempo duration differs from target by {delta_low:+.1f}s."
            )

    payload = {
        "schema": "delax_narrated_vtr_script_review.v0",
        "project_id": project_id,
        "title": title,
        "script": str(script),
        "fps": fps,
        "sections": len(ir.sections),
        "segments": len(segments),
        "total_chars": total_chars,
        "estimated_duration_sec": {
            "low_tempo_280_cpm": round(low_tempo_sec, 3),
            "normal_tempo_330_cpm": round(normal_tempo_sec, 3),
            "target": target_duration_sec,
        },
        "section_rows": section_rows,
        "long_segments": long_segments,
        "warnings": warnings,
    }

    out_dir = project_dir / "outputs/script_review"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "script_review.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    with (out_dir / "sections.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["section_id", "title", "marker_start_sec", "marker_end_sec", "segments", "chars"],
        )
        writer.writeheader()
        writer.writerows(section_rows)
    with (out_dir / "long_segments.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["segment_id", "section_id", "chars", "text"])
        writer.writeheader()
        writer.writerows(long_segments)

    md = [
        f"# Script Review: {title}",
        "",
        f"- Script: `{script}`",
        f"- Sections: {len(ir.sections)}",
        f"- Narration segments: {len(segments)}",
        f"- Narration chars: {total_chars}",
        f"- Estimated duration at 280 chars/min: `{clock(low_tempo_sec)}` ({low_tempo_sec:.1f}s)",
        f"- Estimated duration at 330 chars/min: `{clock(normal_tempo_sec)}` ({normal_tempo_sec:.1f}s)",
    ]
    if target_duration_sec:
        md.append(f"- Target duration: `{clock(target_duration_sec)}` ({target_duration_sec:.1f}s)")
    md.extend(["", "## Review Gates", ""])
    md.extend(
        [
            "- Narration wording approved",
            "- Required fact checks marked or resolved",
            "- Opening and closing fixed phrases approved",
            "- Pronunciation rules updated for proper nouns and ambiguous readings",
            "- TTS retake scope decided before synthesis",
        ]
    )
    md.extend(["", "## Warnings", ""])
    md.extend([f"- {warning}" for warning in warnings] or ["- None"])
    md.extend(["", "## Long Segments", ""])
    if long_segments:
        for row in long_segments:
            md.append(f"- `{row['segment_id']}` {row['chars']} chars: {row['text']}")
    else:
        md.append("- None")
    (out_dir / "script_review.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return payload


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a pre-TTS narrated VTR script review.")
    parser.add_argument("--script", required=True, type=Path)
    parser.add_argument("--project-dir", required=True, type=Path)
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--fps", type=float, default=29.97)
    parser.add_argument("--target-duration-sec", type=float)
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    payload = review_script(
        args.script,
        args.project_dir,
        args.project_id,
        args.title,
        args.fps,
        args.target_duration_sec,
    )
    print(
        "Script review complete: "
        f"sections={payload['sections']}, segments={payload['segments']}, "
        f"warnings={len(payload['warnings'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

