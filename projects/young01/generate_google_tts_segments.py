"""Generate Google Cloud TTS audio split into segments for a given input script."""
from __future__ import annotations

import argparse
import os
import re
import sys
from html import escape
from pathlib import Path
from typing import Iterable, List, Tuple
from typing import Literal

from google.cloud import texttospeech

# Ensure we can import the shared TTS config utilities.
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(REPO_ROOT / "experiments"))

from tts_config_loader import (  # type: ignore  # noqa: E402
    PronunciationHint,
    annotate_text_with_hints,
    load_tts_config,
)


TIMESTAMP_PATTERN = re.compile(
    r"^(?P<start>\d{2}:\d{2}:\d{2}:\d{2})\s*-\s*(?P<end>\d{2}:\d{2}:\d{2}:\d{2})$"
)
VOICE_MARKER_PATTERN = re.compile(r"^V\d+")

AdjustMode = Literal["none", "gemini"]


def build_ssml(
    text: str,
    hints: Iterable[PronunciationHint],
    sentence_pause_ms: int,
    paragraph_pause_ms: int | None,
    comma_pause_ms: int,
    quote_pause_ms: int,
) -> str:
    """Create SSML with pronunciation hints and pacing."""
    effective_sentence_pause = max(sentence_pause_ms, 0)
    effective_paragraph_pause = (
        max(paragraph_pause_ms, effective_sentence_pause)
        if paragraph_pause_ms is not None
        else effective_sentence_pause
    )
    effective_comma_pause = max(comma_pause_ms, 0)
    effective_quote_pause = max(quote_pause_ms, 0)

    escaped = escape(text)
    for hint in hints:
        escaped_term = escape(hint.term)
        alias = escape(hint.reading, quote=True)
        escaped = escaped.replace(
            escaped_term,
            f'<sub alias="{alias}">{escaped_term}</sub>',
        )

    sentence_break = (
        f'<break time="{effective_sentence_pause}ms"/>' if effective_sentence_pause else ""
    )
    paragraph_break = (
        f'<break time="{effective_paragraph_pause}ms"/>' if effective_paragraph_pause else sentence_break
    )
    comma_break = f'<break time="{effective_comma_pause}ms"/>' if effective_comma_pause else ""
    quote_break = f'<break time="{effective_quote_pause}ms"/>' if effective_quote_pause else ""

    if sentence_break:
        for punct in ["。", "！", "？"]:
            escaped = escaped.replace(punct, f"{punct}{sentence_break}")
    if comma_break:
        escaped = escaped.replace("、", f"、{comma_break}")
    if paragraph_break:
        escaped = escaped.replace("\n\n", f"{paragraph_break}\n\n")
    if quote_break:
        for quot in ["「", "『", "“"]:
            escaped = escaped.replace(quot, f"{quote_break}{quot}")
        # Insert pause before ASCII quotes when they likely open speech.
        escaped = re.sub(
            r"(^|[\s\n、。！？])(\"+)",
            lambda m: f"{m.group(1)}{quote_break}{m.group(2)}",
            escaped,
        )

    return f"<speak>{escaped}</speak>"


def derive_output_dir(input_path: Path, explicit_output: Path | None) -> Path:
    """Determine where to save generated audio files."""
    if explicit_output is not None:
        return explicit_output
    project_dir = input_path.parent.parent
    default_dir = project_dir / "output" / input_path.stem
    return default_dir


def parse_segments(raw_text: str) -> List[Tuple[str, str]]:
    """Split the input text into narration segments."""
    parts = re.split(r"(?:\r?\n){2,}", raw_text.strip())
    segments: List[Tuple[str, str]] = []

    for part in parts:
        lines = [line.strip() for line in part.splitlines() if line.strip()]
        if not lines:
            continue

        timestamp_slug = None
        content_lines: List[str] = []

        for line in lines:
            ts_match = TIMESTAMP_PATTERN.match(line)
            if ts_match:
                timestamp_slug = ts_match.group("start").replace(":", "")
                continue

            normalized = line.replace(",", "").replace("、", "、").strip()
            if VOICE_MARKER_PATTERN.match(normalized):
                continue

            content_lines.append(line.replace("\r", ""))

        content = " ".join(content_lines).strip()
        content = re.sub(r"\s{2,}", " ", content)

        if not content:
            continue

        segment_id = f"{len(segments) + 1:02d}"
        if timestamp_slug:
            segment_id = f"{segment_id}_{timestamp_slug}"

        segments.append((segment_id, content))

    return segments


def _extract_response_text(response: object) -> str:
    """Best-effort extraction of text from a Gemini response object."""
    text = getattr(response, "text", None)
    if isinstance(text, str) and text.strip():
        return text.strip()

    candidates = getattr(response, "candidates", None)
    if not candidates:
        return ""

    for candidate in candidates:
        content = getattr(candidate, "content", None)
        if not content:
            continue
        parts = getattr(content, "parts", None)
        if not parts:
            continue
        for part in parts:
            part_text = getattr(part, "text", None)
            if isinstance(part_text, str) and part_text.strip():
                return part_text.strip()
    return ""


def adjust_narration(
    text: str,
    mode: AdjustMode,
    style_prompt: str,
) -> str:
    """Optionally rewrite narration prior to synthesis."""
    if mode == "none":
        return text

    if mode == "gemini":
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set; cannot adjust narration with Gemini."
            )
        try:
            from google import genai
        except ImportError as exc:  # pragma: no cover - defensive
            raise RuntimeError(
                "google-generativeai package is required for Gemini adjustments."
            ) from exc

        client = genai.Client(api_key=api_key)
        tone_instruction = (
            f"Desired tone or delivery notes: {style_prompt.strip()}"
            if style_prompt
            else "Deliver in a calm, educational narration style."
        )
        base_instruction = (
            "Rewrite the following Japanese narration so it is natural and smooth when "
            "spoken aloud, while strictly preserving the original meaning, emphasis, "
            "and order. Keep technical terms and names intact. Return only the revised "
            "Japanese text with no additional commentary."
        )
        prompt = f"{base_instruction}\n{tone_instruction}\n---\n{text.strip()}\n---"

        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-pro")
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
        )
        refined = _extract_response_text(response)
        if not refined:
            raise RuntimeError("Gemini narration adjustment returned empty text.")
        return refined

    raise ValueError(f"Unsupported narration adjustment mode: {mode}")


def synthesize_segments(
    input_path: Path,
    output_dir: Path,
    adjust_mode: AdjustMode,
) -> None:
    """Run Google Cloud TTS for each segment."""
    if not input_path.exists():
        raise FileNotFoundError(f"Input script not found: {input_path}")

    raw_text = input_path.read_text(encoding="utf-8")
    segments = parse_segments(raw_text)
    if not segments:
        raise ValueError("No narration segments detected in the input script.")

    output_dir.mkdir(parents=True, exist_ok=True)

    config = load_tts_config()
    hints = config.pronunciation_hints
    base_sentence_pause_ms = max(config.google_break_ms, 0)
    sentence_pause_ms = max(base_sentence_pause_ms, 700)
    paragraph_pause_ms = config.paragraph_pause_ms
    comma_pause_ms = max(int(sentence_pause_ms * 0.35), 120)
    quote_pause_ms = max(int(sentence_pause_ms * 0.5), 160)

    style_prompt = config.style_prompts.get("google", "").strip()
    use_ssml_env = os.getenv("GOOGLE_TTS_USE_SSML")
    if use_ssml_env is not None:
        use_ssml = use_ssml_env not in {"0", "false", "False"}
    else:
        use_ssml = config.google_use_ssml

    client = texttospeech.TextToSpeechClient()

    voice_params = texttospeech.VoiceSelectionParams(
        language_code=os.getenv("GOOGLE_TTS_LANGUAGE", "ja-JP"),
        name=os.getenv("GOOGLE_TTS_VOICE", "ja-JP-Neural2-B"),
    )

    speaking_rate = float(os.getenv("GOOGLE_TTS_SPEAKING_RATE", "1.0"))
    pitch = float(os.getenv("GOOGLE_TTS_PITCH", "0"))
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=speaking_rate,
        pitch=pitch,
    )

    final_text_log: list[str] = []

    for idx, (segment_id, segment_text) in enumerate(segments, start=1):
        adjusted_segment = adjust_narration(segment_text, adjust_mode, style_prompt)
        final_text_log.append(f"[{segment_id}]\n{adjusted_segment}\n")

        if use_ssml:
            ssml = build_ssml(
                adjusted_segment,
                hints,
                sentence_pause_ms,
                paragraph_pause_ms,
                comma_pause_ms,
                quote_pause_ms,
            )
            synthesis_input = texttospeech.SynthesisInput(ssml=ssml)
        else:
            annotated_text = annotate_text_with_hints(adjusted_segment, hints)
            synthesis_input = texttospeech.SynthesisInput(text=annotated_text)

        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice_params,
            audio_config=audio_config,
        )

        output_path = output_dir / f"{input_path.stem}_{segment_id}.mp3"
        output_path.write_bytes(response.audio_content)
        print(f"[{idx}/{len(segments)}] Saved: {output_path}")

    manifest_path = output_dir / f"{input_path.stem}_segments.txt"
    manifest_path.write_text("\n".join(final_text_log), encoding="utf-8")
    print(f"Wrote narration manifest to {manifest_path}")

    print(f"Generated {len(segments)} segment(s) under {output_dir}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate Google Cloud TTS audio segments.")
    parser.add_argument(
        "input_path",
        type=Path,
        help="Path to the narration text file.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory to store generated audio files. Defaults to <project>/output/<input_stem>.",
    )
    parser.add_argument(
        "--adjust-mode",
        choices=["none", "gemini"],
        default="none",
        help="How to pre-process narration text before synthesis (default: none).",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    input_path: Path = args.input_path.resolve()
    output_dir = derive_output_dir(input_path, args.output_dir)

    synthesize_segments(
        input_path=input_path,
        output_dir=output_dir,
        adjust_mode=args.adjust_mode,  # type: ignore[arg-type]
    )


if __name__ == "__main__":
    main()
