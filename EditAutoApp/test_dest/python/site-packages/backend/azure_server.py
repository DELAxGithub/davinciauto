#!/usr/bin/env python3
"""Local Azure Speech synthesis worker.

Run:
  export AZURE_SPEECH_KEY=...
  export AZURE_SPEECH_REGION=...
  uvicorn backend.azure_server:app --host 127.0.0.1 --port 8788 --reload

POST /api/azure/synthesize
  {
    "project_dir": "/abs/path/to/project",
    "items": [
      {
        "line": 1,
        "text": "...",
        "voice": "ja-JP-NanamiNeural",
        "style": "narration-professional",
        "speaking_rate": 1.0
      }
    ],
    "output_subdir": "サウンド類/Narration"
  }

Saves MP3 files under:
  {project_dir}/{output_subdir}/{ProjectName}_{line:04d}_{Voice}.mp3
"""
from __future__ import annotations

import asyncio
import os
import pathlib
import re
from typing import Any, List, Optional
from xml.sax.saxutils import escape

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None  # type: ignore

if load_dotenv:
    load_dotenv()

try:
    import azure.cognitiveservices.speech as speechsdk  # type: ignore
except Exception:  # pragma: no cover
    speechsdk = None  # type: ignore


AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY", "")
AZURE_SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION", "")
DEFAULT_AZURE_VOICE = os.getenv("AZURE_SPEECH_VOICE", "ja-JP-NanamiNeural")


class Item(BaseModel):
    line: int
    text: str
    voice: Optional[str] = None
    style: Optional[str] = None
    role: Optional[str] = None
    speaking_rate: Optional[float] = None  # multiplier (1.0 = default)


class Job(BaseModel):
    project_dir: str
    items: List[Item]
    output_subdir: str = "サウンド類/Narration"


app = FastAPI(title="Azure Speech Worker", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def ensure_dir(path: pathlib.Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def sanitize_name(name: str) -> str:
    return re.sub(r"[^\w\-\.]+", "_", name.strip())[:48] or "voice"


def parse_rate(rate: Optional[float]) -> Optional[str]:
    if rate is None:
        return None
    try:
        val = float(rate)
    except (TypeError, ValueError):
        return None
    if abs(val - 1.0) < 1e-6:
        return None
    pct = int((val - 1.0) * 100)
    sign = "+" if pct >= 0 else ""
    return f"{sign}{pct}%"


def build_ssml(text: str, voice: str, style: Optional[str], role: Optional[str], rate: Optional[float]) -> str:
    body = escape(text)
    rate_attr = parse_rate(rate)
    if rate_attr:
        body = f"<prosody rate=\"{rate_attr}\">{body}</prosody>"
    if style:
        role_attr = f" role=\"{escape(role or '')}\"" if role else ""
        body = f"<mstts:express-as style=\"{escape(style)}\"{role_attr}>{body}</mstts:express-as>"
    speak_attrs = (
        'version="1.0" '
        'xmlns="http://www.w3.org/2001/10/synthesis" '
        'xmlns:mstts="https://www.w3.org/2001/mstts" '
        'xml:lang="en-US"'
    )
    return f"<speak {speak_attrs}><voice name=\"{escape(voice)}\">{body}</voice></speak>"


async def synthesize_item(item: Item, out_path: pathlib.Path) -> None:
    if speechsdk is None:
        raise RuntimeError("Azure Speech SDK is not installed.")
    if not AZURE_SPEECH_KEY or not AZURE_SPEECH_REGION:
        raise RuntimeError("Azure Speech credentials are not configured.")

    voice = item.voice or DEFAULT_AZURE_VOICE
    speech_config = speechsdk.SpeechConfig(subscription=AZURE_SPEECH_KEY, region=AZURE_SPEECH_REGION)
    speech_config.speech_synthesis_voice_name = voice
    if hasattr(speech_config, "set_speech_synthesis_output_format"):
        speech_config.set_speech_synthesis_output_format(
            speechsdk.SpeechSynthesisOutputFormat.Audio24Khz160KBitRateMonoMp3
        )

    audio_config = speechsdk.audio.AudioOutputConfig(filename=str(out_path))
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)

    text = item.text or ""
    if not text.strip():
        return

    if item.style or item.role or item.speaking_rate not in (None, 1.0):
        ssml = build_ssml(text, voice, item.style, item.role, item.speaking_rate)
        task = synthesizer.speak_ssml_async(ssml)
    else:
        task = synthesizer.speak_text_async(text)

    result = await asyncio.to_thread(task.get)

    if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
        if result.reason == getattr(speechsdk.ResultReason, "Canceled", None):
            cancellation = getattr(speechsdk, "CancellationDetails", None)
            details: Any = None
            if cancellation and hasattr(cancellation, "from_result"):
                details = cancellation.from_result(result)
            message = getattr(details, "error_details", None) or "Azure speech synthesis canceled."
            raise RuntimeError(message)
        raise RuntimeError("Azure speech synthesis failed.")


def estimate_duration(file_path: pathlib.Path) -> Optional[float]:
    try:
        size_bytes = file_path.stat().st_size
        kbps = 160
        seconds = (size_bytes * 8.0) / (kbps * 1000.0)
        return round(seconds, 3)
    except Exception:
        return None


@app.post("/api/azure/synthesize")
async def synthesize(job: Job):  # type: ignore
    if speechsdk is None:
        return {"ok": False, "error": "Azure Speech SDK not installed"}
    if not AZURE_SPEECH_KEY or not AZURE_SPEECH_REGION:
        return {"ok": False, "error": "AZURE_SPEECH_KEY/REGION missing"}

    base = pathlib.Path(job.project_dir).expanduser().resolve()
    project_name = base.name
    out_dir = base / (job.output_subdir or "サウンド類/Narration")
    ensure_dir(out_dir)

    saved = []
    errors = []

    for item in job.items:
        text = (item.text or "").strip()
        if not text:
            continue
        voice_label = sanitize_name(item.voice or DEFAULT_AZURE_VOICE)
        fname = f"{project_name}_{item.line:04d}_{voice_label}.mp3"
        fpath = out_dir / fname
        try:
            await synthesize_item(item, fpath)
            dur = estimate_duration(fpath)
            saved.append({"line": item.line, "path": str(fpath), "duration": dur, "voice": item.voice or DEFAULT_AZURE_VOICE})
        except Exception as exc:
            if fpath.exists():
                try:
                    fpath.unlink()
                except Exception:
                    pass
            errors.append({"line": item.line, "error": str(exc)})

    return {"ok": not errors, "saved": saved, "errors": errors}


@app.get("/api/health")
async def health():  # type: ignore
    return {"ok": True}
