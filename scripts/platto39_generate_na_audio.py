#!/usr/bin/env python3
"""Generate rough EP039 narration audio from Doc-to-DaVinci IR.

The preferred path mirrors shadow_master: Google Cloud TTS via gcloud + REST.
If that fails, fall back to macOS `say` and convert AIFF to WAV with afconvert.
"""

from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
import wave
from pathlib import Path
from typing import Any


GOOGLE_TTS_URL = "https://texttospeech.googleapis.com/v1/text:synthesize"
GOOGLE_QUOTA_PROJECT = "texttospeech-392819"
GOOGLE_VOICE = "ja-JP-Chirp3-HD-Charon"
CUSTOM_DATA_PREFIX = "doc-to-davinci-v0:"


def run_capture(cmd: list[str], timeout: int = 60) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def load_na_entries(ir_json: Path) -> list[dict[str, Any]]:
    ir = json.loads(ir_json.read_text(encoding="utf-8"))
    entries = []
    for entry in ir.get("entries", []):
        speaker = str(entry.get("speaker") or "")
        text = str(entry.get("transcript") or "").strip()
        if speaker.startswith("NA") and text:
            entries.append(entry)
    return entries


def google_token() -> str:
    result = run_capture(["gcloud", "auth", "print-access-token"])
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "gcloud auth failed").strip())
    return result.stdout.strip()


def google_synthesize(token: str, text: str) -> bytes:
    body = json.dumps(
        {
            "input": {"text": text},
            "voice": {"languageCode": "ja-JP", "name": GOOGLE_VOICE},
            "audioConfig": {"audioEncoding": "LINEAR16"},
        },
        ensure_ascii=False,
    )
    result = subprocess.run(
        [
            "curl",
            "--silent",
            "--show-error",
            "--fail-with-body",
            "-X",
            "POST",
            GOOGLE_TTS_URL,
            "-H",
            f"Authorization: Bearer {token}",
            "-H",
            "Content-Type: application/json",
            "-H",
            f"x-goog-user-project: {GOOGLE_QUOTA_PROJECT}",
            "-d",
            body,
        ],
        capture_output=True,
        text=True,
        timeout=90,
    )
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "curl failed").strip()[:500])
    payload = json.loads(result.stdout)
    return base64.b64decode(payload["audioContent"])


def say_synthesize(text: str, wav_path: Path, voice: str) -> None:
    tmp_aiff = wav_path.with_suffix(".aiff")
    say_cmd = ["say"]
    if voice:
        say_cmd.extend(["-v", voice])
    say_cmd.extend(["-o", str(tmp_aiff), text])
    result = subprocess.run(say_cmd, capture_output=True, text=True, timeout=180)
    if result.returncode != 0 and voice:
        result = subprocess.run(["say", "-o", str(tmp_aiff), text], capture_output=True, text=True, timeout=180)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "say failed").strip())

    convert = subprocess.run(
        ["afconvert", "-f", "WAVE", "-d", "LEI16", str(tmp_aiff), str(wav_path)],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if convert.returncode != 0:
        raise RuntimeError((convert.stderr or convert.stdout or "afconvert failed").strip())
    tmp_aiff.unlink(missing_ok=True)


def write_manifest(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def wav_duration(path: Path) -> float:
    try:
        with wave.open(str(path), "rb") as handle:
            rate = handle.getframerate()
            frames = handle.getnframes()
    except Exception:  # noqa: BLE001
        return 0.0
    if rate <= 0:
        return 0.0
    return frames / rate


def generate(ir_json: Path, out_dir: Path, prefer: str, voice: str) -> dict[str, Any]:
    entries = load_na_entries(ir_json)
    out_dir.mkdir(parents=True, exist_ok=True)

    token: str | None = None
    google_error: str | None = None
    if prefer in {"auto", "google"}:
        try:
            token = google_token()
        except Exception as exc:  # noqa: BLE001
            google_error = str(exc)
            if prefer == "google":
                raise

    manifest = []
    generated = 0
    fallback = 0
    for entry in entries:
        speaker = str(entry["speaker"])
        text = str(entry["transcript"]).strip()
        wav_path = out_dir / f"{speaker}.wav"
        method = "google"
        error = None
        existing_duration = wav_duration(wav_path) if wav_path.exists() else 0.0
        if existing_duration > 0.0:
            manifest.append(
                {
                    "na_id": speaker,
                    "text": text,
                    "wav": str(wav_path),
                    "method": "existing",
                    "duration_seconds": existing_duration,
                    "doc_row_id": entry.get("doc_row_id"),
                    "custom_data": f"{CUSTOM_DATA_PREFIX}{entry.get('doc_row_id')}",
                }
            )
            continue

        try:
            if token and prefer in {"auto", "google"}:
                wav_path.write_bytes(google_synthesize(token, text))
            else:
                raise RuntimeError(google_error or "google disabled")
        except Exception as exc:  # noqa: BLE001
            if prefer == "google":
                raise
            method = "mac_say"
            error = str(exc)
            say_synthesize(text, wav_path, voice)
            fallback += 1

        generated += 1
        manifest.append(
            {
                "na_id": speaker,
                "text": text,
                "wav": str(wav_path),
                "method": method,
                "duration_seconds": wav_duration(wav_path),
                "fallback_reason": error,
                "doc_row_id": entry.get("doc_row_id"),
                "custom_data": f"{CUSTOM_DATA_PREFIX}{entry.get('doc_row_id')}",
            }
        )

    manifest_path = out_dir / "na_audio_manifest.json"
    write_manifest(manifest_path, manifest)
    return {
        "ir_json": str(ir_json),
        "out_dir": str(out_dir),
        "na_entries": len(entries),
        "generated_or_existing": len(manifest),
        "newly_generated": generated,
        "fallback_to_mac_say": fallback,
        "manifest": str(manifest_path),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate rough EP039 NA WAV files from desired_timeline_ir.json.")
    parser.add_argument("ir_json", type=Path)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--prefer", choices=["auto", "google", "mac"], default="auto")
    parser.add_argument("--voice", default="Eddy (日本語（日本）)", help="macOS say voice used for fallback")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        print(json.dumps(generate(args.ir_json, args.out_dir, args.prefer, args.voice), ensure_ascii=False, indent=2))
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
