"""Google Cloud + Gemini hybrid TTS generator for narration workflows."""
from __future__ import annotations

import base64
import logging
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

from google.cloud import texttospeech

from orion_ssml_builder import build_ssml


logger = logging.getLogger(__name__)


class OrionTTSGenerator:
    """Wrapper around Google Cloud Text-to-Speech for Orion content."""

    def __init__(self, config: Dict[str, Any]):
        self._ensure_env_var("GEMINI_API_KEY")
        self.config = config
        self.pronunciation_hints: Dict[str, str] = {}
        hints = config.get("pronunciation_hints")
        if isinstance(hints, dict):
            self.pronunciation_hints = hints
        self.client = texttospeech.TextToSpeechClient()
        raw_root = config.get("raw") if isinstance(config.get("raw"), dict) else {}
        google_raw = raw_root.get("google_tts", {}) if isinstance(raw_root, dict) else {}
        if not google_raw and isinstance(config.get("google_tts"), dict):
            google_raw = config.get("google_tts", {})
        self._gemini_settings: Dict[str, Any] = {}
        if isinstance(google_raw, dict):
            settings = google_raw.get("gemini_dialogue")
            if isinstance(settings, dict):
                self._gemini_settings = settings
        self._gemini_client = None

    def generate(
        self,
        text: str,
        character: str,
        output_path: Path,
        segment_no: int | None = None,
        *,
        scene: str | None = None,
        prev_scene: str | None = None,
    ) -> bool:
        """Generate an MP3 file for the supplied segment."""

        try:
            adjusted_text = text
            if self._should_rewrite_dialogue(character):
                adjusted_text = self._rewrite_with_gemini(text, character, scene)

            if self._should_use_gemini_tts(character):
                if self._synthesize_with_gemini_tts(adjusted_text, character, scene, output_path, segment_no):
                    return True

            ssml = build_ssml(
                adjusted_text,
                character,
                self.config,
                scene=scene,
                prev_scene=prev_scene,
            )
            if segment_no is not None:
                logger.debug(f"[{segment_no:03d}] SSML => %s", ssml)

            voice_params = self._get_voice_config(character)
            audio_config = self._get_audio_config(character)

            synthesis_input = texttospeech.SynthesisInput(ssml=ssml)
            response = self.client.synthesize_speech(
                input=synthesis_input,
                voice=voice_params,
                audio_config=audio_config,
            )

            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(response.audio_content)

            display_no = f"[{segment_no:03d}] " if segment_no is not None else ""
            logger.info("%s%s -> %s", display_no, character, output_path.name)
            return True
        except Exception as exc:  # pragma: no cover - defensive
            display_no = f"[{segment_no:03d}] " if segment_no is not None else ""
            logger.error("%sFailed to synthesize %s: %s", display_no, character, exc)
            return False

    def _get_voice_config(self, character: str) -> texttospeech.VoiceSelectionParams:
        voices = self.config.get("google_tts", {}).get("voices", {})
        voice_info = voices.get(character, {}) if isinstance(voices, dict) else {}

        voice_name = voice_info.get("name") or os.getenv("GOOGLE_TTS_VOICE") or "ja-JP-Neural2-C"

        language_code = os.getenv("GOOGLE_TTS_LANGUAGE", "ja-JP")
        return texttospeech.VoiceSelectionParams(language_code=language_code, name=voice_name)

    def _get_audio_config(self, character: str) -> texttospeech.AudioConfig:
        voices = self.config.get("google_tts", {}).get("voices", {})
        voice_info = voices.get(character, {}) if isinstance(voices, dict) else {}

        speaking_rate = os.getenv("GOOGLE_TTS_SPEAKING_RATE")
        if speaking_rate is not None:
            rate_value = float(speaking_rate)
        else:
            rate_value = float(voice_info.get("speaking_rate", 1.0))

        pitch_setting = os.getenv("GOOGLE_TTS_PITCH")
        if pitch_setting is not None:
            pitch_value = float(pitch_setting)
        else:
            pitch_value = float(voice_info.get("pitch", 0.0))

        return texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=rate_value,
            pitch=pitch_value,
        )

    # ------------------------------------------------------------------
    # Gemini-assisted dialogue rewriting

    def _should_use_gemini(self, character: str) -> bool:
        if not self._gemini_settings or not isinstance(self._gemini_settings, dict):
            return False
        if not self._gemini_settings.get("enabled"):
            return False
        if character in {"", None, "ナレーター"}:
            return False
        self._ensure_env_var("GEMINI_API_KEY")
        if not os.getenv("GEMINI_API_KEY"):
            logger.debug("Gemini disabled because GEMINI_API_KEY is missing.")
            return False
        return True

    def _should_rewrite_dialogue(self, character: str) -> bool:
        if not self._should_use_gemini(character):
            return False
        if not self._gemini_settings.get("rewrite_enabled", True):
            return False
        model = self._gemini_settings.get("rewrite_model") or os.getenv("GEMINI_MODEL")
        return bool(model)

    def _should_use_gemini_tts(self, character: str) -> bool:
        if not self._should_use_gemini(character):
            return False
        model = self._gemini_settings.get("tts_model") or os.getenv("GEMINI_TTS_MODEL")
        return bool(model)

    def _ensure_gemini_client(self) -> None:
        if self._gemini_client is not None:
            return
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set; cannot adjust dialogue with Gemini.")
        try:
            from google import genai  # type: ignore
        except ImportError as exc:  # pragma: no cover - defensive
            raise RuntimeError(
                "google-generativeai package is required for Gemini adjustments."
            ) from exc

        self._gemini_client = genai.Client(api_key=api_key)

    def _rewrite_with_gemini(self, text: str, character: str, scene: Optional[str]) -> str:
        if not self._should_rewrite_dialogue(character):
            return text
        try:
            self._ensure_gemini_client()
        except Exception as exc:
            logger.warning("Gemini unavailable (%s); using original dialogue for %s.", exc, character)
            return text

        model = (
            self._gemini_settings.get("rewrite_model")
            or os.getenv("GEMINI_MODEL")
            or "gemini-2.5-pro"
        )
        base_instruction = self._gemini_settings.get("base_instruction", "").strip()
        style_prompts = self._gemini_settings.get("style_prompts", {})
        style_prompt = ""
        if isinstance(style_prompts, dict):
            style_prompt = style_prompts.get(character) or style_prompts.get("default", "")

        parts = [p.strip() for p in [base_instruction, style_prompt] if p and p.strip()]
        prompt_header = "\n".join(parts) if parts else "Rewrite the dialogue naturally for spoken Japanese."
        scene_note = f"Scene context: {scene}" if scene else ""
        prompt = "\n".join([prompt_header, scene_note, "---", text.strip(), "---"]).strip()

        try:
            response = self._gemini_client.models.generate_content(
                model=model,
                contents=prompt,
            )
            rewritten = self._extract_response_text(response)
            if rewritten:
                logger.debug("Gemini rewrote dialogue for %s: %s", character, rewritten)
                return rewritten
            logger.warning("Gemini returned empty rewrite for %s; falling back to original text.", character)
        except Exception as exc:
            logger.warning("Gemini rewrite failed for %s: %s", character, exc)
        return text

    @staticmethod
    def _extract_response_text(response: object) -> str:
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

    # ------------------------------------------------------------------
    # Gemini TTS synthesis

    def _synthesize_with_gemini_tts(
        self,
        text: str,
        character: str,
        scene: Optional[str],
        output_path: Path,
        segment_no: Optional[int],
    ) -> bool:
        try:
            self._ensure_gemini_client()
        except Exception as exc:
            logger.warning("Gemini TTS unavailable (%s); falling back to Google for %s.", exc, character)
            return False

        tts_model = (
            self._gemini_settings.get("tts_model")
            or os.getenv("GEMINI_TTS_MODEL")
            or "gemini-2.5-flash-preview-tts"
        )
        voice_name = self._pick_gemini_voice(character)

        annotated_text = self._annotate_text_for_gemini(text)
        prompt = self._build_gemini_prompt(character, scene, annotated_text)

        try:
            response = self._gemini_client.models.generate_content(
                model=tts_model,
                contents=prompt,
                config={
                    "response_modalities": ["AUDIO"],
                    "speech_config": {
                        "voice_config": {
                            "prebuilt_voice_config": {"voice_name": voice_name}
                        }
                    },
                },
            )
        except Exception as exc:
            logger.warning("Gemini TTS request failed for %s: %s", character, exc)
            return False

        parts = (
            response.candidates[0].content.parts
            if response.candidates and response.candidates[0].content
            else []
        )
        if not parts:
            logger.warning("Gemini TTS returned no audio for %s", character)
            return False

        inline_data = getattr(parts[0], "inline_data", None)
        raw_data = getattr(inline_data, "data", b"") if inline_data else b""
        pcm_bytes = base64.b64decode(raw_data) if isinstance(raw_data, str) else raw_data
        if not pcm_bytes:
            logger.warning("Gemini TTS returned empty audio payload for %s", character)
            return False

        try:
            self._save_pcm_as_mp3(pcm_bytes, output_path)
        except Exception as exc:
            logger.warning("Failed to convert Gemini PCM to MP3 for %s: %s", character, exc)
            return False

        display_no = f"[{segment_no:03d}] " if segment_no is not None else ""
        logger.info("%s%s (Gemini TTS) -> %s", display_no, character, output_path.name)
        return True

    def _annotate_text_for_gemini(self, text: str) -> str:
        annotated = text
        for term, reading in self.pronunciation_hints.items():
            if term in annotated:
                annotated = annotated.replace(term, f"{term}（{reading}）")
        return annotated

    def _pick_gemini_voice(self, character: str) -> str:
        overrides = self._gemini_settings.get("voice_overrides", {})
        if isinstance(overrides, dict):
            voice = overrides.get(character) or overrides.get("default")
            if voice:
                return voice
        return self._gemini_settings.get("voice_name", "kore")

    def _build_gemini_prompt(self, character: str, scene: Optional[str], text: str) -> str:
        base_instruction = self._gemini_settings.get("base_instruction", "").strip()
        style_prompts = self._gemini_settings.get("style_prompts", {})
        style_prompt = ""
        if isinstance(style_prompts, dict):
            style_prompt = style_prompts.get(character) or style_prompts.get("default", "")
        lines = [item for item in [base_instruction, style_prompt] if item]
        if scene:
            lines.append(f"Scene context: {scene}")
        lines.append(text.strip())
        return "\n".join(lines)

    def _save_pcm_as_mp3(self, pcm_data: bytes, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
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
            str(output_path),
        ]
        proc = subprocess.run(cmd, input=pcm_data, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.decode("utf-8", errors="ignore"))

    @staticmethod
    def _ensure_env_var(name: str) -> None:
        if os.getenv(name):
            return
        env_path = REPO_ROOT / ".env" if 'REPO_ROOT' in globals() else Path(__file__).resolve().parents[2] / ".env"
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                if not line or line.strip().startswith("#"):
                    continue
                if line.startswith(f"{name}="):
                    _, value = line.split("=", 1)
                    os.environ[name] = value.strip()
                    return
REPO_ROOT = Path(__file__).resolve().parents[1]
