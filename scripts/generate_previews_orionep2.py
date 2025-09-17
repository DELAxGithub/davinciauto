#!/usr/bin/env python3
import os
import pathlib
import sys


def load_api_key_from_envfile(env_path: pathlib.Path) -> str | None:
    try:
        with env_path.open('r', encoding='utf-8') as f:
            for raw in f:
                s = raw.strip()
                if not s or s.startswith('#'):
                    continue
                if s.startswith('ELEVENLABS_API_KEY='):
                    v = s.split('=', 1)[1].strip().strip('"').strip("'")
                    if '#' in v:
                        v = v.split('#', 1)[0].strip()
                    return v
    except Exception:
        return None
    return None


def main() -> int:
    api_key = os.getenv('ELEVENLABS_API_KEY')
    if not api_key:
        api_key = load_api_key_from_envfile(pathlib.Path('.env'))
    if not api_key:
        print('ERROR: ELEVENLABS_API_KEY not found in environment or .env', file=sys.stderr)
        return 2

    try:
        from elevenlabs import ElevenLabs
    except Exception as e:
        print('ERROR: elevenlabs SDK not available:', e, file=sys.stderr)
        return 3

    text = 'リモートワークの実家も、久々のオフィスも、どこか居心地が悪いと感じたことはありませんか？'
    voices: dict[str, str] = {
        'Shizuka': 'WQz3clzUdMqvBf0jswZQ',
        'Heyhey': 'YFkT3BsfOFWBx3jfroxH',
        'Voiceactor_Hatakekohei': 'sRYzP8TwEiiqAWebdYPJ',
        'Ishibashi': 'Mv8AjrYZCBkdsmDHNwcB',
        'Otani': '3JDquces8E8bkmvbh6Bc',
        'Shohei': '8FuuqoKHuM48hIEwni5e',
        'Fumi': 'PmgfHCGeS5b7sH90BOOJ',
        'Jessica': 'flHkNRp1BlvT73UL6gyz',
    }

    proj = pathlib.Path('projects/OrionEp2')
    out = proj / 'サウンド類' / 'Narration' / 'previews'
    out.mkdir(parents=True, exist_ok=True)

    client = ElevenLabs(api_key=api_key)

    saved: list[str] = []
    errors: list[tuple[str, str]] = []

    for label, vid in voices.items():
        try:
            audio = client.text_to_speech.convert(
                text=text,
                voice_id=vid,
                model_id='eleven_v3',
                output_format='mp3_44100_128',
            )
            fp = out / f'OrionEp2-001-NA-{label}.mp3'
            with open(fp, 'wb') as f:
                if isinstance(audio, (bytes, bytearray)):
                    f.write(audio)
                else:
                    for chunk in audio:
                        if isinstance(chunk, (bytes, bytearray)):
                            f.write(chunk)
            saved.append(str(fp))
        except Exception as e:
            errors.append((label, str(e)))

    print('SAVED:')
    for p in saved:
        print(p)
    if errors:
        print('ERRORS:')
        for lbl, err in errors:
            print(lbl, err)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
