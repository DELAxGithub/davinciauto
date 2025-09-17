#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import os
import pathlib
import sys
import urllib.parse
import xml.etree.ElementTree as ET

FPS = 30


def sec_to_frames(sec: float, fps: int = FPS) -> int:
    return int(round(sec * fps))


def file_url(path: pathlib.Path) -> str:
    p = path.resolve()
    if os.name == 'nt':
        return 'file:///' + urllib.parse.quote(str(p).replace('\\', '/'))
    return 'file://' + urllib.parse.quote(str(p))


def mp3_estimate_duration_seconds(path: pathlib.Path, kbps: int = 128) -> float:
    try:
        size = path.stat().st_size
        return round((size * 8.0) / (kbps * 1000.0), 3)
    except Exception:
        return 0.0


def load_narration_rows(csv_path: pathlib.Path) -> list[dict[str, str]]:
    with csv_path.open('r', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def build_xmeml(name: str) -> ET.Element:
    root = ET.Element('xmeml', version='4')
    sequence = ET.SubElement(root, 'sequence')
    ET.SubElement(sequence, 'uuid').text = name
    ET.SubElement(sequence, 'duration').text = '0'
    ET.SubElement(sequence, 'name').text = name
    rate = ET.SubElement(sequence, 'rate')
    ET.SubElement(rate, 'timebase').text = str(FPS)
    ET.SubElement(rate, 'ntsc').text = 'TRUE'
    media = ET.SubElement(sequence, 'media')
    video = ET.SubElement(media, 'video')
    ET.SubElement(video, 'format')  # match working minimal structure
    audio = ET.SubElement(media, 'audio')
    return root


def ensure_audio_track(audio_elem: ET.Element, track_index: int) -> ET.Element:
    # Create tracks up to track_index (1-based logical; we just append)
    tracks = audio_elem.findall('track')
    while len(tracks) < track_index:
        ET.SubElement(audio_elem, 'track')
        tracks = audio_elem.findall('track')
    return tracks[track_index - 1]


def add_audio_clip(track: ET.Element, clip_id: int, name: str, path: pathlib.Path, start_f: int, end_f: int, in_f: int = 0, out_f: int | None = None):
    if out_f is None:
        out_f = end_f - start_f
    clipitem = ET.SubElement(track, 'clipitem')
    clipitem.set('id', f'clipitem-{clip_id}')
    clipitem.set('premiereChannelType', 'mono')
    ET.SubElement(clipitem, 'name').text = name
    ET.SubElement(clipitem, 'enabled').text = 'TRUE'
    ET.SubElement(clipitem, 'duration').text = str(out_f)
    rate = ET.SubElement(clipitem, 'rate')
    ET.SubElement(rate, 'timebase').text = str(FPS)
    ET.SubElement(rate, 'ntsc').text = 'TRUE'
    ET.SubElement(clipitem, 'start').text = str(start_f)
    ET.SubElement(clipitem, 'end').text = str(end_f)
    ET.SubElement(clipitem, 'in').text = str(in_f)
    ET.SubElement(clipitem, 'out').text = str(in_f + (end_f - start_f))
    file_elem = ET.SubElement(clipitem, 'file')
    file_elem.set('id', f'file-{clip_id}')
    ET.SubElement(file_elem, 'name').text = path.name
    ET.SubElement(file_elem, 'pathurl').text = file_url(path)
    st = ET.SubElement(clipitem, 'sourcetrack')
    ET.SubElement(st, 'mediatype').text = 'audio'
    ET.SubElement(st, 'trackindex').text = '1'


def main() -> int:
    if len(sys.argv) < 4:
        print('Usage: python scripts/build_fcpx_with_bgm_se.py <narration_csv> <bgm_se_plan.json> <out_xml>', file=sys.stderr)
        return 2
    narr_csv = pathlib.Path(sys.argv[1])
    plan_json = pathlib.Path(sys.argv[2])
    out_xml = pathlib.Path(sys.argv[3])

    rows = load_narration_rows(narr_csv)
    plan = json.loads(plan_json.read_text(encoding='utf-8'))
    project = plan.get('project') or narr_csv.parent.parent.parent.name
    project_dir = pathlib.Path('projects') / project
    bgm_dir = project_dir / 'サウンド類' / 'BGM'
    se_dir = project_dir / 'サウンド類' / 'SE'

    root = build_xmeml(out_xml.stem)
    sequence = root.find('sequence')
    assert sequence is not None
    media = sequence.find('media')
    assert media is not None
    audio = media.find('audio')
    assert audio is not None

    next_clip_id = 1
    total_end = 0

    # Track A1: Narration from CSV
    a1 = ensure_audio_track(audio, 1)
    for r in rows:
        f = pathlib.Path(r['filename'])
        start_sec = float(r['start_sec'] or 0)
        dur_sec = float(r['duration_sec'] or 0)
        start_f = sec_to_frames(start_sec)
        end_f = start_f + sec_to_frames(dur_sec)
        add_audio_clip(a1, next_clip_id, f.name, f, start_f, end_f)
        total_end = max(total_end, end_f)
        next_clip_id += 1

    # Track A2: BGM per section
    sections = plan.get('sections') or []
    # Compute section end by next start or last narration end
    # First, precompute section start/end in seconds
    import re
    def tc_to_sec(tc: str) -> float:
        parts = tc.strip().split(':')
        if len(parts) == 3:
            h, m, s = parts
            return int(h) * 3600 + int(m) * 60 + float(s)
        if len(parts) == 2:
            m, s = parts
            return int(m) * 60 + float(s)
        return float(parts[0])

    for s in sections:
        s['start_sec'] = tc_to_sec(s.get('start_tc', '00:00:00'))
    sections.sort(key=lambda x: x['start_sec'])
    if rows:
        last_row = rows[-1]
        proj_end_sec = float(last_row['start_sec']) + float(last_row['duration_sec']) + 1.0
    else:
        proj_end_sec = sections[-1]['start_sec'] + 60.0 if sections else 600.0
    for i, s in enumerate(sections):
        if i + 1 < len(sections):
            s['end_sec'] = sections[i+1]['start_sec']
        else:
            s['end_sec'] = proj_end_sec

    a2 = ensure_audio_track(audio, 2)
    for i, s in enumerate(sections, 1):
        label = s.get('label', f'S{i:02d}')
        # Prefer mastered WAV, fallback to MP3
        bgm_file = project_dir / 'サウンド類' / 'BGM_mastered' / f"{project}_BGM{i:02d}_{label}_master.wav"
        if not bgm_file.exists():
            bgm_file = bgm_dir / f"{project}_BGM{i:02d}_{label}.mp3"
        if not bgm_file.exists():
            continue
        st_s = float(s['start_sec'])
        en_s = float(s['end_sec'])
        st_f = sec_to_frames(st_s)
        en_f = sec_to_frames(en_s)
        # Trim by actual file duration if shorter
        dur_file = mp3_estimate_duration_seconds(bgm_file) if bgm_file.suffix.lower() == '.mp3' else (en_s - st_s)
        end_f = min(en_f, st_f + sec_to_frames(dur_file))
        add_audio_clip(a2, next_clip_id, bgm_file.name, bgm_file, st_f, end_f)
        total_end = max(total_end, end_f)
        next_clip_id += 1

    # Track A3: SFX cues
    a3 = ensure_audio_track(audio, 3)
    for i, s in enumerate(sections, 1):
        cues = s.get('sfx') or []
        for j, cue in enumerate(cues, 1):
            label = cue.get('label', f'SFX{i:02d}_{j:02d}')
            time_tc = cue.get('time_tc', '00:00:00').replace(':', '-')
            se_file = se_dir / f"{project}_SE{i:02d}_{time_tc}_{label}.mp3"
            if not se_file.exists():
                continue
            st_s = tc_to_sec(cue.get('time_tc', '00:00:00'))
            dur_s = float(cue.get('duration_sec', 1.6))
            # Trim by actual file duration if shorter
            dur_file = mp3_estimate_duration_seconds(se_file) or dur_s
            dur_final = min(dur_s, dur_file)
            st_f = sec_to_frames(st_s)
            en_f = st_f + sec_to_frames(dur_final)
            add_audio_clip(a3, next_clip_id, se_file.name, se_file, st_f, en_f)
            total_end = max(total_end, en_f)
            next_clip_id += 1

    # Set sequence duration to cover all
    sequence.find('duration').text = str(total_end)

    # Write pretty XML
    try:
        import xml.dom.minidom as minidom
        xml_bytes = ET.tostring(root, encoding='utf-8')
        dom = minidom.parseString(xml_bytes)
        pretty = dom.toprettyxml(indent='  ', encoding='utf-8')
        out_xml.write_bytes(pretty)
    except Exception:
        ET.ElementTree(root).write(out_xml, encoding='utf-8', xml_declaration=True)
    print(f'WROTE: {out_xml}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
