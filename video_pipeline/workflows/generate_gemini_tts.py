#!/usr/bin/env python3
"""Generate narration MP3 files from a Gemini TTS YAML file."""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Iterable

import yaml


def load_env_files(paths: list[Path]) -> None:
    for path in paths:
        if not path.exists():
            continue
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def clean_for_gemini_tts(text: str) -> str:
    """Convert a small SSML subset into plain text for Gemini TTS."""
    text = re.sub(r"<sub alias=['\"]([^'\"]+)['\"]>([^<]+)</sub>", r"\1", text)
    text = re.sub(r"<break\s+time=['\"][^'\"]+['\"]\s*/>", "、", text)
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", text).strip()


def load_segments(path: Path) -> list[dict]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    segments = data.get("gemini_tts", {}).get("segments", [])
    if not segments:
        raise SystemExit(f"No gemini_tts.segments found in {path}")
    return segments


def save_pcm_as_mp3(pcm_data: bytes, output_path: Path, speed: float) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    filters = []
    if speed and abs(speed - 1.0) > 0.001:
        filters = ["-filter:a", f"atempo={speed}"]
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "s16le",
        "-ar",
        "24000",
        "-ac",
        "1",
        "-i",
        "-",
        *filters,
        str(output_path),
    ]
    proc = subprocess.run(cmd, input=pcm_data, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.decode("utf-8", errors="ignore"))


def synthesize_segment(client, model: str, voice: str, text: str, output_path: Path, speed: float) -> None:
    last_error: Exception | None = None
    for attempt in range(1, 6):
        try:
            response = client.models.generate_content(
                model=model,
                contents=text,
                config={
                    "response_modalities": ["AUDIO"],
                    "speech_config": {
                        "voice_config": {
                            "prebuilt_voice_config": {"voice_name": voice},
                        },
                    },
                },
            )
            candidate = response.candidates[0] if response.candidates else None
            content = getattr(candidate, "content", None) if candidate else None
            parts = getattr(content, "parts", None) if content else []
            if not parts:
                raise RuntimeError("Gemini TTS returned no audio parts")
            inline_data = getattr(parts[0], "inline_data", None)
            raw_data = getattr(inline_data, "data", b"") if inline_data else b""
            pcm_bytes = base64.b64decode(raw_data) if isinstance(raw_data, str) else raw_data
            if not pcm_bytes:
                raise RuntimeError("Gemini TTS returned empty audio")
            save_pcm_as_mp3(pcm_bytes, output_path, speed)
            return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt < 5:
                time.sleep(min(2.0 * attempt, 8.0))
                continue
    raise RuntimeError(f"Gemini TTS failed after retries: {last_error}")


def generate(
    yaml_path: Path,
    out_dir: Path,
    project_id: str,
    model: str,
    default_voice: str,
    delay: float,
    speed: float,
    limit: int | None,
    only_indices: set[int] | None,
    force: bool,
) -> dict:
    load_env_files([Path(".env"), yaml_path.parents[3] / ".env", Path.home() / ".config/davinciauto/.env"])
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise SystemExit("GEMINI_API_KEY or GOOGLE_API_KEY is not set; cannot generate Gemini TTS audio.")

    try:
        from google import genai  # type: ignore
    except ImportError as exc:
        raise SystemExit("google-genai package is required for Gemini TTS.") from exc

    client = genai.Client(api_key=api_key)
    segments = load_segments(yaml_path)
    if limit:
        segments = segments[:limit]

    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema": "delax_video_gemini_tts_manifest.v0",
        "source_yaml": str(yaml_path),
        "project_id": project_id,
        "model": model,
        "audio_dir": str(out_dir),
        "items": [],
    }

    for index, segment in enumerate(segments, start=1):
        if only_indices and index not in only_indices:
            continue
        output_path = out_dir / f"{project_id}_{index:03d}.mp3"
        text = clean_for_gemini_tts(str(segment.get("text", "")))
        voice = str(segment.get("voice") or default_voice)
        item = {
            "index": index,
            "audio_path": str(output_path),
            "voice": voice,
            "text": text,
            "status": "pending",
        }
        if output_path.exists() and not force:
            item["status"] = "exists"
            manifest["items"].append(item)
            continue
        synthesize_segment(client, model, voice, text, output_path, speed)
        item["status"] = "generated"
        manifest["items"].append(item)
        if delay and index < len(segments):
            time.sleep(delay)

    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Gemini TTS narration MP3 files.")
    parser.add_argument("--yaml", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--model", default=os.getenv("GEMINI_TTS_MODEL", "gemini-2.5-flash-preview-tts"))
    parser.add_argument("--voice", default="kore")
    parser.add_argument("--delay", type=float, default=3.0)
    parser.add_argument("--speed", type=float, default=0.9)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--only-indices", help="Comma-separated 1-based segment indices to synthesize, e.g. 1,15,26")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    only_indices = None
    if args.only_indices:
        only_indices = {int(value.strip()) for value in args.only_indices.split(",") if value.strip()}
    manifest = generate(
        args.yaml,
        args.out_dir,
        args.project_id,
        args.model,
        args.voice,
        args.delay,
        args.speed,
        args.limit,
        only_indices,
        args.force,
    )
    generated = sum(1 for item in manifest["items"] if item["status"] == "generated")
    existing = sum(1 for item in manifest["items"] if item["status"] == "exists")
    print(f"Gemini TTS complete: generated={generated}, existing={existing}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
