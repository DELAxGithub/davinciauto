#!/usr/bin/env python3
"""
Create SRT subtitles from our FCP7 (xmeml) XML timeline + the timeline CSV
that contains the text. Uses 30fps timebase by default.

Usage:
  python scripts/make_srt_from_xml_and_csv.py <timeline.xml> <timeline.csv> [<out.srt>]

Output default:
  projects/<Project>/テロップ類/SRT/<Project>_Sub_follow.srt
"""
from __future__ import annotations

import csv
import pathlib
import sys
import xml.etree.ElementTree as ET


FPS = 30
MAX_LINE_CHARS = 26
MAX_LINES = 2
# Splitting policy
MIN_CUE_SEC = 3.0           # Each subtitle should be at least this long
# No maximum duration cap; splitting no longer enforced by a max time
MAX_CHARS_PER_CUE = MAX_LINE_CHARS * MAX_LINES  # Rough readability target per cue


def frames_to_srt_tc(frames: int, fps: int = FPS) -> str:
    total_ms = round((frames / fps) * 1000.0)
    h = total_ms // 3600000
    m = (total_ms % 3600000) // 60000
    s = (total_ms % 60000) // 1000
    ms = total_ms % 1000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def parse_xml_clips(xml_path: pathlib.Path) -> list[dict[str, int]]:
    tree = ET.parse(xml_path)
    root = tree.getroot()
    clips: list[dict[str, int]] = []
    for clip in root.findall('.//clipitem'):
        name_el = clip.find('name')
        st_el = clip.find('start')
        en_el = clip.find('end')
        st = int(st_el.text) if st_el is not None and (st_el.text or '').isdigit() else None
        en = int(en_el.text) if en_el is not None and (en_el.text or '').isdigit() else None
        if name_el is None or st is None or en is None:
            continue
        clips.append({'name': name_el.text, 'start': st, 'end': en})
    clips.sort(key=lambda x: x['start'])
    return clips


def load_text_map(csv_path: pathlib.Path) -> dict[str, dict[str, str]]:
    m: dict[str, dict[str, str]] = {}
    with csv_path.open('r', encoding='utf-8') as f:
        r = csv.DictReader(f)
        for row in r:
            name = pathlib.Path(row['filename']).name
            m[name] = row
    return m


def smart_wrap(text: str, max_line: int = MAX_LINE_CHARS, max_lines: int = MAX_LINES) -> str:
    s = (text or '').strip()
    if not s:
        return ''
    # Prefer splits at punctuation/whitespace between Japanese phrases
    seps = ['。', '、', '！', '？', '——', '—', '・', '…', ' ', '\u3000']
    lines: list[str] = []
    cur = s
    while cur and len(lines) < max_lines:
        if len(cur) <= max_line:
            lines.append(cur)
            cur = ''
            break
        # Find best split point <= max_line
        split_at = -1
        # check punctuation near the limit going backwards
        window = cur[:max_line]
        for i in range(len(window)-1, max(0, max_line-12), -1):
            if window[i] in seps:
                split_at = i + 1
                break
        if split_at == -1:
            # no punctuation: fallback to hard wrap at max_line
            split_at = max_line
        lines.append(cur[:split_at].rstrip())
        cur = cur[split_at:].lstrip()
    if cur:
        # If text remains but exceeded max_lines, append the remainder to last line if short, else truncate with ellipsis
        if len(lines) < max_lines:
            lines.append(cur)
        else:
            # keep within readability; indicate continuation
            tail = cur[:max(0, max_line-1)].rstrip()
            if tail and tail[-1] in ['。', '！', '？']:
                lines[-1] = lines[-1]  # already ends well
            else:
                lines[-1] = (lines[-1] + ' ' + tail + '…').strip()
    return '\n'.join(lines)


def split_sentences(text: str) -> list[str]:
    s = (text or '').strip()
    if not s:
        return []
    # Keep punctuation with the sentence
    import re
    parts = re.split(r'(。|！|!|？|\?|…+|――|—)', s)
    res: list[str] = []
    buf = ''
    for i in range(0, len(parts), 2):
        chunk = parts[i]
        punc = parts[i+1] if i+1 < len(parts) else ''
        piece = (chunk + punc).strip()
        if piece:
            res.append(piece)
    if not res:
        return [s]
    return res


def chunk_text(text: str, target_segments: int) -> list[str]:
    if target_segments <= 1:
        return [text.strip()]
    sents = split_sentences(text)
    if not sents:
        sents = [text]
    total = sum(len(x) for x in sents) or 1
    target_len = total / target_segments
    groups: list[list[str]] = []
    cur: list[str] = []
    cur_len = 0
    for sent in sents:
        if not cur:
            cur = [sent]
            cur_len = len(sent)
            continue
        if cur_len + len(sent) <= target_len * 1.25 and len(groups) + 1 < target_segments:
            cur.append(sent)
            cur_len += len(sent)
        else:
            groups.append(cur)
            cur = [sent]
            cur_len = len(sent)
    if cur:
        groups.append(cur)
    # If we have fewer groups than target, try to split long groups by simple hard wrap
    while len(groups) < target_segments:
        # find the longest group
        idx = max(range(len(groups)), key=lambda i: sum(len(x) for x in groups[i]))
        text_joined = ' '.join(groups[idx])
        mid = len(text_joined) // 2
        groups[idx:idx+1] = [[text_joined[:mid].strip()], [text_joined[mid:].strip()]]
    return [''.join(g).strip() for g in groups]


def decide_segments(duration_sec: float, text: str) -> int:
    # Upper cap removed: only ensure minimum duration and optional char density
    max_by_time = max(1, int(duration_sec // MIN_CUE_SEC))
    need_by_chars = max(1, (len(text.strip()) + MAX_CHARS_PER_CUE - 1) // MAX_CHARS_PER_CUE)
    target = min(max_by_time, need_by_chars)
    return max(1, target)


def make_srt(xml_path: pathlib.Path, csv_path: pathlib.Path, out_path: pathlib.Path) -> None:
    clips = parse_xml_clips(xml_path)
    texts = load_text_map(csv_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open('w', encoding='utf-8') as w:
        idx = 1
        for c in clips:
            name = c['name']
            st_f = c['start']
            en_f = c['end']
            dur_f = max(1, en_f - st_f)
            dur_sec = dur_f / FPS
            row = texts.get(name) or {}
            role = (row.get('role') or '').strip()
            character = (row.get('character') or '').strip()
            text = (row.get('text') or name).strip()
            # Prefix character for dialogue; otherwise plain text
            if role.upper() in ('DL', 'DIALOGUE') and character and character != 'NA':
                display = f"{character}: {text}"
            else:
                display = text
            segments = decide_segments(dur_sec, display)
            chunks = chunk_text(display, segments)
            # Allocate time proportionally to chunk lengths
            lens = [max(1, len(t)) for t in chunks]
            total_len = sum(lens)
            acc = 0
            for i, t in enumerate(chunks):
                # Proportional boundaries
                start_ratio = acc / total_len
                acc += lens[i]
                end_ratio = acc / total_len
                seg_st_f = st_f + int(round(dur_f * start_ratio))
                seg_en_f = st_f + int(round(dur_f * end_ratio))
                if seg_en_f <= seg_st_f:
                    seg_en_f = seg_st_f + 1
                text_out = smart_wrap(t)
                w.write(f"{idx}\n")
                w.write(f"{frames_to_srt_tc(seg_st_f)} --> {frames_to_srt_tc(seg_en_f)}\n")
                w.write(f"{text_out}\n\n")
                idx += 1


def default_out_for(xml_path: pathlib.Path) -> pathlib.Path:
    # projects/<Project>/exports/timelines/<name>.xml -> projects/<Project>/テロップ類/SRT/<Project>_Sub_follow.srt
    parts = list(xml_path.parts)
    if 'projects' in parts:
        i = parts.index('projects')
        proj = parts[i+1] if i+1 < len(parts) else 'Project'
    else:
        proj = 'Project'
    base = pathlib.Path('projects') / proj / 'テロップ類' / 'SRT'
    return base / f"{proj}_Sub_follow.srt"


def main() -> int:
    if len(sys.argv) < 3:
        print('Usage: python scripts/make_srt_from_xml_and_csv.py <timeline.xml> <timeline.csv> [<out.srt>]', file=sys.stderr)
        return 2
    xml_path = pathlib.Path(sys.argv[1])
    csv_path = pathlib.Path(sys.argv[2])
    out_path = pathlib.Path(sys.argv[3]) if len(sys.argv) >= 4 else default_out_for(xml_path)
    make_srt(xml_path, csv_path, out_path)
    print(f'WROTE: {out_path}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
