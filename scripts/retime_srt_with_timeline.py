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
    n_c = len(cues)
    n_k = len(clips)
    out_lines: list[str] = []
    if n_c == 0 or n_k == 0:
        return out_lines

    # Strategy: distribute cues across clips proportionally
    ci = 0  # cue index
    for ki, (st, en) in enumerate(clips):
        remaining_cues = n_c - ci
        remaining_clips = n_k - ki
        if remaining_cues <= 0:
            break
        # Assign how many cues to this clip (ceil division for front-loading)
        per = (remaining_cues + remaining_clips - 1) // remaining_clips
        per = max(1, per)
        used = min(per, remaining_cues)
        dur = en - st
        if used <= 1:
            # Single cue spans whole clip
            c = cues[ci]
            idx = len(out_lines) // 3 + 1
            out_lines.append(str(idx))
            out_lines.append(f"{frames_to_tc(st,fps)} --> {frames_to_tc(en,fps)}")
            out_lines.append(c['text'] + '\n')
            ci += 1
        else:
            # Enforce minimum duration per segment
            max_segments_by_time = max(1, int((dur / fps) // MIN_CUE_SEC))
            used = max(1, min(used, max_segments_by_time))
            if used == 1:
                # Fallback to single cue
                c = cues[ci]
                idx = len(out_lines) // 3 + 1
                out_lines.append(str(idx))
                out_lines.append(f"{frames_to_tc(st,fps)} --> {frames_to_tc(en,fps)}")
                out_lines.append(c['text'] + '\n')
                ci += 1
                continue
            # Split clip into equal segments for multiple cues
            seg = dur // used
            for j in range(used):
                c = cues[ci]
                seg_st = st + seg * j
                seg_en = en if j == used - 1 else st + seg * (j + 1)
                idx = len(out_lines) // 3 + 1
                out_lines.append(str(idx))
                out_lines.append(f"{frames_to_tc(seg_st,fps)} --> {frames_to_tc(seg_en,fps)}")
                out_lines.append(c['text'] + '\n')
                ci += 1
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
