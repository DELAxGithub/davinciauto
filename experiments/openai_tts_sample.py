"""Generate speech from `ttssample.md` using OpenAI's text-to-speech API."""
from __future__ import annotations

import os
from pathlib import Path

from openai import OpenAI

from tts_config_loader import (
    annotate_text_with_hints,
    extend_prompt,
    load_tts_config,
)


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    sample_path = base_dir / "ttssample.md"
    if not sample_path.exists():
        raise FileNotFoundError(f"Sample text not found: {sample_path}")

    text = sample_path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError("ttssample.md is empty; add some text to synthesize.")

    config = load_tts_config()
    client = OpenAI()

    output_path = base_dir / "openai_tts_output.mp3"
    voice = os.getenv("OPENAI_TTS_VOICE", "verse")
    base_prompt = os.getenv("OPENAI_TTS_STYLE") or config.style_prompts.get("openai")
    if base_prompt:
        # We still derive pacing guidance from the style prompt but do not append it to the text,
        # because OpenAI's TTS engine will literally read any prefix we send.
        prompt = extend_prompt(base_prompt, config.pronunciation_hints, config.sentence_pause_ms)
        print(f"[OpenAI TTS] Using style guidance: {prompt}")

    annotated_text = annotate_text_with_hints(text, config.pronunciation_hints)

    with client.audio.speech.with_streaming_response.create(
        model="gpt-4o-mini-tts",
        voice=voice,
        input=annotated_text,
    ) as response:
        response.stream_to_file(output_path)

    print(f"Saved synthesized speech to {output_path}")


if __name__ == "__main__":
    main()
