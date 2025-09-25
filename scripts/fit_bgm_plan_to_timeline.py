#!/usr/bin/env python3
"""Sync BGM/SE plan timecodes with a narration timeline CSV."""

from __future__ import annotations

import argparse
import csv
import json
import pathlib
import re
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class Clip:
    line: int
    start: float
    end: float


def _parse_line_number(filename: str) -> Optional[int]:
    match = re.search(r"(\d{3})", filename)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def _load_timeline(path: pathlib.Path) -> List[Clip]:
    clips: List[Clip] = []
    with path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            line = _parse_line_number(pathlib.Path(row.get("filename", "")).name)
            if line is None:
                continue
            try:
                start = float(row.get("start_sec") or 0.0)
                duration = float(row.get("duration_sec") or 0.0)
            except ValueError:
                continue
            end = start + max(duration, 0.0)
            clips.append(Clip(line=line, start=start, end=end))
    clips.sort(key=lambda c: (c.start, c.line))
    return clips


def _load_plan(path: pathlib.Path) -> Dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if "sections" not in data or not isinstance(data["sections"], list):
        raise SystemExit("Plan JSON must contain a top-level 'sections' list")
    return data


def _seconds_to_tc(value: float) -> str:
    total_ms = round(max(value, 0.0) * 1000)
    hours, rem = divmod(total_ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    seconds, millis = divmod(rem, 1000)
    if millis:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def _map_clips_by_line(clips: List[Clip]) -> Dict[int, Clip]:
    return {clip.line: clip for clip in clips}


def _resolve_line(line_str: Optional[str]) -> Optional[int]:
    if not line_str:
        return None
    try:
        return int(line_str)
    except ValueError:
        try:
            return int(line_str.strip().lstrip("0") or "0")
        except ValueError:
            return None


def _section_anchor(section: Dict, clips_by_line: Dict[int, Clip], fallback_clip: Clip) -> Clip:
    start_line = _resolve_line(section.get("start_line"))
    if start_line and start_line in clips_by_line:
        return clips_by_line[start_line]
    current_tc = section.get("start_tc")
    if current_tc:
        sec = _parse_seconds(current_tc)
        if sec is not None:
            best = min(clips_by_line.values(), key=lambda c: abs(c.start - sec))
            return best
    return fallback_clip


def _parse_seconds(tc: str) -> Optional[float]:
    if not tc:
        return None
    tc = tc.strip()
    if not tc:
        return None
    parts = tc.split(":")
    try:
        if len(parts) == 3:
            hours, minutes, seconds = parts
            return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
        if len(parts) == 2:
            minutes, seconds = parts
            return int(minutes) * 60 + float(seconds)
        if len(parts) == 1:
            return float(parts[0])
    except ValueError:
        return None
    return None


def _compute_section_end(
    index: int,
    sections: List[Dict],
    clips: List[Clip],
    clips_by_line: Dict[int, Clip],
    project_end: float,
) -> tuple[float, Clip]:
    end_line = _resolve_line(sections[index].get("end_line"))
    if end_line and end_line in clips_by_line:
        clip = clips_by_line[end_line]
        return clip.end, clip
    if index + 1 < len(sections):
        next_anchor = _section_anchor(sections[index + 1], clips_by_line, clips[-1])
        target = max(next_anchor.start, clips_by_line.get(next_anchor.line, next_anchor).start)
        candidates = [c for c in clips if c.start <= target]
        clip = max(candidates, key=lambda c: c.start) if candidates else clips[0]
        return clip.end, clip
    return project_end, clips[-1]


def sync_plan(timeline_path: pathlib.Path, plan_path: pathlib.Path, output_path: pathlib.Path) -> None:
    clips = _load_timeline(timeline_path)
    if not clips:
        raise SystemExit(f"No timeline clips found in {timeline_path}")
    plan = _load_plan(plan_path)

    clips_by_line = _map_clips_by_line(clips)
    sections = plan.get("sections", [])
    project_end = clips[-1].end

    for idx, section in enumerate(sections):
        anchor = _section_anchor(section, clips_by_line, clips[0])
        section["start_line"] = f"{anchor.line:03d}"
        section["start_tc"] = _seconds_to_tc(anchor.start)

        end_sec, end_clip = _compute_section_end(idx, sections, clips, clips_by_line, project_end)
        if end_sec >= anchor.start:
            section["end_line"] = f"{end_clip.line:03d}"
            section["end_tc"] = _seconds_to_tc(end_sec)

        cues = section.get("sfx") or []
        for cue in cues:
            line_num = _resolve_line(cue.get("line_number"))
            clip = clips_by_line.get(line_num) if line_num else None
            if clip is None:
                tc_sec = _parse_seconds(cue.get("time_tc"))
                clip = min(clips, key=lambda c: abs(c.start - tc_sec)) if tc_sec is not None else anchor
            base = clip.start
            offset = cue.get("offset_sec")
            try:
                offset_val = float(offset)
            except (TypeError, ValueError):
                offset_val = 0.0
            time_sec = base + max(offset_val, 0.0)
            cue["line_number"] = f"{clip.line:03d}"
            cue["offset_sec"] = round(max(offset_val, 0.0), 3)
            cue["time_tc"] = _seconds_to_tc(time_sec)

    output_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Adjust BGM/SE plan timing to match timeline CSV")
    parser.add_argument("timeline_csv", type=pathlib.Path, help="Narration timeline CSV path")
    parser.add_argument("plan_json", type=pathlib.Path, help="BGM/SE plan JSON path")
    parser.add_argument("--out", type=pathlib.Path, help="Output path (default: overwrite plan)")
    args = parser.parse_args()

    timeline = args.timeline_csv.resolve()
    plan = args.plan_json.resolve()
    if not timeline.exists():
        raise SystemExit(f"Timeline CSV not found: {timeline}")
    if not plan.exists():
        raise SystemExit(f"Plan JSON not found: {plan}")

    out_path = args.out.resolve() if args.out else plan
    sync_plan(timeline, plan, out_path)
    print(f"WROTE: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
