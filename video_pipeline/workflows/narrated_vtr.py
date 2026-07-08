#!/usr/bin/env python3
"""Build reviewable artifacts for narrated VTR projects.

This workflow is intentionally conservative: it creates an IR, narration text,
Gemini TTS YAML, draft subtitles, BGM cue plan, and a Resolve apply-plan stub.
Actual Resolve mutation and BGM placement remain separate approval steps.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

from video_pipeline.workflows.pronunciation import apply_pronunciation_rules, load_rules, normalize_tts_breaks


SECTION_RE = re.compile(
    r"^\s*(?:\*\*)?【(?P<time>[^｜】]+)(?:[｜|](?P<title>[^】]+))?】(?:\*\*)?\s*$"
)
TIME_RE = re.compile(r"(?P<minute>\d{1,2}):(?P<second>\d{2})(?::(?P<frame>\d{2}))?")


@dataclass
class NarrationSegment:
    segment_id: str
    section_id: str
    text: str
    estimated_start_sec: float
    estimated_end_sec: float
    pause_after_sec: float = 0.35
    speaker: str = "ナレーター"


@dataclass
class Section:
    section_id: str
    title: str
    start_sec: float
    end_sec: float | None = None
    raw_lines: list[str] = field(default_factory=list)
    narration: list[NarrationSegment] = field(default_factory=list)


@dataclass
class ProjectIR:
    schema: str
    project_id: str
    title: str
    source_script: str
    fps: float
    tts_engine: str
    bgm_catalogs: list[dict[str, str]]
    sections: list[Section]
    notes: list[str] = field(default_factory=list)


def parse_timecode(value: str) -> float:
    match = TIME_RE.search(value)
    if not match:
        raise ValueError(f"Unsupported time marker: {value}")
    minute = int(match.group("minute"))
    second = int(match.group("second"))
    return float(minute * 60 + second)


def format_clock(seconds: float) -> str:
    milliseconds = int(round((seconds - int(seconds)) * 1000))
    total = int(seconds)
    hours = total // 3600
    minutes = (total % 3600) // 60
    secs = total % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{milliseconds:03d}"


def format_srt_time(seconds: float) -> str:
    return format_clock(seconds).replace(".", ",")


def strip_markdown_emphasis(line: str) -> str:
    return line.strip().strip("*").strip()


def is_narration_line(line: str) -> bool:
    text = strip_markdown_emphasis(line)
    if not text:
        return False
    if text.startswith("#") or text.startswith("- ") or text.startswith("---"):
        return False
    if text.startswith("（") and text.endswith("）"):
        return False
    if SECTION_RE.match(text):
        return False
    if text.startswith("**") or text.endswith("**"):
        return False
    return True


def section_slug(index: int) -> str:
    return f"S{index:02d}"


def parse_script(path: Path, project_id: str, title: str, fps: float) -> ProjectIR:
    lines = path.read_text(encoding="utf-8").splitlines()
    in_narration = False
    sections: list[Section] = []
    current: Section | None = None

    for raw in lines:
        line = raw.strip()
        if line.startswith("## ナレーション全文"):
            in_narration = True
            continue
        if in_narration and line.startswith("## ") and "ナレーション全文" not in line:
            break
        if not in_narration:
            continue

        section_match = SECTION_RE.match(line)
        if section_match:
            section = Section(
                section_id=section_slug(len(sections) + 1),
                title=(section_match.group("title") or "").strip() or "Section",
                start_sec=parse_timecode(section_match.group("time")),
            )
            sections.append(section)
            current = section
            continue

        if current is not None:
            current.raw_lines.append(raw)

    if not sections:
        raise ValueError("No narration sections found. Expected headings like 【00:15｜Title】.")

    for index, section in enumerate(sections):
        if index + 1 < len(sections):
            section.end_sec = sections[index + 1].start_sec
        else:
            section.end_sec = None

    segment_counter = 1
    for section in sections:
        narration_lines = []
        for raw_line in section.raw_lines:
            text = strip_markdown_emphasis(raw_line)
            if text == "（間）":
                if narration_lines:
                    narration_lines[-1]["pause_after_sec"] = 1.2
                continue
            if is_narration_line(text):
                narration_lines.append({"text": text, "pause_after_sec": 0.35})

        section_duration = max(4.0, (section.end_sec or section.start_sec + 20.0) - section.start_sec)
        total_chars = max(1, sum(len(item["text"]) for item in narration_lines))
        cursor = section.start_sec
        for item in narration_lines:
            # Allocate by character count, keeping each subtitle readable.
            duration = max(2.2, section_duration * (len(item["text"]) / total_chars))
            segment = NarrationSegment(
                segment_id=f"NA{segment_counter:03d}",
                section_id=section.section_id,
                text=item["text"],
                estimated_start_sec=cursor,
                estimated_end_sec=min(cursor + duration, section.start_sec + section_duration),
                pause_after_sec=float(item["pause_after_sec"]),
            )
            section.narration.append(segment)
            cursor = segment.estimated_end_sec + segment.pause_after_sec
            segment_counter += 1

    return ProjectIR(
        schema="delax_video_project_ir.v0",
        project_id=project_id,
        title=title,
        source_script=str(path),
        fps=fps,
        tts_engine="gemini",
        bgm_catalogs=[
            {
                "name": "Platto",
                "catalog": "/Users/delaxpro/src/70_プラッと/platto-automation/bgm/profiles/catalog.md",
                "audio_root": "/Users/delaxpro/Dropbox/プラッと/03_プラッとBGM",
            },
            {
                "name": "Orion",
                "catalog": "/Users/delaxpro/src/80_トヨタ/OrionS2_ALL/オリオンBGMカタログ.md",
                "audio_root": "/Users/delaxpro/src/80_トヨタ/OrionS2_ALL/BGM解析",
            },
        ],
        sections=sections,
        notes=[
            "Gemini TTS is the default narration engine.",
            "BGM cue approval is separate from Resolve placement.",
            "Catalog access does not automatically imply client reuse rights.",
        ],
    )


def all_segments(ir: ProjectIR) -> list[NarrationSegment]:
    return [segment for section in ir.sections for segment in section.narration]


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def yaml_quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def write_narration(path: Path, ir: ProjectIR) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for section in ir.sections:
        lines.append(f"# {section.section_id} {section.title}")
        for segment in section.narration:
            lines.append(segment.text)
        lines.append("")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_gemini_tts_yaml(path: Path, ir: ProjectIR, rules_csv: Path | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rules = load_rules(rules_csv)
    review_rows: list[dict[str, str]] = []
    lines = ["gemini_tts:", "  segments:"]
    for index, segment in enumerate(all_segments(ir), start=1):
        text, hits = apply_pronunciation_rules(normalize_tts_breaks(segment.text), rules)
        for hit in hits:
            review_rows.append(
                {
                    "segment_index": str(index),
                    "scene": segment.section_id,
                    "surface": hit["surface"],
                    "reading": hit["reading"],
                    "count": hit["count"],
                    "note": hit["note"],
                    "original_text": segment.text,
                    "reviewed_text": text,
                }
            )
        lines.extend(
            [
                "    - speaker: ナレーター",
                "      voice: kore",
                f"      text: {yaml_quote(text)}",
                f"      display_text: {yaml_quote(segment.text)}",
                "      style_prompt: \"Speak slowly with calm, premium documentary narration; intimate, reflective, and restrained.\"",
                f"      scene: {yaml_quote(segment.section_id)}",
            ]
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    write_pronunciation_report(path.with_name("pronunciation_review.csv"), review_rows)


def write_pronunciation_report(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        "segment_index",
        "scene",
        "surface",
        "reading",
        "count",
        "note",
        "original_text",
        "reviewed_text",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def wrap_subtitle(text: str, limit: int = 22) -> list[str]:
    if len(text) <= limit:
        return [text]
    separators = ["。", "、", "——", " "]
    for sep in separators:
        idx = text.rfind(sep, 0, limit + 1)
        if idx > 3:
            left = text[: idx + (0 if sep == " " else 1)].strip()
            right = text[idx + (0 if sep == " " else 1) :].strip()
            return [left, right[:limit]]
    return [text[:limit], text[limit : limit * 2]]


def write_draft_srt(path: Path, ir: ProjectIR) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for index, segment in enumerate(all_segments(ir), start=1):
        lines.append(str(index))
        lines.append(f"{format_srt_time(segment.estimated_start_sec)} --> {format_srt_time(segment.estimated_end_sec)}")
        lines.extend(wrap_subtitle(segment.text))
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def default_bgm_candidates(ir: ProjectIR) -> list[dict[str, object]]:
    # Sparse cues by editorial act, kept unapproved until a human confirms.
    return [
        {
            "cue_id": "BGM-001",
            "start": "00:00:00.000",
            "end": "00:00:55.000",
            "track_index": 4,
            "bgm_path": "00_Original/1 - PR/02 空中庭園　リズムなし.wav",
            "source_start_sec": 0,
            "label": "Opening / cloud-sea invitation",
            "reason": "Platto catalog. Airy, open, rhythm-light cue for the fixed opening and first question.",
            "confidence": "MEDIUM",
            "approved": "no",
        },
        {
            "cue_id": "BGM-002",
            "start": "00:00:55.000",
            "end": "00:02:00.000",
            "track_index": 4,
            "bgm_path": "ANW4478_002_The-Assignment-03.wav",
            "source_start_sec": 0,
            "label": "Time as an invention",
            "reason": "Orion catalog. Quiet intellectual texture for clocks, railways, and the idea of standard time.",
            "confidence": "MEDIUM",
            "approved": "no",
        },
        {
            "cue_id": "BGM-003",
            "start": "00:02:00.000",
            "end": "00:02:40.000",
            "track_index": 4,
            "bgm_path": "ANW4149_002_Stargaze-05.wav",
            "source_start_sec": 0,
            "label": "Suspended time / landing",
            "reason": "Orion catalog. Warm skyward soundscape for the reflective landing and series close.",
            "confidence": "MEDIUM",
            "approved": "no",
        },
    ]


def write_bgm_plan(path: Path, ir: ProjectIR) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        "cue_id",
        "start",
        "end",
        "track_index",
        "bgm_path",
        "source_start_sec",
        "label",
        "reason",
        "confidence",
        "approved",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(default_bgm_candidates(ir))


def write_resolve_plan(path: Path, ir: ProjectIR) -> None:
    segments = all_segments(ir)
    plan = {
        "schema": "delax_video_resolve_apply_plan.v0",
        "project_id": ir.project_id,
        "title": ir.title,
        "safety": {
            "mutates_resolve": False,
            "requires_explicit_apply": True,
            "create_or_duplicate_timeline": True,
            "bgm_approved_rows_only": True,
        },
        "timeline": {
            "suggested_name": f"{ir.project_id}_v001",
            "fps": ir.fps,
            "tracks": {
                "V1": "picture placeholders / future shot plan",
                "A1": "Gemini TTS narration",
                "A4": "BGM approved cues",
            },
        },
        "operations": [
            {
                "op": "create_section_marker",
                "section_id": section.section_id,
                "label": section.title,
                "record_start_sec": section.start_sec,
            }
            for section in ir.sections
        ]
        + [
            {
                "op": "place_narration_clip",
                "segment_id": segment.segment_id,
                "record_start_sec": segment.estimated_start_sec,
                "record_end_sec": segment.estimated_end_sec,
                "expected_audio_name": f"{ir.project_id}_{int(segment.segment_id[2:]):03d}.mp3",
                "text": segment.text,
            }
            for segment in segments
        ],
    }
    write_json(path, plan)


def write_project_readme(path: Path, ir: ProjectIR) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# {ir.title}",
        "",
        "Generated by `video_pipeline.workflows.narrated_vtr`.",
        "",
        "## Outputs",
        "",
        "- `outputs/ir/project_ir.json`: common project IR",
        "- `outputs/narration/narration.md`: narration text for review",
        "- `outputs/tts/gemini_tts.yaml`: Gemini TTS input",
        "- `outputs/subtitles/draft.srt`: draft subtitles with estimated timing",
        "- `outputs/bgm/bgm_plan.csv`: reviewable BGM cue plan; all cues start as `approved=no`",
        "- `outputs/resolve/resolve_apply_plan.json`: non-mutating Resolve plan stub",
        "",
        "## Next Manual Gates",
        "",
        "1. Confirm rights/editorial suitability for selected BGM catalogs.",
        "2. Review subtitle splits and Gemini pronunciation hints.",
        "3. Generate narration audio, then recalculate timing from actual audio durations.",
        "4. Run Resolve/BGM placement only after approval.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build(script: Path, project_dir: Path, project_id: str, title: str, fps: float, pronunciation_rules: Path | None = None) -> None:
    ir = parse_script(script, project_id, title, fps)
    write_json(project_dir / "outputs/ir/project_ir.json", asdict(ir))
    write_narration(project_dir / "outputs/narration/narration.md", ir)
    write_gemini_tts_yaml(project_dir / "outputs/tts/gemini_tts.yaml", ir, pronunciation_rules)
    write_draft_srt(project_dir / "outputs/subtitles/draft.srt", ir)
    write_bgm_plan(project_dir / "outputs/bgm/bgm_plan.csv", ir)
    write_resolve_plan(project_dir / "outputs/resolve/resolve_apply_plan.json", ir)
    write_project_readme(project_dir / "README.md", ir)


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build narrated VTR review artifacts.")
    parser.add_argument("--script", required=True, type=Path)
    parser.add_argument("--project-dir", required=True, type=Path)
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--fps", type=float, default=29.97)
    parser.add_argument("--pronunciation-rules", type=Path)
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    build(args.script, args.project_dir, args.project_id, args.title, args.fps, args.pronunciation_rules)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
