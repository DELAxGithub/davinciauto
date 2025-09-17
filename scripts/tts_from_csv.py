#!/usr/bin/env python3
import csv
import os
import pathlib
import sys
from typing import Dict


VOICE_MAP: Dict[str, str] = {
    # キャラクター固定
    'オデュッセウス': 'sRYzP8TwEiiqAWebdYPJ',  # Voiceactor Hatakekohei
    '釈迦': '8FuuqoKHuM48hIEwni5e',            # Shohei
    'ヘラクレイトス': 'Mv8AjrYZCBkdsmDHNwcB',    # Ishibashi
    '同僚A': 'PmgfHCGeS5b7sH90BOOJ',            # Fumi
    '母親': 'WQz3clzUdMqvBf0jswZQ',            # Shizuka
    '内なる声': 'YFkT3BsfOFWBx3jfroxH',         # Heyhey
}

# 役割デフォルト
DEFAULT_NA = 'WQz3clzUdMqvBf0jswZQ'  # Shizuka（日本語）
DEFAULT_DL = 'YFkT3BsfOFWBx3jfroxH'  # Heyhey（汎用）


def load_api_key() -> str | None:
    k = os.getenv('ELEVENLABS_API_KEY')
    if k:
        return k
    try:
        with open('.env', 'r', encoding='utf-8') as f:
            for line in f:
                s = line.strip()
                if s.startswith('ELEVENLABS_API_KEY='):
                    v = s.split('=', 1)[1].split('#', 1)[0].strip().strip('"').strip("'")
                    return v
    except Exception:
        return None
    return None


def resolve_voice_id(role: str, character: str) -> str:
    if character and character in VOICE_MAP:
        return VOICE_MAP[character]
    role_u = (role or '').strip().upper()
    if role_u == 'DL':
        return DEFAULT_DL
    return DEFAULT_NA


def main() -> int:
    if len(sys.argv) < 2:
        print('Usage: python scripts/tts_from_csv.py <csv_path> [project_dir]', file=sys.stderr)
        return 2
    csv_path = pathlib.Path(sys.argv[1])
    if not csv_path.exists():
        print(f'CSV not found: {csv_path}', file=sys.stderr)
        return 3
    project_dir = pathlib.Path(sys.argv[2]) if len(sys.argv) >= 3 else csv_path.parent.parent

    api_key = load_api_key()
    if not api_key:
        print('ERROR: ELEVENLABS_API_KEY missing', file=sys.stderr)
        return 4

    try:
        from elevenlabs import ElevenLabs
    except Exception as e:
        print('ERROR: elevenlabs SDK not available:', e, file=sys.stderr)
        return 5

    out_dir = project_dir / 'サウンド類' / 'Narration'
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = list(csv.DictReader(csv_path.open('r', encoding='utf-8')))
    # CLI options
    model_id = 'eleven_v3'
    if '--model' in sys.argv:
        try:
            model_id = sys.argv[sys.argv.index('--model') + 1].strip()
        except Exception:
            pass
    # Optional voice settings (supported by multilingual_v2 and others)
    def get_opt(name: str, default: float) -> float:
        if name in sys.argv:
            try:
                return float(sys.argv[sys.argv.index(name) + 1])
            except Exception:
                return default
        return default
    stability = get_opt('--stability', 0.3)
    similarity = get_opt('--similarity', 0.85)
    style = get_opt('--style', 0.2)
    speaker_boost = 1 if ('--boost' in sys.argv and sys.argv[sys.argv.index('--boost') + 1].strip() not in ('0', 'false', 'False')) else 1
    # Voice override (NA/DL)
    na_override = None
    dl_override = None
    if '--na-voice-id' in sys.argv:
        try:
            na_override = sys.argv[sys.argv.index('--na-voice-id') + 1].strip()
        except Exception:
            na_override = None
    if '--dl-voice-id' in sys.argv:
        try:
            dl_override = sys.argv[sys.argv.index('--dl-voice-id') + 1].strip()
        except Exception:
            dl_override = None
    client = ElevenLabs(api_key=api_key)

    saved, errors = [], []
    for r in rows:
        num = (r.get('number') or '').zfill(3)
        role = r.get('role') or 'NA'
        character = r.get('character') or ''
        text = (r.get('text') or '').strip()
        if not text:
            continue
        vid = resolve_voice_id(role, character)
        if (role or '').strip().upper() == 'NA' and na_override:
            vid = na_override
        if (role or '').strip().upper() == 'DL' and dl_override:
            vid = dl_override
        out_name = f"OrionEp2-{num}-{role.upper()}.mp3"
        out_path = out_dir / out_name
        try:
            kwargs = dict(
                text=text,
                voice_id=vid,
                model_id=model_id,
                output_format='mp3_44100_128',
            )
            # Attach voice settings when using multilingual model
            if 'multilingual' in model_id:
                kwargs['voice_settings'] = {
                    'stability': stability,
                    'similarity_boost': similarity,
                    'style': style,
                    'use_speaker_boost': bool(speaker_boost),
                }
            audio = client.text_to_speech.convert(**kwargs)
            with out_path.open('wb') as f:
                if isinstance(audio, (bytes, bytearray)):
                    f.write(audio)
                else:
                    for chunk in audio:
                        if isinstance(chunk, (bytes, bytearray)):
                            f.write(chunk)
            saved.append(str(out_path))
        except Exception as e:
            errors.append(f"{num} {role} {character}: {e}")

    print('SAVED:')
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
