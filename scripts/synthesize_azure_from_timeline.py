#!/usr/bin/env python3
"""Synthesize narration audio for an entire timeline CSV using Azure AI Speech."""
from __future__ import annotations

import argparse
import csv
import os
import sys
import time
from pathlib import Path
from typing import Optional
from xml.sax.saxutils import escape

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None  # type: ignore


def load_env() -> None:
    if load_dotenv:
        repo_root = Path(__file__).resolve().parent.parent
        env_path = repo_root / ".env"
        if env_path.exists():
            load_dotenv(str(env_path))


def build_ssml(text: str, voice: str, style: Optional[str], rate: float) -> str:
    body = escape(text)
    if abs(rate - 1.0) > 1e-6:
        pct = int(round((rate - 1.0) * 100))
        sign = "+" if pct >= 0 else ""
        body = f"<prosody rate=\"{sign}{pct}%\">{body}</prosody>"
    if style:
        body = f"<mstts:express-as style=\"{escape(style)}\">{body}</mstts:express-as>"
    speak_attrs = (
        'version="1.0" '
        'xmlns="http://www.w3.org/2001/10/synthesis" '
        'xmlns:mstts="https://www.w3.org/2001/mstts" '
        'xml:lang="ja-JP"'
    )
    return f"<speak {speak_attrs}><voice name=\"{escape(voice)}\">{body}</voice></speak>"


def choose_voice(role: str, character: str) -> tuple[str, Optional[str], float]:
    role = (role or "").strip().upper()
    char = (character or "").strip()

    char_map = {
        "同僚A": ("ja-JP-MayuNeural", "friendly", 1.0),
        "母親": ("ja-JP-ShioriNeural", "calm", 1.0),
        "オデュッセウス": ("ja-JP-KeitaNeural", "narration-relaxed", 1.0),
        "釈迦": ("ja-JP-NaokiNeural", "calm", 1.0),
        "ヘラクレイトス": ("ja-JP-DaichiNeural", "narration-relaxed", 1.0),
        "内なる声": ("ja-JP-ShioriNeural", "chat", 1.0),
    }
    if char in char_map:
        return char_map[char]

    if role == "NA":
        return ("ja-JP-NanamiNeural", "narration-professional", 1.0)
    if role == "DL":
        return ("ja-JP-KeitaNeural", "chat", 1.0)

    return ("ja-JP-NanamiNeural", None, 1.0)


def synthesize_rows(csv_path: Path) -> None:
    load_env()

    try:
        import azure.cognitiveservices.speech as speechsdk  # type: ignore
    except Exception as exc:  # pragma: no cover
        print("Azure Speech SDK is not installed (pip install azure-cognitiveservices-speech)", file=sys.stderr)
        raise SystemExit(1) from exc

    key = os.getenv("AZURE_SPEECH_KEY")
    region = os.getenv("AZURE_SPEECH_REGION")
    if not key or not region:
        print("AZURE_SPEECH_KEY and AZURE_SPEECH_REGION must be set.", file=sys.stderr)
        raise SystemExit(1)

    speech_config = speechsdk.SpeechConfig(subscription=key, region=region)
    if hasattr(speech_config, "set_speech_synthesis_output_format"):
        speech_config.set_speech_synthesis_output_format(
            speechsdk.SpeechSynthesisOutputFormat.Audio24Khz160KBitRateMonoMp3
        )

    repo_root = Path(__file__).resolve().parent.parent

    with csv_path.open('r', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))

    total = len(rows)
    ok = 0
    start_time = time.time()

    for idx, row in enumerate(rows, 1):
        text = (row.get('text') or '').strip()
        if not text:
            print(f"[{idx}/{total}] Skip empty text")
            continue

        voice, style, rate = choose_voice(row.get('role', ''), row.get('character', ''))

        rel_path = Path(row['filename'])
        target_path = rel_path if rel_path.is_absolute() else (repo_root / rel_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        speech_config.speech_synthesis_voice_name = voice
        audio_config = speechsdk.audio.AudioOutputConfig(filename=str(target_path))
        synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)

        print(f"[{idx}/{total}] {target_path.name} <- {voice} (style={style or '-'} )")

        if style or abs(rate - 1.0) > 1e-6:
            ssml = build_ssml(text, voice, style, rate)
            result = synthesizer.speak_ssml_async(ssml).get()
        else:
            result = synthesizer.speak_text_async(text).get()

        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            ok += 1
            continue

        if result.reason == getattr(speechsdk.ResultReason, "Canceled", None):
            cancellation = speechsdk.CancellationDetails.from_result(result)
            print(f"    ERROR: synthesis canceled -> {cancellation.error_details}")
        else:
            print("    ERROR: synthesis failed.")

    elapsed = time.time() - start_time
    print(f"Done. Synthesized {ok}/{total} clips in {elapsed:.1f}s")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Azure Speech MP3s from timeline CSV")
    parser.add_argument("csv", type=Path, help="Timeline CSV path")
    args = parser.parse_args()

    if not args.csv.exists():
        print(f"CSV not found: {args.csv}", file=sys.stderr)
        return 2

    synthesize_rows(args.csv.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
