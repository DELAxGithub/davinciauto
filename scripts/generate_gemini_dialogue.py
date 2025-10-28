"""Generate selected dialogue segments with Gemini TTS."""
from __future__ import annotations

import base64
import csv
import os
import subprocess
import sys
import argparse
from pathlib import Path
from typing import Dict, Iterable, List

from google import genai
from google.genai import types

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(REPO_ROOT / "experiments"))

from tts_config_loader import annotate_text_with_hints, load_tts_config  # type: ignore


PCM_SAMPLE_RATE = 24_000
PCM_CHANNELS = 1
PCM_SAMPLE_WIDTH = 2  # bytes


def _ensure_env_var(name: str) -> None:
    if os.getenv(name):
        return
    env_path = REPO_ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if not line or line.strip().startswith("#"):
                continue
            if line.startswith(f"{name}="):
                _, value = line.split("=", 1)
                os.environ[name] = value.strip()
                return


def _ensure_gemini_client() -> genai.Client:
    _ensure_env_var("GEMINI_API_KEY")
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set; cannot call Gemini TTS.")
    return genai.Client(api_key=api_key)


def _load_segments(csv_path: Path) -> Dict[int, Dict[str, str]]:
    segments: Dict[int, Dict[str, str]] = {}
    with csv_path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                idx = int(row.get("no", 0))
            except ValueError:
                continue
            segments[idx] = row
    return segments


def _pick_voice(config: Dict[str, any], character: str) -> str:
    overrides = config.get("voice_overrides", {})
    if isinstance(overrides, dict):
        voice = overrides.get(character)
        if voice:
            return voice
        voice = overrides.get("default")
        if voice:
            return voice
    return config.get("voice_name", "Kore")


def _build_prompt(settings: Dict[str, any], character: str, scene: str | None, text: str) -> str:
    base_instruction = settings.get("base_instruction", "").strip()
    style_prompts = settings.get("style_prompts", {}) if isinstance(settings.get("style_prompts"), dict) else {}
    style_prompt = style_prompts.get(character) or style_prompts.get("default", "")
    lines: List[str] = []
    if base_instruction:
        lines.append(base_instruction)
    if style_prompt:
        lines.append(style_prompt)
    if scene:
        lines.append(f"Scene context: {scene}")
    lines.append("---")
    lines.append(text.strip())
    lines.append("---")
    return "\n".join(lines)


def _save_mp3(pcm_data: bytes, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "s16le",
        "-ar",
        str(PCM_SAMPLE_RATE),
        "-ac",
        str(PCM_CHANNELS),
        "-i",
        "-",
        str(output_path),
    ]
    proc = subprocess.run(cmd, input=pcm_data, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg conversion failed: {proc.stderr.decode('utf-8', errors='ignore')}")


def synthesize_segments(segment_ids: Iterable[int], *, output_dir: Path, csv_path: Path) -> None:
    if not os.getenv("TTS_CONFIG_PATHS"):
        default_paths = [
            "orion/config/global.yaml",
            "projects/OrionEp7/inputs/orionep7_tts.yaml",
        ]
        legacy_path = Path("experiments/tts_config/global.yaml")
        if legacy_path.exists():
            default_paths.insert(1, "experiments/tts_config/global.yaml")
        os.environ["TTS_CONFIG_PATHS"] = ",".join(default_paths)
    config = load_tts_config()
    raw_config = config.raw.get("google_tts", {}) if isinstance(config.raw, dict) else {}
    gemini_settings = raw_config.get("gemini_dialogue", {}) if isinstance(raw_config, dict) else {}
    if not gemini_settings.get("enabled"):
        raise RuntimeError("Gemini dialogue synthesis is not enabled in configuration.")

    if not csv_path.exists():
        raise FileNotFoundError(f"Script CSV not found: {csv_path}")

    segments = _load_segments(csv_path)
    client = _ensure_gemini_client()

    output_dir.mkdir(parents=True, exist_ok=True)

    for seg_id in segment_ids:
        row = segments.get(seg_id)
        if not row:
            print(f"[Gemini] Skip {seg_id}: segment not found in CSV")
            continue

        character = row.get("character", "ナレーター")
        if character == "ナレーター":
            print(f"[Gemini] Skip {seg_id}: narration handled by Google TTS")
            continue

        text = row.get("text", "").strip()
        if not text:
            print(f"[Gemini] Skip {seg_id}: empty text")
            continue

        scene = row.get("scene") or None
        annotated = annotate_text_with_hints(text, config.pronunciation_hints)
        prompt = _build_prompt(gemini_settings, character, scene, annotated)

        voice_name = _pick_voice(gemini_settings, character)
        model_name = gemini_settings.get("tts_model") or os.getenv("GEMINI_TTS_MODEL", "gemini-2.5-flash-preview-tts")

        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
                    )
                ),
            ),
        )

        parts = (
            response.candidates[0].content.parts
            if response.candidates and response.candidates[0].content
            else []
        )
        if not parts:
            raise RuntimeError(f"Gemini returned no audio for segment {seg_id}")

        inline_data = parts[0].inline_data
        raw_data = inline_data.data
        pcm_bytes = base64.b64decode(raw_data) if isinstance(raw_data, str) else raw_data
        if not pcm_bytes:
            raise RuntimeError(f"Gemini returned empty audio for segment {seg_id}")

        output_name = f"OrionEp7_{seg_id:03d}.mp3"
        output_path = output_dir / output_name
        _save_mp3(pcm_bytes, output_path)
        print(f"[Gemini] Saved {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate dialogue segments with Gemini TTS.")
    parser.add_argument("segments", nargs="+", help="Segment numbers or comma-separated lists (e.g., 7 9 10-12).")
    parser.add_argument(
        "--dest",
        default="projects/OrionEp7/outputs/audio_test",
        help="Destination directory for generated audio (default: %(default)s)",
    )
    parser.add_argument(
        "--csv",
        default="projects/OrionEp7/inputs/orion_ep7_script.csv",
        help="Path to narration CSV (default: %(default)s)",
    )

    args = parser.parse_args()

    try:
        ids: List[int] = []
        for token in args.segments:
            for part in token.split(","):
                part = part.strip()
                if not part:
                    continue
                if "-" in part:
                    start_str, end_str = part.split("-", 1)
                    start = int(start_str)
                    end = int(end_str)
                    ids.extend(range(start, end + 1))
                else:
                    ids.append(int(part))

        csv_path = Path(args.csv)
        output_dir = Path(args.dest)
        synthesize_segments(ids, output_dir=output_dir, csv_path=csv_path)
    except Exception as exc:  # pragma: no cover - CLI safety
        print(f"Error: {exc}")
        sys.exit(1)
