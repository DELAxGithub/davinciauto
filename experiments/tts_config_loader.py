"""Utility functions for loading shared TTS configuration."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List
import os
import sys

import yaml


DEFAULT_STYLE_PROMPTS = {
    "openai": (
        "Please read the following text slowly and warmly, with clear articulation "
        "suitable for shared educational storytelling."
    ),
    "gemini": (
        "Please narrate the script in a composed, insightful tone with deliberate pacing "
        "and gentle engagement."
    ),
    "google": (
        "Deliver the narration with a calm, educational tone, keeping the cadence steady "
        "and welcoming."
    ),
}


@dataclass(frozen=True)
class PronunciationHint:
    term: str
    reading: str


@dataclass(frozen=True)
class TTSConfig:
    pronunciation_hints: List[PronunciationHint]
    sentence_pause_ms: int
    paragraph_pause_ms: int | None
    style_prompts: Dict[str, str]
    google_use_ssml: bool
    google_break_ms: int


def load_tts_config() -> TTSConfig:
    """Load TTS configuration from YAML files listed in `TTS_CONFIG_PATHS`."""
    config = {
        "pronunciation_hints": [],
        "pacing": {
            "sentence_pause_ms": 500,
            "paragraph_pause_ms": None,
        },
        "style_prompts": DEFAULT_STYLE_PROMPTS.copy(),
        "google_tts": {
            "use_ssml": True,
            "break_ms": 500,
        },
    }

    for path in _iter_config_paths():
        data = _read_yaml(path)
        if not data:
            continue
        _merge_config(config, data)

    hints = _dedupe_hints(config.get("pronunciation_hints", []))
    pacing = config.get("pacing", {})
    sentence_pause_ms = _ensure_positive_int(pacing.get("sentence_pause_ms", 500), fallback=500)
    paragraph_pause_ms = pacing.get("paragraph_pause_ms")
    if paragraph_pause_ms is not None:
        paragraph_pause_ms = _ensure_positive_int(paragraph_pause_ms, fallback=None)

    styles = DEFAULT_STYLE_PROMPTS.copy()
    styles.update(config.get("style_prompts", {}))

    google_settings = config.get("google_tts", {})
    google_use_ssml = bool(google_settings.get("use_ssml", True))
    google_break_ms = _ensure_positive_int(
        google_settings.get("break_ms", sentence_pause_ms), fallback=sentence_pause_ms
    )

    return TTSConfig(
        pronunciation_hints=hints,
        sentence_pause_ms=sentence_pause_ms,
        paragraph_pause_ms=paragraph_pause_ms,
        style_prompts=styles,
        google_use_ssml=google_use_ssml,
        google_break_ms=google_break_ms,
    )


def annotate_text_with_hints(text: str, hints: Iterable[PronunciationHint]) -> str:
    updated = text
    for hint in hints:
        if hint.term in updated:
            updated = updated.replace(hint.term, f"{hint.term}（{hint.reading}）")
    return updated


def extend_prompt(prompt: str, hints: Iterable[PronunciationHint], pause_ms: int) -> str:
    additions: List[str] = []
    effective_pause = max(pause_ms, 0)
    hints_list = list(hints)
    if hints_list:
        formatted = "、".join(f"「{hint.term}」は「{hint.reading}」" for hint in hints_list)
        additions.append(f"Pronounce the following terms carefully: {formatted}.")
    if effective_pause:
        seconds = effective_pause / 1000
        additions.append(
            "Add roughly " + f"{seconds:.1f}" + " second pause after Japanese punctuation such as '。' and '、'."
        )
    if additions:
        return prompt.rstrip() + " " + " ".join(additions)
    return prompt


def _iter_config_paths() -> Iterable[Path]:
    raw = os.getenv("TTS_CONFIG_PATHS", "")
    if not raw.strip():
        return []
    repo_root = Path(__file__).resolve().parent.parent
    for part in raw.split(","):
        trimmed = part.strip()
        if not trimmed:
            continue
        path = Path(trimmed)
        if not path.is_absolute():
            path = (repo_root / path).resolve()
        yield path


def _read_yaml(path: Path) -> Dict:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"[TTS config] Skipping missing config: {path}", file=sys.stderr)
        return {}
    data = yaml.safe_load(text) or {}
    if not isinstance(data, dict):
        return {}
    return data


def _merge_config(base: Dict, incoming: Dict) -> None:
    for key, value in incoming.items():
        if key == "pronunciation_hints":
            base.setdefault(key, [])
            if isinstance(value, list):
                base[key].extend(item for item in value if isinstance(item, dict))
        elif isinstance(value, dict):
            target = base.setdefault(key, {})
            if isinstance(target, dict):
                _merge_config(target, value)
            else:
                base[key] = value
        else:
            base[key] = value


def _dedupe_hints(items: List[Dict]) -> List[PronunciationHint]:
    merged: Dict[str, str] = {}
    for item in items:
        term = str(item.get("term", "")).strip()
        reading = str(item.get("reading", "")).strip()
        if term and reading:
            merged[term] = reading
    return [PronunciationHint(term=term, reading=reading) for term, reading in merged.items()]


def _ensure_positive_int(value, fallback: int | None) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return fallback if fallback is not None else 0
    return max(number, 0)
