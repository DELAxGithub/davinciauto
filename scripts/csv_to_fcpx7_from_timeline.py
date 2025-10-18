#!/usr/bin/env python3
"""
Build a simple Final Cut Pro 7 XML (xmeml) audio timeline from our gap-aware CSV.

Input CSV headers:
  filename,start_sec,duration_sec,role,character,text,gap_after_sec

Output:
  <csv_path_without_ext>.xml (xmeml v4) — importable in DaVinci Resolve
"""
from __future__ import annotations

import csv
import json
import os
import pathlib
import subprocess
import sys
import urllib.parse
import xml.etree.ElementTree as ET


FPS = 30


def sec_to_frames(sec: float, fps: int = FPS) -> int:
    return int(round(sec * fps))


def file_url(path: pathlib.Path) -> str:
    p = path.resolve()
    if os.name == 'nt':
        # Windows: drive letter with colon needs special handling
        return 'file:///' + urllib.parse.quote(str(p).replace('\\', '/'))
    return 'file://' + urllib.parse.quote(str(p))


def probe_audio(path: pathlib.Path) -> tuple[float, int]:
    """Get duration (sec) and sample rate for an audio file via ffprobe."""
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "a:0",
        "-show_entries",
        "stream=sample_rate:format=duration",
        "-of",
        "json",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)
    duration = float(data["format"]["duration"])
    sample_rate = int(data["streams"][0]["sample_rate"])
    return duration, sample_rate


def build_xml(rows: list[dict[str, str]], name: str) -> ET.ElementTree:
    total_end_frames = 0
    # Root
    root = ET.Element('xmeml', version='4')
    sequence = ET.SubElement(root, 'sequence')
    ET.SubElement(sequence, 'uuid').text = name
    duration_elem = ET.SubElement(sequence, 'duration')
    ET.SubElement(sequence, 'name').text = name
    # Rate
    rate = ET.SubElement(sequence, 'rate')
    ET.SubElement(rate, 'timebase').text = str(FPS)
    ET.SubElement(rate, 'ntsc').text = 'TRUE'
    # Media container
    media = ET.SubElement(sequence, 'media')
    video = ET.SubElement(media, 'video')
    ET.SubElement(video, 'format')  # keep empty
    audio = ET.SubElement(media, 'audio')
    # Audio track (single A1)
    track = ET.SubElement(audio, 'track')

    next_clip_id = 1
    next_file_id = 1
    for r in rows:
        fpath = pathlib.Path(r['filename'])
        start_sec = float(r['start_sec'] or '0')
        dur_sec = float(r['duration_sec'] or '0')
        start_f = sec_to_frames(start_sec)
        dur_f = max(1, sec_to_frames(dur_sec))
        end_f = start_f + dur_f
        total_end_frames = max(total_end_frames, end_f)

        # Probe audio metadata once so in/out and sample rate match actual file
        try:
            _, sample_rate = probe_audio(fpath)
        except Exception as exc:  # pragma: no cover - defensive
            raise RuntimeError(f"Failed to probe audio metadata for {fpath}") from exc

        in_samples = 0
        out_samples = max(1, int(round(dur_sec * sample_rate)))

        clipitem = ET.SubElement(track, 'clipitem')
        clipitem.set('id', f'clipitem-{next_clip_id}')
        next_clip_id += 1
        ET.SubElement(clipitem, 'name').text = fpath.name
        ET.SubElement(clipitem, 'enabled').text = 'TRUE'
        # duration = source total; we set to used duration for simplicity
        ET.SubElement(clipitem, 'duration').text = str(dur_f)
        # Rate
        c_rate = ET.SubElement(clipitem, 'rate')
        ET.SubElement(c_rate, 'timebase').text = str(FPS)
        ET.SubElement(c_rate, 'ntsc').text = 'TRUE'
        # Timeline position
        ET.SubElement(clipitem, 'start').text = str(start_f)
        ET.SubElement(clipitem, 'end').text = str(end_f)
        # Source in/out
        ET.SubElement(clipitem, 'in').text = str(in_samples)
        ET.SubElement(clipitem, 'out').text = str(out_samples)
        # File reference
        file_elem = ET.SubElement(clipitem, 'file')
        file_elem.set('id', f'file-{next_file_id}')
        next_file_id += 1
        ET.SubElement(file_elem, 'name').text = fpath.name
        ET.SubElement(file_elem, 'pathurl').text = file_url(fpath)

        # Source audio metadata (explicit sample rate/channel count avoids speed issues)
        f_rate = ET.SubElement(file_elem, 'rate')
        ET.SubElement(f_rate, 'timebase').text = str(sample_rate)
        ET.SubElement(f_rate, 'ntsc').text = 'FALSE'
        media = ET.SubElement(file_elem, 'media')
        audio_media = ET.SubElement(media, 'audio')
        ET.SubElement(audio_media, 'channelcount').text = '1'
        sample = ET.SubElement(audio_media, 'samplecharacteristics')
        ET.SubElement(sample, 'samplerate').text = str(sample_rate)
        ET.SubElement(sample, 'samplesize').text = '16'

        # audio sourcetrack mapping
        st = ET.SubElement(clipitem, 'sourcetrack')
        ET.SubElement(st, 'mediatype').text = 'audio'
        ET.SubElement(st, 'trackindex').text = '1'

    duration_elem.text = str(total_end_frames)
    return ET.ElementTree(root)


def main() -> int:
    if len(sys.argv) < 2:
        print('Usage: python scripts/csv_to_fcpx7_from_timeline.py <timeline_csv> [<out_xml>]', file=sys.stderr)
        return 2
    csv_path = pathlib.Path(sys.argv[1])
    if not csv_path.exists():
        print(f'CSV not found: {csv_path}', file=sys.stderr)
        return 3
    out_xml = pathlib.Path(sys.argv[2]) if len(sys.argv) >= 3 else csv_path.with_suffix('.xml')

    rows: list[dict[str, str]] = []
    with csv_path.open('r', encoding='utf-8') as f:
        r = csv.DictReader(f)
        for row in r:
            rows.append(row)

    name = out_xml.stem
    tree = build_xml(rows, name)
    # pretty print by minidom
    try:
        import xml.dom.minidom as minidom
        xml_bytes = ET.tostring(tree.getroot(), encoding='utf-8')
        dom = minidom.parseString(xml_bytes)
        pretty = dom.toprettyxml(indent='  ', encoding='utf-8')
        out_xml.write_bytes(pretty)
    except Exception:
        tree.write(out_xml, encoding='utf-8', xml_declaration=True)
    print(f'WROTE: {out_xml}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
