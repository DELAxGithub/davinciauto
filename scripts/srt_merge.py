#!/usr/bin/env python3
"""Merge original subtitle text with narration timings while preserving structure."""
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Iterable, List, Sequence


@dataclass
class Subtitle:
    index: int
    start_time: str
    end_time: str
    text: str

    def duration_ms(self) -> int:
        return _time_to_ms(self.end_time) - _time_to_ms(self.start_time)

    def start_ms(self) -> int:
        return _time_to_ms(self.start_time)

    def end_ms(self) -> int:
        return _time_to_ms(self.end_time)

    def char_count(self) -> int:
        return len(re.sub(r"\s", "", self.text)) or 1


_TIME_RE = re.compile(r"(\d+):(\d+):(\d+),(\d+)")
_PUNCT_RE = re.compile(r"[、。，．,.！？!？\s\n「」『』（）()【】——…・※★]")


def _time_to_ms(time_str: str) -> int:
    match = _TIME_RE.match(time_str)
    if not match:
        return 0
    h, m, s, ms = map(int, match.groups())
    return h * 3_600_000 + m * 60_000 + s * 1_000 + ms


def _ms_to_time(ms: int) -> str:
    hours = ms // 3_600_000
    ms %= 3_600_000
    minutes = ms // 60_000
    ms %= 60_000
    seconds = ms // 1_000
    milliseconds = ms % 1_000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def parse_srt(content: str) -> List[Subtitle]:
    content = re.sub(r"```srt\s*", "", content)
    content = re.sub(r"```\s*$", "", content, flags=re.MULTILINE)
    blocks = re.split(r"\n\s*\n", content.strip())
    subtitles: List[Subtitle] = []
    for block in blocks:
        lines = block.strip().splitlines()
        if len(lines) < 3:
            continue
        try:
            idx = int(lines[0])
        except ValueError:
            continue
        match = re.match(r"(\d+:\d+:\d+,\d+)\s*-->\s*(\d+:\d+:\d+,\d+)", lines[1])
        if not match:
            continue
        start_time, end_time = match.groups()
        text = "\n".join(lines[2:]).strip()
        subtitles.append(Subtitle(index=idx, start_time=start_time, end_time=end_time, text=text))
    return subtitles


def write_srt(subtitles: Sequence[Subtitle], path: Path) -> None:
    lines: List[str] = []
    for idx, sub in enumerate(subtitles, start=1):
        lines.append(str(idx))
        lines.append(f"{sub.start_time} --> {sub.end_time}")
        lines.append(sub.text)
        lines.append("")
    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def _normalize(text: str) -> str:
    return _PUNCT_RE.sub("", text).lower()


def _overlap_score(timed_text: str, group: Sequence[Subtitle]) -> float:
    timed_norm = _normalize(timed_text)
    group_norm = _normalize("".join(sub.text for sub in group))
    if not timed_norm or not group_norm:
        return 0.0
    overlap = SequenceMatcher(None, timed_norm, group_norm).ratio()
    char_ratio = min(len(timed_norm), len(group_norm)) / max(len(timed_norm), len(group_norm))
    return overlap * 0.7 + char_ratio * 0.3


def _choose_group(
    originals: Sequence[Subtitle],
    timed_sub: Subtitle,
    start_idx: int,
    max_group: int = 10,
) -> List[Subtitle]:
    if start_idx >= len(originals):
        return []

    best_group: List[Subtitle] = [originals[start_idx]]
    best_score = 0.0

    for size in range(1, min(max_group, len(originals) - start_idx) + 1):
        group = list(originals[start_idx : start_idx + size])
        score = _overlap_score(timed_sub.text, group)
        combined_chars = sum(sub.char_count() for sub in group)
        if score > best_score:
            best_group = group
            best_score = score
        if combined_chars > timed_sub.char_count() * 1.5:
            break

    return best_group


def _redistribute_timings(timed_sub: Subtitle, group: Sequence[Subtitle]) -> List[Subtitle]:
    if not group:
        return []

    total_duration = max(timed_sub.duration_ms(), 1)
    counts = [sub.char_count() for sub in group]
    weight_sum = sum(counts) or len(group)

    allocations = [total_duration * count // weight_sum for count in counts]
    remainder = total_duration - sum(allocations)
    for i in range(remainder):
        allocations[i % len(allocations)] += 1

    redistributed: List[Subtitle] = []
    current = timed_sub.start_ms()
    for src, share in zip(group, allocations):
        start = current
        end = start + share
        text_lines = [ln.strip() for ln in src.text.splitlines() if ln.strip()]
        if not text_lines:
            text_lines = [src.text.strip()]
        combined = "\n".join(_limit_lines(text_lines))
        redistributed.append(
            Subtitle(
                index=0,
                start_time=_ms_to_time(start),
                end_time=_ms_to_time(end),
                text=combined,
            )
        )
        current = end

    if redistributed:
        redistributed[-1].end_time = timed_sub.end_time
    return redistributed


def merge_subtitles_default(originals: Sequence[Subtitle], timed: Sequence[Subtitle]) -> List[Subtitle]:
    merged: List[Subtitle] = []
    orig_idx = 0

    for timed_sub in timed:
        if orig_idx >= len(originals):
            break
        group = _choose_group(originals, timed_sub, orig_idx)
        redistributed = _redistribute_timings(timed_sub, group)
        merged.extend(redistributed)
        orig_idx += len(group)

    if orig_idx < len(originals) and merged:
        remaining_lines: List[str] = []
        for src in originals[orig_idx:]:
            src_lines = [ln.strip() for ln in src.text.splitlines() if ln.strip()]
            if src_lines:
                remaining_lines.extend(src_lines)
        if remaining_lines:
            combined = "\n".join(_limit_lines(remaining_lines))
            last = merged[-1]
            merged[-1] = Subtitle(
                index=last.index,
                start_time=last.start_time,
                end_time=last.end_time,
                text=f"{last.text}\n{combined}" if last.text else combined,
            )

    for i, sub in enumerate(merged, start=1):
        sub.index = i

    return merged


def merge_subtitles_balanced(originals: Sequence[Subtitle], timed: Sequence[Subtitle]) -> List[Subtitle]:
    return merge_subtitles_default(originals, timed)


def _expand_subtitles(originals: Sequence[Subtitle]) -> List[Subtitle]:
    expanded: List[Subtitle] = []
    for sub in originals:
        lines = [ln.strip() for ln in sub.text.splitlines() if ln.strip()]
        if not lines:
            expanded.append(Subtitle(index=sub.index, start_time=sub.start_time, end_time=sub.end_time, text=sub.text.strip()))
            continue
        for line in lines:
            expanded.append(
                Subtitle(
                    index=sub.index,
                    start_time=sub.start_time,
                    end_time=sub.end_time,
                    text=line,
                )
            )
    return expanded


def merge_srt_files(
    source_path: Path,
    timed_path: Path,
    output_path: Path,
    *,
    strategy: str = "default",
) -> None:
    source_subs = parse_srt(source_path.read_text(encoding="utf-8"))
    source_subs = _expand_subtitles(source_subs)
    timed_subs = parse_srt(timed_path.read_text(encoding="utf-8"))
    merged = merge_subtitles_default(source_subs, timed_subs)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_srt(merged, output_path)


def align_srt_files(
    source_path: Path,
    timed_path: Path,
    output_path: Path,
    *,
    max_lines: int = 2,
    max_span: int = 8,
    min_score: float = 0.35,
) -> None:
    merge_srt_files(source_path, timed_path, output_path)


def _limit_lines(lines: Sequence[str], max_lines: int = 2) -> List[str]:
    filtered = [ln for ln in lines if ln.strip()]
    if not filtered:
        return [""]
    if len(filtered) <= max_lines:
        return list(filtered)
    first = filtered[0]
    second = " ".join(filtered[1:])
    return [first, second]


def _cli(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, help="Path to the original SRT")
    parser.add_argument("--timed", required=True, help="Path to the timed SRT")
    parser.add_argument("--output", required=True, help="Path to write the merged SRT")
    parser.add_argument("--strategy", choices=("default", "balanced"), default="default")
    args = parser.parse_args(list(argv) if argv is not None else None)

    merge_srt_files(Path(args.source), Path(args.timed), Path(args.output), strategy=args.strategy)


if __name__ == "__main__":
    _cli()
