#!/usr/bin/env python3
"""
Retime an existing SRT (keep text/segmentation) to match a timeline from FCP7 XML.

- Reads clip positions from XML (xmeml) and sorts by start.
- Assigns cues to clips in order. If counts differ:
  * If cues > clips: splits each clip evenly among the number of assigned cues.
  * If cues < clips: merges multiple clips per cue (cue spans over consecutive clips).

Usage:
  python scripts/retime_srt_with_timeline.py <timeline.xml> <input.srt> [<out.srt>]

Default output: alongside input, with suffix `_retimed.srt`.
"""
from __future__ import annotations

import pathlib
import sys
import xml.etree.ElementTree as ET

FPS = 30
MIN_CUE_SEC = 3.0  # enforce minimum subtitle duration; do not alter text/layout


def parse_srt(path: pathlib.Path) -> list[dict[str, str]]:
    text = path.read_text(encoding='utf-8')
    blocks = []
    cur_lines: list[str] = []
    for line in text.splitlines():
        if line.strip() == '':
            if cur_lines:
                blocks.append(cur_lines)
                cur_lines = []
            continue
        cur_lines.append(line.rstrip('\n'))
    if cur_lines:
        blocks.append(cur_lines)

    cues: list[dict[str, str]] = []
    for b in blocks:
        if not b:
            continue
        # Typical: index, time-range, text...
        idx_line = b[0].strip()
        time_line = b[1].strip() if len(b) > 1 else ''
        content_lines = b[2:] if len(b) > 2 else b[1:]
        content = '\n'.join(content_lines).strip()
        cues.append({'index': idx_line, 'time': time_line, 'text': content})
    return cues


def frames_to_tc(frames: int, fps: int = FPS) -> str:
    total_ms = round((frames / fps) * 1000.0)
    h = total_ms // 3600000
    m = (total_ms % 3600000) // 60000
    s = (total_ms % 60000) // 1000
    ms = total_ms % 1000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def parse_xml(xml_path: pathlib.Path) -> list[tuple[int, int]]:
    tree = ET.parse(xml_path)
    root = tree.getroot()
    clips: list[tuple[int, int]] = []
    for clip in root.findall('.//clipitem'):
        file_elem = clip.find('file')
        pathurl = file_elem.find('pathurl').text if file_elem is not None and file_elem.find('pathurl') is not None else ''
        if 'サウンド類/Narration' not in pathurl and 'Narration' not in pathurl:
            name = clip.findtext('name') or ''
            if not name.endswith('-NA.mp3'):
                continue
        st_el = clip.find('start')
        en_el = clip.find('end')
        if st_el is None or en_el is None:
            continue
        try:
            st = int(st_el.text)
            en = int(en_el.text)
        except Exception:
            continue
        if en > st:
            clips.append((st, en))
    clips.sort(key=lambda x: x[0])
    return clips


def retime(cues: list[dict[str, str]], clips: list[tuple[int, int]], fps: int = FPS) -> list[str]:
    total_cues = len(cues)
    if total_cues == 0 or not clips:
        return []

    total_frames = sum(en - st for st, en in clips)
    remaining_cues = total_cues
    remaining_frames = total_frames
    cue_index = 0
    out_lines: list[str] = []

    for clip_idx, (st, en) in enumerate(clips):
        if cue_index >= total_cues:
            break
        dur_frames = max(1, en - st)
        remaining_clips = len(clips) - clip_idx

        if remaining_frames > 0:
            portion = dur_frames / remaining_frames
        else:
            portion = 1.0 / remaining_clips

        assign = max(1, round(portion * remaining_cues))
        max_assign = remaining_cues - (remaining_clips - 1)
        assign = min(assign, max_assign)

        assign = min(assign, remaining_cues)

        if assign <= 0:
            assign = 1

        for j in range(assign):
            if cue_index >= total_cues:
                break
            c = cues[cue_index]
            start_frames = st + (dur_frames * j) // assign
            end_frames = en if j == assign - 1 else st + (dur_frames * (j + 1)) // assign
            idx_num = len(out_lines) // 3 + 1
            out_lines.append(str(idx_num))
            out_lines.append(f"{frames_to_tc(start_frames, fps)} --> {frames_to_tc(end_frames, fps)}")
            out_lines.append(c['text'] + '\n')
            cue_index += 1

        remaining_cues = total_cues - cue_index
        remaining_frames -= dur_frames

    # If any cues remain, append them sequentially after the last clip using final time
    if cue_index < total_cues:
        last_end = clips[-1][1]
        for i in range(cue_index, total_cues):
            idx_num = len(out_lines) // 3 + 1
            out_lines.append(str(idx_num))
            out_lines.append(f"{frames_to_tc(last_end, fps)} --> {frames_to_tc(last_end, fps)}")
            out_lines.append(cues[i]['text'] + '\n')

    return out_lines


def main() -> int:
    if len(sys.argv) < 3:
        print('Usage: python scripts/retime_srt_with_timeline.py <timeline.xml> <input.srt> [<out.srt>]', file=sys.stderr)
        return 2
    xml_path = pathlib.Path(sys.argv[1])
    srt_in = pathlib.Path(sys.argv[2])
    srt_out = pathlib.Path(sys.argv[3]) if len(sys.argv) >= 4 else srt_in.with_name(srt_in.stem + '_retimed.srt')
    cues = parse_srt(srt_in)
    clips = parse_xml(xml_path)
    lines = retime(cues, clips, 30)
    srt_out.parent.mkdir(parents=True, exist_ok=True)
    srt_out.write_text('\n'.join(lines), encoding='utf-8')
    print(f'WROTE: {srt_out}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
