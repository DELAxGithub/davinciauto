#!/usr/bin/env python3
"""Convert a simple `役割,台詞` script into Azure Speech audio + DaVinci timeline.

Workflow:
  1. Parse the provided script file.
  2. Generate a manifest for `synthesize_azure_from_timeline.py` and run it.
  3. Measure clip durations with ffprobe.
  4. Emit a Resolve-friendly CSV and FCP7 XML.
"""
from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

PRE_ROLL = 0.50
BASE_GAP_NA = 0.35
BASE_GAP_DL = 0.60
QUESTION_BONUS = 0.30
LONG_COEF = 0.004
LONG_MAX = 0.40


@dataclass
class LineEntry:
    number: str
    role: str
    character: str
    text: str
    filename: Path


def parse_script(path: Path, audio_dir: Path, prefix: str, start_index: int) -> list[LineEntry]:
    entries: list[LineEntry] = []
    lines = path.read_text(encoding="utf-8").splitlines()
    counter = start_index
    for raw in lines:
        raw = raw.strip()
        if not raw:
            continue
        if "," not in raw:
            # Allow comments or headings that don't map to narration lines
            continue
        speaker, text = raw.split(",", 1)
        speaker = speaker.strip()
        text = text.strip()
        if not text:
            continue
        role = "NA" if speaker.upper() == "NA" else "DL"
        character = "NA" if role == "NA" else speaker
        filename = audio_dir / f"{prefix}-{counter:03d}-{role}.mp3"
        entries.append(
            LineEntry(number=f"{counter:03d}", role=role, character=character, text=text, filename=filename)
        )
        counter += 1
    if not entries:
        raise RuntimeError("No entries parsed from script.")
    return entries


def write_manifest(entries: list[LineEntry], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["filename", "number", "role", "character", "text"])
        writer.writeheader()
        for e in entries:
            writer.writerow({
                "filename": str(e.filename.relative_to(REPO_ROOT)),
                "number": e.number,
                "role": e.role,
                "character": e.character,
                "text": e.text,
            })


def run_azure_synthesis(manifest: Path) -> None:
    script = REPO_ROOT / "scripts" / "synthesize_azure_from_timeline.py"
    cmd = [sys.executable, str(script), str(manifest)]
    subprocess.run(cmd, check=True)


def probe_duration(path: Path) -> float:
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
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    try:
        return round(float(proc.stdout.strip()), 3)
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(f"Could not parse duration for {path}: {proc.stdout}") from exc


def compute_gap(role: str, text: str) -> float:
    base = BASE_GAP_DL if role.upper() == "DL" else BASE_GAP_NA
    bonus = QUESTION_BONUS if ("？" in text or "?" in text) else 0.0
    bonus += min(LONG_MAX, len(text) * LONG_COEF)
    return round(base + bonus, 3)


def build_timeline(entries: list[LineEntry], timeline_csv: Path, timeline_dir: Path) -> None:
    rows: list[dict[str, str]] = []
    cur = PRE_ROLL
    for entry in entries:
        if not entry.filename.exists():
            raise FileNotFoundError(f"Missing audio file: {entry.filename}")
        duration = probe_duration(entry.filename)
        gap = compute_gap(entry.role, entry.text)
        rows.append({
            "filename": str(entry.filename),
            "start_sec": f"{cur:.3f}",
            "duration_sec": f"{duration:.3f}",
            "role": entry.role,
            "character": entry.character,
            "text": entry.text,
            "gap_after_sec": f"{gap:.3f}",
        })
        cur += duration + gap
    timeline_dir.mkdir(parents=True, exist_ok=True)
    with timeline_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "filename",
                "start_sec",
                "duration_sec",
                "role",
                "character",
                "text",
                "gap_after_sec",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def timeline_to_xml(csv_path: Path, xml_path: Path) -> None:
    script = REPO_ROOT / "scripts" / "csv_to_fcpx7_from_timeline.py"
    cmd = [sys.executable, str(script), str(csv_path), str(xml_path)]
    subprocess.run(cmd, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Azure Speech clips + timeline from a script")
    parser.add_argument("script", type=Path, help="Input script file (lines formatted as ROLE,text)")
    parser.add_argument("--audio-dir", type=Path, help="Output directory for narration clips")
    parser.add_argument("--prefix", type=str, help="Filename prefix for generated clips")
    parser.add_argument("--timeline-dir", type=Path, help="Directory for exported timelines")
    parser.add_argument("--timeline-name", type=str, help="Base name for CSV/XML outputs")
    parser.add_argument("--manifest-name", type=str, help="Manifest CSV filename (defaults to <timeline-name>_manifest.csv)")
    parser.add_argument("--start-index", type=int, default=1, help="Starting index number for clips (default: 1)")
    args = parser.parse_args()

    script_path: Path = args.script.resolve()
    if not script_path.exists():
        raise SystemExit(f"Script not found: {script_path}")

    project_dir = script_path.parent.parent if script_path.parent.name == "inputs" else script_path.parent
    audio_dir = (args.audio_dir or (project_dir / "サウンド類" / "Narration")).resolve()
    audio_dir.mkdir(parents=True, exist_ok=True)

    prefix = args.prefix or script_path.stem.replace(" ", "")

    timeline_dir = (args.timeline_dir or (project_dir / "exports" / "timelines")).resolve()
    timeline_name = args.timeline_name or f"{prefix}_timeline"
    manifest_name = args.manifest_name or f"{timeline_name}_manifest.csv"
    manifest_path = (timeline_dir / manifest_name).resolve()
    timeline_csv = (timeline_dir / f"{timeline_name}.csv").resolve()
    timeline_xml = timeline_csv.with_suffix(".xml")

    entries = parse_script(script_path, audio_dir, prefix, args.start_index)
    write_manifest(entries, manifest_path)
    run_azure_synthesis(manifest_path)
    build_timeline(entries, timeline_csv, timeline_dir)
    timeline_to_xml(timeline_csv, timeline_xml)
    print(f"Timeline CSV: {timeline_csv}")
    print(f"Timeline XML: {timeline_xml}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
