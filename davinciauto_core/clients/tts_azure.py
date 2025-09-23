"""Azure Speech Service based TTS helpers."""

from __future__ import annotations

import os
import pathlib
from typing import Callable, List, Optional
from xml.sax.saxutils import escape

from ..utils.voice_parser import VoiceInstructionParser

try:  # pragma: no cover - optional dependency guard
    import azure.cognitiveservices.speech as speechsdk  # type: ignore
except Exception:  # pragma: no cover
    speechsdk = None  # type: ignore


class AzureTTSError(RuntimeError):
    """Base exception for Azure Speech TTS."""


def _require_sdk() -> "speechsdk":
    if speechsdk is None:  # pragma: no cover - environment guard
        raise AzureTTSError(
            "azure-cognitiveservices-speech is required for Azure TTS. Install it via `pip install azure-cognitiveservices-speech`."
        )
    return speechsdk


def _audio_segment():
    try:
        from pydub import AudioSegment  # type: ignore
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise AzureTTSError(
            "pydub is required for Azure TTS synthesis. Install it via `pip install pydub`."
        ) from exc

    ffmpeg_path = os.getenv("DAVA_FFMPEG_PATH")
    if not ffmpeg_path:
        raise AzureTTSError("Set DAVA_FFMPEG_PATH to the bundled ffmpeg binary before running TTS.")

    ffmpeg_file = pathlib.Path(ffmpeg_path)
    if not ffmpeg_file.exists():
        raise AzureTTSError(f"DAVA_FFMPEG_PATH does not exist: {ffmpeg_file}")

    ffprobe_path = os.getenv("DAVA_FFPROBE_PATH") or str(ffmpeg_file.with_name("ffprobe"))
    if not pathlib.Path(ffprobe_path).exists():
        raise AzureTTSError(
            "Set DAVA_FFPROBE_PATH to the bundled ffprobe binary (or place it alongside ffmpeg)."
        )

    AudioSegment.converter = str(ffmpeg_file)
    AudioSegment.ffmpeg = str(ffmpeg_file)
    AudioSegment.ffprobe = str(ffprobe_path)
    return AudioSegment


def _build_ssml(text: str, voice_name: str, style: Optional[str], rate: float) -> str:
    body = escape(text)
    if abs(rate - 1.0) > 1e-6:
        pct = int(round((rate - 1.0) * 100))
        sign = "+" if pct >= 0 else ""
        body = f"<prosody rate=\"{sign}{pct}%\">{body}</prosody>"
    if style:
        body = f"<mstts:express-as style=\"{escape(style)}\">{body}</mstts:express-as>"
    speak_attrs = (
        'version="1.0" '
        'xmlns="http://www.w3.org/2001/10/synthesis" '
        'xmlns:mstts="https://www.w3.org/2001/mstts" '
        'xml:lang="ja-JP"'
    )
    return f"<speak {speak_attrs}><voice name=\"{escape(voice_name)}\">{body}</voice></speak>"


def _select_voice(role: str, gender: Optional[str]) -> str:
    default_voice = os.getenv("AZURE_SPEECH_VOICE", "ja-JP-NanamiNeural")
    narration_voice = os.getenv("AZURE_SPEECH_VOICE_NARRATION", default_voice)
    dialogue_voice = os.getenv("AZURE_SPEECH_VOICE_DIALOGUE", default_voice)
    male_voice = os.getenv("AZURE_SPEECH_VOICE_MALE", dialogue_voice)
    female_voice = os.getenv("AZURE_SPEECH_VOICE_FEMALE", dialogue_voice)

    if gender == "male":
        return male_voice
    if gender == "female":
        return female_voice
    return narration_voice if role == "NA" else dialogue_voice


def _speak_to_file(speechsdk_module, speech_config, ssml: str, out_path: pathlib.Path) -> None:
    audio_config = speechsdk_module.audio.AudioOutputConfig(filename=str(out_path))
    synthesizer = speechsdk_module.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
    try:
        result = synthesizer.speak_ssml_async(ssml).get()
    finally:
        if hasattr(synthesizer, "close"):
            try:
                synthesizer.close()
            except Exception:  # pragma: no cover - best effort
                pass

    if result.reason == speechsdk_module.ResultReason.SynthesizingAudioCompleted:
        return

    if result.reason == getattr(speechsdk_module.ResultReason, "Canceled", None):
        cancellation_details = getattr(speechsdk_module, "CancellationDetails", None)
        error_details = None
        if cancellation_details and hasattr(cancellation_details, "from_result"):
            try:
                detail_obj = cancellation_details.from_result(result)
                error_details = getattr(detail_obj, "error_details", None)
            except Exception:  # pragma: no cover - defensive
                error_details = None
        raise AzureTTSError(error_details or "Azure speech synthesis canceled.")

    raise AzureTTSError("Azure speech synthesis failed.")


def tts_azure_per_line(
    items: List[dict],
    out_dir: str = "output/audio",
    rate: float = 1.0,
    *,
    enable_voice_parsing: bool = True,
    concurrency: int = 1,
    on_progress: Optional[Callable[[int, int], None]] = None,
) -> tuple[str, List[str]]:
    speechsdk_module = _require_sdk()

    key = os.getenv("AZURE_SPEECH_KEY")
    region = os.getenv("AZURE_SPEECH_REGION")
    if not key or not region:
        raise AzureTTSError("AZURE_SPEECH_KEY and AZURE_SPEECH_REGION must be set.")

    out_path = pathlib.Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    speech_config = speechsdk_module.SpeechConfig(subscription=key, region=region)
    if hasattr(speech_config, "set_speech_synthesis_output_format"):
        speech_config.set_speech_synthesis_output_format(
            speechsdk_module.SpeechSynthesisOutputFormat.Audio24Khz160KBitRateMonoMp3
        )

    parser = VoiceInstructionParser() if enable_voice_parsing else None
    piece_files: List[str] = []

    total_items = len(items)
    for index, item in enumerate(items, start=1):
        role = (item.get("role") or "DL").upper()
        raw_text = (item.get("text") or "").strip()
        if not raw_text:
            continue

        gender: Optional[str] = None
        clean_text = raw_text
        if parser:
            instruction = parser.parse_voice_instruction(raw_text)
            clean_text = instruction.clean_text or raw_text
            gender = instruction.gender
        else:
            clean_text = raw_text

        voice_name = _select_voice(role, gender)
        style = "narration-professional" if role == "NA" else "chat"
        speech_config.speech_synthesis_voice_name = voice_name

        clip_path = out_path / f"line_{index:03d}.mp3"
        ssml = _build_ssml(clean_text, voice_name, style, rate)
        _speak_to_file(speechsdk_module, speech_config, ssml, clip_path)
        piece_files.append(str(clip_path))

        if on_progress:
            on_progress(index, total_items)

    audio_segment = _audio_segment()
    if piece_files:
        merged = audio_segment.empty()
        for filename in piece_files:
            merged += audio_segment.from_file(filename)
    else:
        merged = audio_segment.silent(duration=1000)

    merged_path = out_path / "narration.mp3"
    merged.export(str(merged_path), format="mp3")

    return str(merged_path), piece_files


__all__ = ["AzureTTSError", "tts_azure_per_line"]
