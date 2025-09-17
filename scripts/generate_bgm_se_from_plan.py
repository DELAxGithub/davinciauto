#!/usr/bin/env python3
import os
import json
import pathlib
import sys
from typing import Any, Dict, List


def load_env_api_key() -> str | None:
    k = os.getenv('ELEVENLABS_API_KEY')
    if k:
        return k
    try:
        with open('.env', 'r', encoding='utf-8') as f:
            for raw in f:
                s = raw.strip()
                if s.startswith('ELEVENLABS_API_KEY='):
                    v = s.split('=', 1)[1].strip().strip('"').strip("'")
                    if '#' in v:
                        v = v.split('#', 1)[0].strip()
                    return v
    except Exception:
        return None
    return None


def tc_to_sec(tc: str) -> float:
    parts = tc.strip().split(':')
    if len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + float(s)
    if len(parts) == 2:
        m, s = parts
        return int(m) * 60 + float(s)
    return float(parts[0])


def sec_to_hhmmss(sec: float) -> str:
    s = int(round(sec))
    h = s // 3600
    m = (s % 3600) // 60
    ss = s % 60
    return f"{h:02d}-{m:02d}-{ss:02d}"


def project_end_seconds(project: str) -> float:
    # Try SRT first
    srt = pathlib.Path('projects') / project / 'テロップ類' / 'SRT' / f'{project}_Sub_follow.srt'
    end_last = 0.0
    if srt.exists():
        try:
            text = srt.read_text(encoding='utf-8')
            # find last time range "HH:MM:SS,mmm --> HH:MM:SS,mmm"
            import re
            matches = re.findall(r"(\d\d:\d\d:\d\d,\d\d\d)\s*-->\s*(\d\d:\d\d:\d\d,\d\d\d)", text)
            if matches:
                last_end = matches[-1][1]
                hh, mm, rest = last_end.split(':')
                ss, ms = rest.split(',')
                end_last = int(hh) * 3600 + int(mm) * 60 + int(ss) + int(ms)/1000.0
        except Exception:
            end_last = 0.0
    # Fallback to narration CSV last end
    if end_last <= 0:
        csvp = pathlib.Path('projects') / project / 'exports' / 'timelines' / f'{project}_timeline_v1.csv'
        try:
            import csv
            with csvp.open('r', encoding='utf-8') as f:
                r = list(csv.DictReader(f))
            if r:
                last = r[-1]
                start = float(last['start_sec'] or 0)
                dur = float(last['duration_sec'] or 0)
                end_last = start + dur + 1.0
        except Exception:
            end_last = 600.0
    return max(end_last, 1.0)


def main() -> int:
    if len(sys.argv) < 2:
        print('Usage: python scripts/generate_bgm_se_from_plan.py <plan.json> [--only bgm|sfx]', file=sys.stderr)
        return 2
    plan_path = pathlib.Path(sys.argv[1])
    if not plan_path.exists():
        print(f'Plan not found: {plan_path}', file=sys.stderr)
        return 3

    api_key = load_env_api_key()
    if not api_key:
        print('ERROR: ELEVENLABS_API_KEY missing', file=sys.stderr)
        return 4

    try:
        from elevenlabs import ElevenLabs
    except Exception as e:
        print('ERROR: elevenlabs SDK not available:', e, file=sys.stderr)
        return 5

    plan = json.loads(plan_path.read_text(encoding='utf-8'))
    project = plan.get('project', plan_path.parent.parent.name)
    sections: List[Dict[str, Any]] = plan.get('sections', [])
    if not sections:
        print('No sections in plan', file=sys.stderr)
        return 6

    # Sort by start time
    for s in sections:
        s['start_sec'] = tc_to_sec(s['start_tc'])
    sections.sort(key=lambda x: x['start_sec'])

    project_dir = pathlib.Path('projects') / project
    bgm_dir = project_dir / 'サウンド類' / 'BGM'
    se_dir = project_dir / 'サウンド類' / 'SE'
    bgm_dir.mkdir(parents=True, exist_ok=True)
    se_dir.mkdir(parents=True, exist_ok=True)

    # Determine end times by next section start, last by project end
    proj_end = project_end_seconds(project)
    for i, s in enumerate(sections):
        if i + 1 < len(sections):
            s['end_sec'] = sections[i+1]['start_sec']
        else:
            s['end_sec'] = proj_end
        s['length_ms'] = max(1000, int(round((s['end_sec'] - s['start_sec']) * 1000)))

    client = ElevenLabs(api_key=api_key)

    # Options
    only_mode = None
    if '--only' in sys.argv:
        try:
            only_mode = sys.argv[sys.argv.index('--only') + 1].strip().lower()
        except Exception:
            only_mode = None
    do_bgm = (only_mode is None) or (only_mode == 'bgm')
    do_sfx = (only_mode is None) or (only_mode == 'sfx')

    saved_bgm: List[str] = []
    saved_se: List[str] = []
    errors: List[str] = []

    # Generate BGM per section
    if do_bgm:
        for idx, s in enumerate(sections, 1):
            prompt = (s.get('bgm_prompt') or '').strip()
            if not prompt:
                continue
            try:
                audio = client.music.compose(prompt=prompt, music_length_ms=int(s['length_ms']))
                out = bgm_dir / f"{project}_BGM{idx:02d}_{s['label']}.mp3"
                with out.open('wb') as f:
                    if isinstance(audio, (bytes, bytearray)):
                        f.write(audio)
                    else:
                        for chunk in audio:
                            if isinstance(chunk, (bytes, bytearray)):
                                f.write(chunk)
                saved_bgm.append(str(out))
            except Exception as e:
                errors.append(f"BGM {idx}: {e}")

    # Generate SFX cues
    if do_sfx:
        for idx, s in enumerate(sections, 1):
            cues = s.get('sfx') or []
            for j, cue in enumerate(cues, 1):
                text = (cue.get('prompt') or '').strip()
                if not text:
                    continue
                try:
                    # Prefer modern path; fallback if SDK name differs
                    try:
                        audio = client.sound_effects.convert(text=text, duration_seconds=float(cue.get('duration_sec', 1.6)))  # type: ignore[attr-defined]
                    except Exception:
                        audio = client.text_to_sound_effects.convert(text=text, duration_seconds=float(cue.get('duration_sec', 1.6)))  # type: ignore[attr-defined]
                    hhmmss = cue.get('time_tc', '00:00:00').replace(':', '-')
                    label = cue.get('label', f'SFX{idx:02d}_{j:02d}')
                    out = se_dir / f"{project}_SE{idx:02d}_{hhmmss}_{label}.mp3"
                    with out.open('wb') as f:
                        if isinstance(audio, (bytes, bytearray)):
                            f.write(audio)
                        else:
                            for chunk in audio:
                                if isinstance(chunk, (bytes, bytearray)):
                                    f.write(chunk)
                    saved_se.append(str(out))
                except Exception as e:
                    errors.append(f"SE {idx}-{j}: {e}")

    print('BGM SAVED:')
    for p in saved_bgm:
        print(p)
    print('SE SAVED:')
    for p in saved_se:
        print(p)
    if errors:
        print('ERRORS:')
        for e in errors:
            print(e)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
