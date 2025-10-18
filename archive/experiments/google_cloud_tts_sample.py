"""Generate speech from `ttssample.md` using Google Cloud Text-to-Speech."""
from __future__ import annotations

import os
from html import escape
from pathlib import Path
from typing import Iterable

from google.cloud import texttospeech

from tts_config_loader import (
    PronunciationHint,
    annotate_text_with_hints,
    load_tts_config,
)


def build_ssml(text: str, hints: Iterable[PronunciationHint], pause_ms: int, paragraph_pause_ms: int | None) -> str:
    effective_sentence_pause = max(pause_ms, 0)
    effective_paragraph_pause = (
        max(paragraph_pause_ms, effective_sentence_pause)
        if paragraph_pause_ms is not None
        else effective_sentence_pause
    )

    escaped = escape(text)
    for hint in hints:
        escaped_term = escape(hint.term)
        alias = escape(hint.reading, quote=True)
        escaped = escaped.replace(
            escaped_term,
            f'<sub alias="{alias}">{escaped_term}</sub>',
        )

    sentence_break = f'<break time="{effective_sentence_pause}ms"/>' if effective_sentence_pause else ""
    paragraph_break = f'<break time="{effective_paragraph_pause}ms"/>' if effective_paragraph_pause else sentence_break

    if sentence_break:
        for punct in ["。", "、", "！", "？"]:
            escaped = escaped.replace(punct, f"{punct}{sentence_break}")
    if paragraph_break:
        escaped = escaped.replace("\n\n", f"{paragraph_break}\n\n")

    return f"<speak>{escaped}</speak>"


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    sample_path = base_dir / "ttssample.md"
    if not sample_path.exists():
        raise FileNotFoundError(f"Sample text not found: {sample_path}")

    text = sample_path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError("ttssample.md is empty; add some text to synthesize.")

    config = load_tts_config()

    hints = config.pronunciation_hints
    sentence_pause_ms = config.sentence_pause_ms
    paragraph_pause_ms = config.paragraph_pause_ms

    client = texttospeech.TextToSpeechClient()

    use_ssml_env = os.getenv("GOOGLE_TTS_USE_SSML")
    if use_ssml_env is not None:
        use_ssml = use_ssml_env not in {"0", "false", "False"}
    else:
        use_ssml = config.google_use_ssml

    if use_ssml:
        ssml = build_ssml(text, hints, config.google_break_ms, paragraph_pause_ms)
        synthesis_input = texttospeech.SynthesisInput(ssml=ssml)
    else:
        annotated_text = annotate_text_with_hints(text, hints)
        synthesis_input = texttospeech.SynthesisInput(text=annotated_text)

    voice_name = os.getenv("GOOGLE_TTS_VOICE", "ja-JP-Neural2-B")
    voice_params = texttospeech.VoiceSelectionParams(
        language_code=os.getenv("GOOGLE_TTS_LANGUAGE", "ja-JP"),
        name=voice_name,
    )

    speaking_rate = float(os.getenv("GOOGLE_TTS_SPEAKING_RATE", "1.0"))
    pitch = float(os.getenv("GOOGLE_TTS_PITCH", "0"))
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=speaking_rate,
        pitch=pitch,
    )

    response = client.synthesize_speech(
        input=synthesis_input,
        voice=voice_params,
        audio_config=audio_config,
    )

    output_path = base_dir / "google_cloud_tts_output.mp3"
    output_path.write_bytes(response.audio_content)

    print(f"Saved synthesized speech to {output_path}")


if __name__ == "__main__":
    main()
