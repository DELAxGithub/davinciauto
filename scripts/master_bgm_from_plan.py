#!/usr/bin/env python3
import json
import pathlib
import subprocess
import sys
from typing import Any, Dict, List, Optional


TARGET_LUFS = -15.0  # I
TARGET_TP = -1.0     # dBTP
TARGET_LRA = 11.0
FADE_IN = 1.0
FADE_OUT = 1.5
OUT_SR = 48000
OUT_CH = 2


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def tc_to_sec(tc: str) -> float:
    parts = tc.strip().split(':')
    if len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + float(s)
    if len(parts) == 2:
        m, s = parts
        return int(m) * 60 + float(s)
    return float(parts[0])


def measure_loudness(in_path: pathlib.Path) -> Optional[Dict[str, Any]]:
    cmd = [
        'ffmpeg', '-hide_banner', '-nostats', '-y',
        '-i', str(in_path),
        '-filter_complex', f"loudnorm=I={TARGET_LUFS}:TP={TARGET_TP}:LRA={TARGET_LRA}:print_format=json",
        '-f', 'null', '-'
    ]
    p = run(cmd)
    out = p.stderr or p.stdout
    if p.returncode != 0:
        return None
    # Extract last JSON object in output
    start = out.rfind('{')
    end = out.rfind('}')
    if start == -1 or end == -1 or end <= start:
        return None
    import json as _json
    try:
        data = _json.loads(out[start:end+1])
        return data
    except Exception:
        return None


def apply_master(in_path: pathlib.Path, out_path: pathlib.Path, dur_sec: float) -> bool:
    # Adjust fades if duration is very short
    fade_in = min(FADE_IN, max(0.0, dur_sec * 0.2))
    fade_out = min(FADE_OUT, max(0.0, dur_sec * 0.3))
    fade_out_start = max(0.0, dur_sec - fade_out)

    meas = measure_loudness(in_path)
    if not meas:
        return False
    args = {
        'measured_I': meas.get('input_i'),
        'measured_TP': meas.get('input_tp'),
        'measured_LRA': meas.get('input_lra'),
        'measured_thresh': meas.get('input_thresh'),
        'offset': meas.get('target_offset')
    }
    if None in args.values():
        return False
    loudnorm2 = (
        f"loudnorm=I={TARGET_LUFS}:TP={TARGET_TP}:LRA={TARGET_LRA}:"
        f"measured_I={args['measured_I']}:measured_TP={args['measured_TP']}:"
        f"measured_LRA={args['measured_LRA']}:measured_thresh={args['measured_thresh']}:"
        f"offset={args['offset']}:linear=true:print_format=summary"
    )
    af = f"{loudnorm2},afade=t=in:st=0:d={fade_in},afade=t=out:st={fade_out_start}:d={fade_out}"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        'ffmpeg', '-hide_banner', '-nostats', '-y',
        '-t', f"{dur_sec:.3f}",
        '-i', str(in_path),
        '-af', af,
        '-ar', str(OUT_SR), '-ac', str(OUT_CH),
        str(out_path)
    ]
    p = run(cmd)
    return p.returncode == 0


def main() -> int:
    if len(sys.argv) < 2:
        print('Usage: python scripts/master_bgm_from_plan.py <plan.json> [project_dir]', file=sys.stderr)
        return 2
    plan_path = pathlib.Path(sys.argv[1])
    proj_dir = pathlib.Path(sys.argv[2]) if len(sys.argv) >= 3 else plan_path.parent.parent
    if not plan_path.exists():
        print(f'Plan not found: {plan_path}', file=sys.stderr)
        return 3
    plan = json.loads(plan_path.read_text(encoding='utf-8'))
    project = plan.get('project', proj_dir.name)
    sections: List[Dict[str, Any]] = plan.get('sections', [])
    if not sections:
        print('No sections found in plan', file=sys.stderr)
        return 4

    for s in sections:
        s['start_sec'] = tc_to_sec(s.get('start_tc', '00:00:00'))
    sections.sort(key=lambda x: x['start_sec'])
    # Determine end by next start; last gets +1min fallback
    for i, s in enumerate(sections):
        if i + 1 < len(sections):
            s['end_sec'] = sections[i+1]['start_sec']
        else:
            s['end_sec'] = s['start_sec'] + 60.0

    bgm_src = proj_dir / 'サウンド類' / 'BGM'
    bgm_out = proj_dir / 'サウンド類' / 'BGM_mastered'

    saved = []
    errors = []
    for i, s in enumerate(sections, 1):
        label = s.get('label', f'S{i:02d}')
        in_path = bgm_src / f"{project}_BGM{i:02d}_{label}.mp3"
        if not in_path.exists():
            errors.append(f'missing BGM: {in_path}')
            continue
        dur = max(1.0, float(s['end_sec'] - s['start_sec']))
        out_path = bgm_out / f"{project}_BGM{i:02d}_{label}_master.wav"
        ok = apply_master(in_path, out_path, dur)
        if ok:
            saved.append(str(out_path))
        else:
            errors.append(f'fail master: {in_path}')

    print('MASTERED:')
    for p in saved:
        print(p)
    if errors:
        print('ERRORS:')
        for e in errors:
            print(e)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

