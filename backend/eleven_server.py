#!/usr/bin/env python3
"""
Local ElevenLabs synthesis worker.

Run:
  export ELEVENLABS_API_KEY=sk-...  # your key
  uvicorn backend.eleven_server:app --host 127.0.0.1 --port 8787 --reload

POST /api/eleven/synthesize
  {
    "project_dir": "/abs/path/to/project",            # will save under exports/audio/narr
    "model_id": "eleven_turbo_v2_5",                 # optional (overrides item.model_id)
    "items": [ {"line":1, "text":"...", "voice":"Rachel"}, ... ]
  }

Saves:
  {project_dir}/exports/audio/narr/{line:04d}_{voice}.mp3
"""
from __future__ import annotations

import os
import re
import pathlib
from typing import List, Optional, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

try:
    from elevenlabs import ElevenLabs
except Exception as e:  # pragma: no cover
    ElevenLabs = None  # type: ignore


API_KEY = os.getenv("ELEVENLABS_API_KEY", "")


class Item(BaseModel):
    line: int
    text: str
    voice: Optional[str] = None
    role: Optional[str] = None
    character: Optional[str] = None
    gender: Optional[str] = None  # 'male' | 'female'
    model_id: Optional[str] = None
    output_format: str = "mp3_44100_128"  # ElevenLabs SDK output format


class Job(BaseModel):
    project_dir: str
    items: List[Item]
    model_id: Optional[str] = None
    # Default to category-based path that maps to Resolve bins
    # Default to category-based path that maps to Resolve bins. Can be overridden.
    output_subdir: str = "サウンド類/Narration"


# === Music composition ===
class MusicItem(BaseModel):
    label: Optional[str] = None
    prompt: str
    length_ms: int
    output_format: str = "mp3_44100_128"


class MusicJob(BaseModel):
    project_dir: str
    items: List[MusicItem]
    output_subdir: str = "サウンド類/BGM"
    output_subdir: Optional[str] = "サウンド類/BGM"


# === Sound Effects (SFX) ===
class SfxItem(BaseModel):
    label: Optional[str] = None
    prompt: str
    duration_sec: Optional[float] = None  # optional; model can auto
    looping: Optional[bool] = None
    prompt_influence: Optional[float] = None
    output_format: str = "mp3_44100_128"


class SfxJob(BaseModel):
    project_dir: str
    items: List[SfxItem]
    output_subdir: str = "サウンド類/SE"
    output_subdir: Optional[str] = "サウンド類/SE"


app = FastAPI(title="ElevenLabs Worker", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def ensure_dir(p: pathlib.Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def sanitize_name(s: str) -> str:
    return re.sub(r"[^\w\-\.]+", "_", s.strip())[:48] or "voice"


def parse_bitrate_kbps(output_format: str) -> Optional[int]:
    """Parse bitrate from formats like 'mp3_44100_128' or 'opus_48000_64'."""
    try:
        parts = (output_format or "").split("_")
        if len(parts) >= 3:
            kbps = int(parts[-1])
            return kbps
        return None
    except Exception:
        return None


def estimate_duration_seconds(file_path: pathlib.Path, output_format: str) -> Optional[float]:
    """Estimate duration using file size and declared bitrate when possible (CBR mp3/opus)."""
    try:
        kbps = parse_bitrate_kbps(output_format)
        if kbps:
            size_bytes = file_path.stat().st_size
            bps = kbps * 1000
            dur = (size_bytes * 8.0) / float(bps)
            return round(dur, 3)
    except Exception:
        pass
    return None


# === Voice assignment policy (fixed mapping) ===
# Provided custom voices (IDs)
VOICE_ISHIBASHI = "Mv8AjrYZCBkdsmDHNwcB"  # 引用 男声 1 (Ishibashi)
VOICE_HEYHEY    = "YFkT3BsfOFWBx3jfroxH"  # 登場人物 若手 男声 (Heyhey)
VOICE_OTANI     = "3JDquces8E8bkmvbh6Bc"  # 引用 男声 2 (Otani)
VOICE_SHOHEI    = "8FuuqoKHuM48hIEwni5e"  # 引用 男声 3 (Shohei)
VOICE_SHIZUKA   = "WQz3clzUdMqvBf0jswZQ"  # ナレーション 女声 (Shizuka)
VOICE_HATAKE    = "sRYzP8TwEiiqAWebdYPJ"  # 上司系 男声 (Voiceactor Hatakekohei)
VOICE_FUMI      = "PmgfHCGeS5b7sH90BOOJ"  # 登場人物 女声 1 (Fumi)
VOICE_JESSICA   = "flHkNRp1BlvT73UL6gyz"  # 登場人物 女声 2 (Jessica)

# Role-based defaults (IDs). Keep only clear, single-choice roles here.
ROLE_DEFAULT_VOICE = {
    "NA": VOICE_SHIZUKA,  # Narration
}

# Pools for rotation / stable assignment
QUOTE_VOICES = [VOICE_ISHIBASHI, VOICE_OTANI, VOICE_SHOHEI]
DIALOGUE_VOICES = [VOICE_HEYHEY, VOICE_HATAKE, VOICE_FUMI, VOICE_JESSICA]
MALE_VOICES = [VOICE_HEYHEY, VOICE_HATAKE, VOICE_ISHIBASHI, VOICE_OTANI, VOICE_SHOHEI]
FEMALE_VOICES = [VOICE_FUMI, VOICE_JESSICA, VOICE_SHIZUKA]

# Map voice IDs to human-friendly nicknames for filenames/metadata
VOICE_ID_TO_LABEL = {
    VOICE_ISHIBASHI: "Ishibashi",
    VOICE_HEYHEY: "Heyhey",
    VOICE_OTANI: "Otani",
    VOICE_SHOHEI: "Shohei",
    VOICE_SHIZUKA: "Shizuka",
    VOICE_HATAKE: "Voiceactor Hatakekohei",
    VOICE_FUMI: "Fumi",
    VOICE_JESSICA: "Jessica",
}


def stable_pick_from(name: str, choices: list[str]) -> str:
    if not choices:
        return "Rachel"
    h = 0
    for ch in name:
        h = (h * 131 + ord(ch)) & 0xFFFFFFFF
    return choices[h % len(choices)]


def choose_voice_name(it: Item) -> str:
    # If explicitly set in the item, honor it
    if it.voice and it.voice.strip():
        return it.voice.strip()
    role = (it.role or "").strip()
    norm = role.upper()
    # Gender hint overrides (if present)
    g = (it.gender or "").strip().lower()
    if g == "male":
        pool = QUOTE_VOICES if norm in ("Q",) or it.role in ("引用",) else DIALOGUE_VOICES
        key = (it.character or f"{it.line}")
        return stable_pick_from(key, pool if pool else MALE_VOICES)
    if g == "female":
        pool = [VOICE_FUMI, VOICE_JESSICA] if norm in ("DL", "DIALOGUE") or it.role in ("セリフ",) else [VOICE_SHIZUKA]
        key = (it.character or f"{it.line}")
        return stable_pick_from(key, pool if pool else FEMALE_VOICES)

    # Fixed role-based mapping first
    if role in ROLE_DEFAULT_VOICE:
        return ROLE_DEFAULT_VOICE[role]
    # Quote family → rotate within QUOTE_VOICES
    if norm == "Q" or role in ("引用",):
        key = (it.character or f"{it.line}")
        return stable_pick_from(key, QUOTE_VOICES)
    # Dialogue family → rotate within DIALOGUE_VOICES
    if norm in ("DL", "DIALOGUE") or role in ("セリフ",):
        key = (it.character or f"{it.line}")
        return stable_pick_from(key, DIALOGUE_VOICES)
    # Character-based fallback
    char = (it.character or "").strip()
    if char:
        return stable_pick_from(char, DIALOGUE_VOICES)
    # Default fallback narration voice
    return VOICE_SHIZUKA


def resolve_voice_id(client: ElevenLabs, name_or_id: str) -> str:
    # If it already looks like an id (uuid-ish), return as is
    if re.fullmatch(r"[a-fA-F0-9]{8,}", name_or_id.replace("-", "")):
        return name_or_id
    # Otherwise, best-effort lookup by name (case-insensitive)
    try:
        voices_resp: Any = client.voices.get_all()
        candidates = getattr(voices_resp, "voices", None) or voices_resp
        name_l = name_or_id.strip().lower()
        for v in candidates or []:
            v_name = getattr(v, "name", None)
            if v_name is None and isinstance(v, dict):
                v_name = v.get("name")
            if (v_name or "").strip().lower() == name_l:
                v_id = getattr(v, "voice_id", None)
                if v_id is None and isinstance(v, dict):
                    v_id = v.get("voice_id")
                if v_id:
                    return v_id
    except Exception:
        # ignore and fall through
        pass
    # Default fallback voice
    return name_or_id or "Rachel"


@app.post("/api/eleven/synthesize")
def synthesize(job: Job):  # type: ignore
    if ElevenLabs is None:
        return {"ok": False, "error": "elevenlabs SDK not installed"}
    if not API_KEY:
        return {"ok": False, "error": "ELEVENLABS_API_KEY missing"}

    client = ElevenLabs(api_key=API_KEY)

    base = pathlib.Path(job.project_dir).expanduser().resolve()
    project_name = base.name
    out_dir = base / job.output_subdir
    out_dir = base / (job.output_subdir or "サウンド類/BGM")
    ensure_dir(out_dir)

    saved = []
    errors = []
    # Round-robin indices (order of appearance per request)
    male_idx = 0
    female_idx = 0

    for it in job.items:
        text = (it.text or "").strip()
        if not text:
            continue
        model_id = it.model_id or job.model_id or "eleven_v3"
        # Determine voice by priority:
        # 1) explicit item.voice (name or id)
        # 2) gender-guided round-robin pools (male/female)
        # 3) role defaults (NA -> Shizuka; quotes/dialogue -> male pool)
        # 4) fallback Shizuka
        voice_choice: str
        if it.voice and it.voice.strip():
            voice_choice = it.voice.strip()
        else:
            g = (it.gender or "").strip().lower()
            role = (it.role or "").strip()
            norm = role.upper()
            if g == "male":
                pool = MALE_VOICES
                voice_choice = pool[male_idx % len(pool)]
                male_idx += 1
            elif g == "female":
                pool = FEMALE_VOICES
                voice_choice = pool[female_idx % len(pool)]
                female_idx += 1
            else:
                if norm == "NA":
                    voice_choice = VOICE_SHIZUKA
                elif norm in ("Q",) or role in ("引用",):
                    pool = MALE_VOICES
                    voice_choice = pool[male_idx % len(pool)]
                    male_idx += 1
                elif norm in ("DL", "DIALOGUE") or role in ("セリフ",):
                    pool = MALE_VOICES
                    voice_choice = pool[male_idx % len(pool)]
                    male_idx += 1
                else:
                    voice_choice = VOICE_SHIZUKA
        try:
            voice_id = resolve_voice_id(client, voice_choice)
            voice_label = VOICE_ID_TO_LABEL.get(voice_id) or voice_choice
            voice_name = sanitize_name(voice_label)
            kwargs = dict(
                voice_id=voice_id,
                output_format=it.output_format,
                model_id=model_id,
                text=text,
            )
            # optimize_streaming_latency is not supported on v3 alpha
            if "v3" not in (model_id or ""):
                kwargs["optimize_streaming_latency"] = "0"
            audio = client.text_to_speech.convert(**kwargs)
            fname = f"{project_name}_{it.line:04d}_{voice_name}.mp3"
            fpath = out_dir / fname
            with open(fpath, "wb") as f:
                if isinstance(audio, (bytes, bytearray)):
                    f.write(audio)
                else:
                    for chunk in audio:
                        if isinstance(chunk, (bytes, bytearray)):
                            f.write(chunk)
            dur = estimate_duration_seconds(fpath, it.output_format)
            saved.append({"line": it.line, "path": str(fpath), "duration": dur, "voice": voice_label, "voice_id": voice_id})
        except Exception as e:
            errors.append({"line": it.line, "error": str(e)})

    return {"ok": len(errors) == 0, "saved": saved, "errors": errors}


@app.get("/api/health")
def health():  # type: ignore
    return {"ok": True}


@app.post("/api/music/compose")
def compose_music(job: MusicJob):  # type: ignore
    if ElevenLabs is None:
        return {"ok": False, "error": "elevenlabs SDK not installed"}
    if not API_KEY:
        return {"ok": False, "error": "ELEVENLABS_API_KEY missing"}

    client = ElevenLabs(api_key=API_KEY)

    base = pathlib.Path(job.project_dir).expanduser().resolve()
    project_name = base.name
    out_dir = base / job.output_subdir
    out_dir = base / (job.output_subdir or "サウンド類/SE")
    ensure_dir(out_dir)

    saved = []
    errors = []

    for idx, it in enumerate(job.items, 1):
        prompt = (it.prompt or "").strip()
        if not prompt:
            continue
        try:
            audio = client.music.compose(
                prompt=prompt,
                music_length_ms=int(it.length_ms),
            )
            # File naming: keep instruction order as BGM1, BGM2, ...
            label = sanitize_name(it.label or f"BGM{idx}")
            fname = f"{project_name}_BGM{idx:02d}.mp3"
            fpath = out_dir / fname
            with open(fpath, "wb") as f:
                if isinstance(audio, (bytes, bytearray)):
                    f.write(audio)
                else:
                    for chunk in audio:
                        if isinstance(chunk, (bytes, bytearray)):
                            f.write(chunk)
            dur = estimate_duration_seconds(fpath, it.output_format) or round(it.length_ms/1000.0, 3)
            saved.append({"index": idx, "label": it.label or f"BGM{idx}", "path": str(fpath), "duration": dur})
        except Exception as e:
            errors.append({"index": idx, "label": it.label, "error": str(e)})

    return {"ok": len(errors) == 0, "saved": saved, "errors": errors}


@app.post("/api/sfx/convert")
def convert_sfx(job: SfxJob):  # type: ignore
    if ElevenLabs is None:
        return {"ok": False, "error": "elevenlabs SDK not installed"}
    if not API_KEY:
        return {"ok": False, "error": "ELEVENLABS_API_KEY missing"}

    client = ElevenLabs(api_key=API_KEY)

    base = pathlib.Path(job.project_dir).expanduser().resolve()
    project_name = base.name
    out_dir = base / job.output_subdir
    ensure_dir(out_dir)

    saved = []
    errors = []

    for idx, it in enumerate(job.items, 1):
        prompt = (it.prompt or "").trim() if hasattr(str, 'trim') else (it.prompt or "").strip()
        if not prompt:
            continue
        try:
            # SDK expects 'text' (not 'prompt') for SFX
            kwargs: dict[str, Any] = {"text": prompt}
            if it.duration_sec and it.duration_sec > 0:
                kwargs["duration_seconds"] = float(it.duration_sec)
            if it.prompt_influence is not None:
                kwargs["prompt_influence"] = float(it.prompt_influence)
            if it.looping is not None:
                kwargs["looping"] = bool(it.looping)
            # SDK path guessed based on API naming
            try:
                audio = client.sound_effects.convert(**kwargs)  # type: ignore[attr-defined]
            except Exception:
                # fallback name
                audio = client.text_to_sound_effects.convert(**kwargs)  # type: ignore[attr-defined]

            # File naming: keep list order as SE1, SE2, ...
            label = sanitize_name(it.label or f"SE{idx}")
            fname = f"{project_name}_SE{idx:02d}.mp3"
            fpath = out_dir / fname
            with open(fpath, "wb") as f:
                if isinstance(audio, (bytes, bytearray)):
                    f.write(audio)
                else:
                    for chunk in audio:
                        if isinstance(chunk, (bytes, bytearray)):
                            f.write(chunk)
            dur = estimate_duration_seconds(fpath, it.output_format)
            saved.append({"index": idx, "label": it.label or f"SE{idx}", "path": str(fpath), "duration": dur})
        except Exception as e:
            errors.append({"index": idx, "label": it.label, "error": str(e)})

    return {"ok": len(errors) == 0, "saved": saved, "errors": errors}


if __name__ == "__main__":  # pragma: no cover
    import uvicorn
    host = os.getenv("EL_HOST", "127.0.0.1")
    port = int(os.getenv("EL_PORT", "8787"))
    uvicorn.run("backend.eleven_server:app", host=host, port=port, reload=True)
