#!/usr/bin/env python3
import csv
import pathlib
import sys
from typing import Dict, List

try:
    from mutagen import File as MutagenFile  # type: ignore
except Exception:  # pragma: no cover
    MutagenFile = None  # type: ignore

FPS = 30
PRE_ROLL = 0.50
BASE_GAP_NA = 0.35
BASE_GAP_DL = 0.60
QUESTION_BONUS = 0.30
LONG_COEF = 0.004
LONG_MAX = 0.40


def mp3_duration_seconds(path: pathlib.Path, kbps: int = 128) -> float:
    # Prefer precise duration via mutagen if available
    if MutagenFile is not None:
        try:
            audio = MutagenFile(path)
            if audio is not None and getattr(audio, "info", None) and audio.info.length:
                return round(float(audio.info.length), 3)
        except Exception:
            pass

    # Fallback to size-based estimate
    try:
        size = path.stat().st_size
        return round((size * 8.0) / (kbps * 1000.0), 3)
    except Exception:
        return 0.0


def compute_gap(role: str, text: str) -> float:
    base = BASE_GAP_DL if (role or '').strip().upper() == 'DL' else BASE_GAP_NA
    bonus = 0.0
    if '？' in text or '?' in text:
        bonus += QUESTION_BONUS
    bonus += min(LONG_MAX, len(text) * LONG_COEF)
    return round(base + bonus, 3)


def main() -> int:
    if len(sys.argv) < 3:
        print('Usage: python scripts/build_timeline_from_csv.py <input_csv> <out_timeline_csv>', file=sys.stderr)
        return 2
    in_csv = pathlib.Path(sys.argv[1])
    out_csv = pathlib.Path(sys.argv[2])
    project_dir = in_csv.parent.parent

    rows_in = list(csv.DictReader(in_csv.open('r', encoding='utf-8')))
    narr_dir = project_dir / 'サウンド類' / 'Narration'

    rows_out: List[Dict[str, str]] = []
    cur = PRE_ROLL
    for r in rows_in:
        num = (r.get('number') or '').zfill(3)
        role = r.get('role') or 'NA'
        character = r.get('character') or 'NA'
        text = (r.get('text') or '').strip()
        fname = f"OrionEp2-{num}-{role.upper()}.mp3"
        fpath = narr_dir / fname
        dur = mp3_duration_seconds(fpath)
        gap = compute_gap(role, text)
        rows_out.append({
            'filename': str(fpath),
            'start_sec': f"{cur:.3f}",
            'duration_sec': f"{dur:.3f}",
            'role': role,
            'character': character,
            'text': text,
            'gap_after_sec': f"{gap:.3f}",
        })
        cur += dur + gap

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['filename','start_sec','duration_sec','role','character','text','gap_after_sec'])
        w.writeheader()
        w.writerows(rows_out)
    print(f'WROTE: {out_csv}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
