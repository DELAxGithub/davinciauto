"""Generate speech from `ttssample.md` using the Gemini TTS preview model."""
from __future__ import annotations

import base64
import os
import wave
from pathlib import Path

from google import genai
from google.genai import types

from tts_config_loader import (
    annotate_text_with_hints,
    extend_prompt,
    load_tts_config,
)


PCM_SAMPLE_RATE = 24_000
PCM_CHANNELS = 1
PCM_SAMPLE_WIDTH = 2  # bytes (16-bit)


def save_wave(filename: Path, pcm_data: bytes) -> None:
    """Persist PCM data to a WAV container so common players can open it."""
    with wave.open(str(filename), "wb") as wav_file:
        wav_file.setnchannels(PCM_CHANNELS)
        wav_file.setsampwidth(PCM_SAMPLE_WIDTH)
        wav_file.setframerate(PCM_SAMPLE_RATE)
        wav_file.writeframes(pcm_data)


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    sample_path = base_dir / "ttssample.md"
    if not sample_path.exists():
        raise FileNotFoundError(f"Sample text not found: {sample_path}")

    text = sample_path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError("ttssample.md is empty; add some text to synthesize.")

    config = load_tts_config()
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

    base_prompt = os.getenv("GEMINI_TTS_STYLE") or config.style_prompts.get("gemini")
    if not base_prompt:
        base_prompt = (
            "Please narrate the following script in a composed, insightful tone "
            "appropriate for educational content."
        )

    annotated_text = annotate_text_with_hints(text, config.pronunciation_hints)
    style_prompt = extend_prompt(base_prompt, config.pronunciation_hints, config.sentence_pause_ms)

    response = client.models.generate_content(
        model=os.getenv("GEMINI_TTS_MODEL", "gemini-2.5-flash-preview-tts"),
        contents=f"{style_prompt}\n\n{annotated_text}",
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=os.getenv("GEMINI_TTS_VOICE", "Kore"),
                    )
                )
            ),
        ),
    )

    inline_data = response.candidates[0].content.parts[0].inline_data
    raw_data = inline_data.data
    if isinstance(raw_data, str):
        pcm_bytes = base64.b64decode(raw_data)
    else:
        pcm_bytes = raw_data

    if not pcm_bytes:
        raise RuntimeError("Gemini TTS returned empty audio data")

    output_path = base_dir / "gemini_tts_output.wav"
    save_wave(output_path, pcm_bytes)

    print(f"Saved synthesized speech to {output_path}")


if __name__ == "__main__":
    main()
