"""Helpers for BGM/SE生成（ElevenLabs API を利用）。"""

from __future__ import annotations

import csv
import json
import os
import pathlib
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple


class BGMGenerationError(RuntimeError):
    """Base exception for BGM/SE 自動生成エラー。"""


class ElevenLabsDependencyError(BGMGenerationError):
    """Raised when elevenlabs SDK is missing."""


class ElevenLabsAPIKeyError(BGMGenerationError):
    """Raised when ELEVENLABS_API_KEY is not configured."""


def _load_api_key(explicit: Optional[str] = None) -> str:
    if explicit:
        return explicit
    key = os.getenv("ELEVENLABS_API_KEY")
    if key:
        return key
    env_path = pathlib.Path(".env")
    if env_path.exists():
        pattern = re.compile(r"^ELEVENLABS_API_KEY\s*=\s*(.+)$")
        for line in env_path.read_text(encoding="utf-8").splitlines():
            match = pattern.match(line.strip())
            if match:
                candidate = match.group(1).split("#", 1)[0].strip().strip('"').strip("'")
                if candidate:
                    return candidate
    raise ElevenLabsAPIKeyError("ELEVENLABS_API_KEY is not set.")


def _tc_to_seconds(tc: str) -> float:
    parts = tc.strip().split(":")
    if len(parts) == 3:
        hours, minutes, seconds = parts
        return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    if len(parts) == 2:
        minutes, seconds = parts
        return int(minutes) * 60 + float(seconds)
    return float(parts[0])


def _project_end_seconds(project_dir: pathlib.Path) -> float:
    project = project_dir.name
    srt_path = project_dir / "テロップ類" / "SRT" / f"{project}_Sub_follow.srt"
    if srt_path.exists():
        text = srt_path.read_text(encoding="utf-8", errors="ignore")
        matches = re.findall(r"(\d\d:\d\d:\d\d,\d\d\d)\s*-->\s*(\d\d:\d\d:\d\d,\d\d\d)", text)
        if matches:
            _, end_tc = matches[-1]
            hh, mm, rest = end_tc.split(":")
            ss, ms = rest.split(",")
            return int(hh) * 3600 + int(mm) * 60 + int(ss) + int(ms) / 1000.0

    csv_path = project_dir / "exports" / "timelines" / f"{project}_timeline_v1.csv"
    if csv_path.exists():
        with csv_path.open("r", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        if rows:
            last = rows[-1]
            start = float(last.get("start_sec") or 0)
            duration = float(last.get("duration_sec") or 0)
            return max(start + duration + 1.0, 1.0)

    return 600.0


def _consume_audio_chunks(chunks: Iterable[bytes]) -> bytes:
    return b"".join(chunk for chunk in chunks if isinstance(chunk, (bytes, bytearray)))


def generate_bgm_and_se(
    plan_path: pathlib.Path,
    *,
    api_key: Optional[str] = None,
    only: Optional[str] = None,
) -> Tuple[List[pathlib.Path], List[pathlib.Path], List[str]]:
    """Generate BGM / SE assets from a plan JSON."""

    try:
        from elevenlabs import ElevenLabs
    except Exception as exc:  # pragma: no cover - optional dependency
        raise ElevenLabsDependencyError(
            "elevenlabs package is required for BGM/SE generation. Install it via `pip install elevenlabs`."
        ) from exc

    plan_path = pathlib.Path(plan_path).expanduser().resolve()
    if not plan_path.exists():
        raise BGMGenerationError(f"Plan file not found: {plan_path}")

    payload = json.loads(plan_path.read_text(encoding="utf-8"))
    sections: List[Dict[str, Any]] = payload.get("sections", [])
    if not sections:
        raise BGMGenerationError("Plan JSON does not contain any sections.")

    project_name = payload.get("project") or plan_path.parent.parent.name
    project_dir = plan_path.parent.parent
    if project_dir.name != project_name:
        alt_dir = pathlib.Path("projects") / project_name
        if alt_dir.exists():
            project_dir = alt_dir.resolve()

    project_dir.mkdir(parents=True, exist_ok=True)
    bgm_dir = project_dir / "サウンド類" / "BGM"
    se_dir = project_dir / "サウンド類" / "SE"
    bgm_dir.mkdir(parents=True, exist_ok=True)
    se_dir.mkdir(parents=True, exist_ok=True)

    for section in sections:
        section["start_sec"] = _tc_to_seconds(section.get("start_tc", "0"))

    sections.sort(key=lambda s: s.get("start_sec", 0.0))
    project_end = _project_end_seconds(project_dir)
    for index, section in enumerate(sections):
        if index + 1 < len(sections):
            section["end_sec"] = sections[index + 1].get("start_sec", project_end)
        else:
            section["end_sec"] = project_end
        section["length_ms"] = max(1000, int(round((section["end_sec"] - section["start_sec"]) * 1000)))

    key = _load_api_key(api_key)
    client = ElevenLabs(api_key=key)

    only_mode = only.lower() if only else None
    do_bgm = only_mode in (None, "bgm")
    do_se = only_mode in (None, "se", "sfx")

    bgm_saved: List[pathlib.Path] = []
    se_saved: List[pathlib.Path] = []
    errors: List[str] = []

    if do_bgm:
        for idx, section in enumerate(sections, 1):
            prompt = (section.get("bgm_prompt") or "").strip()
            if not prompt:
                continue
            try:
                audio = client.music.compose(prompt=prompt, music_length_ms=int(section["length_ms"]))
                chunk_bytes = audio if isinstance(audio, (bytes, bytearray)) else _consume_audio_chunks(audio)
                out_path = bgm_dir / f"{project_name}_BGM{idx:02d}_{section.get('label','')}.mp3"
                out_path.write_bytes(chunk_bytes)
                bgm_saved.append(out_path)
            except Exception as exc:  # pragma: no cover - API failures
                errors.append(f"BGM section {idx}: {exc}")

    if do_se:
        for idx, section in enumerate(sections, 1):
            cues = section.get("sfx") or []
            for cue_index, cue in enumerate(cues, 1):
                prompt = (cue.get("prompt") or "").strip()
                if not prompt:
                    continue
                try:
                    duration = float(cue.get("duration_sec", 1.6) or 1.6)
                    try:
                        audio = client.sound_effects.convert(text=prompt, duration_seconds=duration)  # type: ignore[attr-defined]
                    except Exception:
                        audio = client.text_to_sound_effects.convert(text=prompt, duration_seconds=duration)  # type: ignore[attr-defined]
                    chunk_bytes = audio if isinstance(audio, (bytes, bytearray)) else _consume_audio_chunks(audio)
                    timecode = (cue.get("time_tc") or "00:00:00").replace(":", "-")
                    label = cue.get("label") or f"SFX{idx:02d}_{cue_index:02d}"
                    out_path = se_dir / f"{project_name}_SE{idx:02d}_{timecode}_{label}.mp3"
                    out_path.write_bytes(chunk_bytes)
                    se_saved.append(out_path)
                except Exception as exc:  # pragma: no cover - API failures
                    errors.append(f"SE section {idx}-{cue_index}: {exc}")

    return bgm_saved, se_saved, errors


__all__ = [
    "BGMGenerationError",
    "ElevenLabsDependencyError",
    "ElevenLabsAPIKeyError",
    "generate_bgm_and_se",
]
