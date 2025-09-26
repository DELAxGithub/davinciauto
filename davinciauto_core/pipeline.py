from __future__ import annotations

import json
import os
import platform
import re
import signal
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from dotenv import load_dotenv

from .bgm import (
    BGMGenerationError,
    StableAudioAPIError,
    StableAudioAPIKeyError,
    StableAudioDependencyError,
    generate_bgm_and_se,
)
from .clients.tts_azure import AzureTTSError, tts_azure_per_line
from .clients.tts_elevenlabs import RateLimitError, TTSError, tts_elevenlabs_per_line
from .utils.cost_tracker import CostTracker
from .utils.srt import Cue, build_srt, distribute_by_audio_length
from .utils.wrap import split_text_to_multiple_subtitles

# Optional debug utilities are imported lazily to avoid side effects


@dataclass
class PipelineConfig:
    """Configuration payload used for pipeline execution."""

    script_path: Optional[Path] = None
    script_text: Optional[str] = None
    output_root: Path = Path("output")
    fake_tts: bool = False
    rate: float = 1.0
    voice_preset: Optional[str] = None
    enable_voice_parsing: bool = True
    load_env: bool = True
    debug_llm: bool = False
    verbose_debug: bool = False
    cost_log_dir: Optional[Path] = None
    progress_log_path: Optional[Path] = None
    concurrency: int = 1
    project_id: Optional[str] = None
    provider: str = "azure"
    target: str = "resolve"
    frame_rate: float = 23.976
    sample_rate: int = 48000
    api_key: Optional[str] = None
    subtitle_lang: str = "ja-JP"
    subtitle_format: str = "srt"
    audio_format: str = "mp3"
    subtitle_text_path: Optional[Path] = None
    subtitle_srt_path: Optional[Path] = None
    bgm_plan_path: Optional[Path] = None
    scene_plan_path: Optional[Path] = None
    timeline_csv_path: Optional[Path] = None
    enable_bgm_workflow: bool = True

    def resolve_script_text(self) -> str:
        """Return the script contents, reading from disk if necessary."""

        if self.script_text:
            return self.script_text
        if not self.script_path:
            raise ValueError("script_path or script_text must be provided")
        return Path(self.script_path).read_text(encoding="utf-8")


@dataclass
class PipelinePaths:
    """Derived file system locations for pipeline outputs."""

    output_root: Path
    audio_dir: Path = field(init=False)
    subtitles_dir: Path = field(init=False)
    storyboard_dir: Path = field(init=False)
    logs_dir: Path = field(init=False)
    audio_path: Path = field(init=False)
    subtitles_path: Path = field(init=False)
    plain_subtitles_path: Path = field(init=False)
    storyboard_pack_path: Path = field(init=False)

    def __post_init__(self) -> None:
        root = self.output_root
        self.audio_dir = root / "audio"
        self.subtitles_dir = root / "subtitles"
        self.storyboard_dir = root / "storyboard"
        self.logs_dir = root / "logs"
        self.audio_path = self.audio_dir / "narration.mp3"
        self.subtitles_path = self.subtitles_dir / "script.srt"
        self.plain_subtitles_path = root / "subtitles_plain.txt"
        self.storyboard_pack_path = self.storyboard_dir / "pack.json"

    def ensure_directories(self) -> None:
        for directory in (self.audio_dir, self.subtitles_dir, self.storyboard_dir, self.logs_dir):
            directory.mkdir(parents=True, exist_ok=True)


class ManifestStore:
    """Helper for reading/writing manifest with backup support."""

    def __init__(self, path: Path):
        self.path = path
        self.backup = path.with_suffix(path.suffix + ".backup")

    def write(self, content: str) -> None:
        self.backup.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            try:
                self.backup.write_text(self.path.read_text(encoding="utf-8"), encoding="utf-8")
            except Exception:
                pass
        _atomic_write_text(self.path, content)

    def read(self) -> Dict[str, object]:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            if self.backup.exists():
                return json.loads(self.backup.read_text(encoding="utf-8"))
            raise


class ProgressLogger:
    """Append-only JSONL logger for pipeline progress."""

    def __init__(self, path: Optional[Path]):
        self._path = Path(path) if path else None
        if self._path:
            self._path.parent.mkdir(parents=True, exist_ok=True)
        self._counter = 0
        self._last_emit = time.time()

    def emit(self, event_type: str, **payload: object) -> None:
        if not self._path:
            return
        self._counter += 1
        now = time.time()
        level = str(payload.pop("level", "info"))
        message = payload.get("message") or payload.get("msg")
        record = {
            "schema": "davinciauto.v1",
            "seq": self._counter,
            "type": event_type,
            "code": payload.get("code", event_type),
            "level": level,
            "ts": now,
            **payload,
        }
        if message:
            record.setdefault("message", message)
        line = json.dumps(record, ensure_ascii=False)
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
        self._last_emit = now

    def maybe_heartbeat(self, threshold: float = 5.0) -> None:
        if not self._path:
            return
        now = time.time()
        if now - self._last_emit >= threshold:
            self.emit("heartbeat")


@dataclass
class PipelineResult:
    """Structured result returned by :func:`run_pipeline`."""

    audio_path: Path
    audio_segments: List[Path]
    subtitles_path: Path
    plain_subtitles_path: Path
    storyboard_pack_path: Path
    subtitle_cards: List[Dict[str, Sequence[str]]]
    original_items: List[Dict[str, str]]
    cost_summary: Optional[str] = None
    usage_log_path: Optional[Path] = None
    bgm_tracks: List[Path] = field(default_factory=list)
    se_tracks: List[Path] = field(default_factory=list)
    bgm_errors: List[str] = field(default_factory=list)
    extra: Dict[str, object] = field(default_factory=dict)


_SCRIPT_PREFIX = re.compile(r"^(NA|セリフ)\s*[:：,，、]\s*(.+)$")


def _resource_path(relative: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return (base / relative).resolve()


def parse_script(script_text: str) -> List[Dict[str, str]]:
    """Extract dialogue/narration rows from the raw script.

    Historically、台本は ``NA: ...`` / ``セリフ: ...`` の形式だったが、
    実際には「NA,」「NA：」などの記法も混在するケースがあるため、
    コロン・読点の揺れを吸収する。
    """

    items: List[Dict[str, str]] = []
    for line in script_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        match = _SCRIPT_PREFIX.match(stripped)
        if not match:
            continue
        role_key, body = match.groups()
        role = "NA" if role_key == "NA" else "DL"
        items.append({"role": role, "text": body.strip()})
    return items


def _configure_environment() -> None:
    """Ensure Python bytecode/cache paths stay within the sandbox."""

    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

    if not os.environ.get("PYTHONPYCACHEPREFIX"):
        cache_root = (
            Path(os.getenv("XDG_CACHE_HOME", str(Path.home() / ".cache")))
            / "davinciauto"
            / "pyc"
        )
        cache_root.mkdir(parents=True, exist_ok=True)
        os.environ["PYTHONPYCACHEPREFIX"] = str(cache_root)

    os.environ.setdefault("LC_ALL", "en_US_POSIX")


def _validate_output_root(output_root: Path) -> None:
    """Disallow writing into application bundles or other protected locations."""

    resolved = output_root.expanduser()
    try:
        real = resolved.resolve(strict=False)
    except FileNotFoundError:
        real = resolved

    def contains_app(path: Path) -> bool:
        for parent in [path] + list(path.parents):
            if parent.suffix.lower() == ".app":
                return True
        return False

    if contains_app(resolved) or contains_app(real):
        raise PermissionError(
            "Output directory cannot reside inside a .app bundle. Choose a user-writable location."
        )


def _atomic_write_text(path: Path, content: str, *, encoding: str = "utf-8") -> None:
    """Write text using an atomic rename to avoid partial files."""

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.tmp")
    tmp_path.write_text(content, encoding=encoding)
    tmp_path.replace(path)


def perform_self_check() -> Dict[str, object]:
    """Run minimal environment checks and return diagnostic information."""

    info: Dict[str, object] = {"ok": True}
    try:
        _configure_environment()
        import pydub  # type: ignore

        info.setdefault("deps", {})
        info["deps"]["pydub"] = getattr(pydub, "__version__", "unknown")
    except Exception as exc:  # pragma: no cover - environment guard
        info["ok"] = False
        info["error"] = str(exc)
        return info

    try:
        import elevenlabs  # type: ignore

        info.setdefault("deps", {})["elevenlabs"] = getattr(elevenlabs, "__version__", "unknown")
    except Exception as exc:  # pragma: no cover - optional dependency guard
        info.setdefault("issues", []).append("elevenlabs-missing")
        info.setdefault("warnings", []).append(str(exc))

    try:
        _get_audio_segment()
        info["ffmpeg"] = os.getenv("DAVA_FFMPEG_PATH", "")
        info["ffprobe"] = os.getenv("DAVA_FFPROBE_PATH", "")
    except Exception as exc:  # pragma: no cover - environment guard
        info["ok"] = False
        info["error"] = str(exc)
        return info

    try:
        probe = Path(tempfile.gettempdir()) / f"davinciauto_check_{os.getpid()}_{int(time.time())}.tmp"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
    except Exception as exc:  # pragma: no cover
        info["ok"] = False
        info["error"] = str(exc)

    return info


def _enable_debug_logging(config: PipelineConfig) -> None:
    if not config.debug_llm:
        return
    from .utils.debug_logger import enable_debug_logging

    enable_debug_logging(verbose=config.verbose_debug)


def _finalize_debug_logging(config: PipelineConfig) -> None:
    if not config.debug_llm:
        return
    from .utils.debug_logger import get_debug_logger

    logger = get_debug_logger()
    if logger.enabled:
        logger.print_session_summary()


def _get_audio_segment():
    try:
        from pydub import AudioSegment  # type: ignore
    except ModuleNotFoundError as exc:  # pragma: no cover - environment guard
        raise RuntimeError(
            "pydub is required to run the DaVinci Auto pipeline. "
            "Install it via `pip install pydub` or include it in the bundled runtime."
        ) from exc

    ffmpeg_path = os.getenv("DAVA_FFMPEG_PATH")
    if not ffmpeg_path:
        candidate = _resource_path("Resources/bin/ffmpeg")
        if candidate.exists():
            ffmpeg_path = str(candidate)
            os.environ["DAVA_FFMPEG_PATH"] = ffmpeg_path
        else:
            raise RuntimeError(
                "Set DAVA_FFMPEG_PATH to the bundled ffmpeg binary so pydub can render audio."
            )

    ffmpeg_file = Path(ffmpeg_path)
    if not ffmpeg_file.exists():
        raise RuntimeError(f"DAVA_FFMPEG_PATH does not exist: {ffmpeg_file}")
    if not os.access(ffmpeg_file, os.X_OK):
        raise RuntimeError(f"DAVA_FFMPEG_PATH is not executable: {ffmpeg_file}")

    ffprobe_path = os.getenv("DAVA_FFPROBE_PATH") or str(ffmpeg_file.with_name("ffprobe"))
    if not Path(ffprobe_path).exists():
        candidate = _resource_path("Resources/bin/ffprobe")
        if candidate.exists():
            ffprobe_path = str(candidate)
            os.environ["DAVA_FFPROBE_PATH"] = ffprobe_path
    if not Path(ffprobe_path).exists():
        raise RuntimeError(
            "Set DAVA_FFPROBE_PATH to the bundled ffprobe binary (or place it alongside ffmpeg)."
        )
    if not os.access(ffprobe_path, os.X_OK):
        raise RuntimeError(f"DAVA_FFPROBE_PATH is not executable: {ffprobe_path}")

    AudioSegment.converter = str(ffmpeg_file)
    AudioSegment.ffmpeg = str(ffmpeg_file)
    AudioSegment.ffprobe = str(ffprobe_path)
    return AudioSegment


def _generate_silent_audio(audio_path: Path, duration_seconds: float) -> Path:
    audio_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        audio_segment = _get_audio_segment()
        silence = audio_segment.silent(duration=int(duration_seconds * 1000), frame_rate=44100)
        format_hint = audio_path.suffix.lstrip('.') or 'mp3'
        silence.export(audio_path, format=format_hint)
        return audio_path
    except Exception:
        pass

    import wave
    import struct
    import math

    sample_rate = 48000
    wav_path = audio_path.with_suffix('.wav')
    frames = int(sample_rate * max(duration_seconds, 1.0))
    with wave.open(str(wav_path), 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for i in range(frames):
            value = int(0.05 * 32767 * math.sin(2 * math.pi * 220 * i / sample_rate))
            wav_file.writeframes(struct.pack('<h', value))
    return wav_path


def _probe_tool_version(executable: Optional[str]) -> Optional[str]:
    if not executable:
        return None
    try:
        proc = subprocess.run([executable, "-version"], check=False, capture_output=True, text=True)
        output = proc.stdout or proc.stderr
        return output.splitlines()[0].strip() if output else None
    except Exception:  # pragma: no cover - best effort
        return None


def _collect_tool_versions() -> Dict[str, Optional[str]]:
    versions: Dict[str, Optional[str]] = {
        "python": platform.python_version(),
    }
    try:
        import pydub  # type: ignore

        versions["pydub"] = getattr(pydub, "__version__", "unknown")
    except Exception:  # pragma: no cover
        versions["pydub"] = None

    versions["ffmpeg"] = _probe_tool_version(
        os.getenv("DAVA_FFMPEG_PATH") or os.getenv("DAVINCIAUTO_FFMPEG")
    )
    versions["ffprobe"] = _probe_tool_version(
        os.getenv("DAVA_FFPROBE_PATH") or os.getenv("DAVINCIAUTO_FFPROBE")
    )
    return versions


def run_pipeline(config: PipelineConfig) -> PipelineResult:
    """Execute the narration → subtitle pipeline using the provided configuration."""

    if config.load_env:
        load_dotenv()

    _configure_environment()
    prev_eleven_api_key = os.environ.get("ELEVENLABS_API_KEY")
    if config.api_key and config.provider.lower() == "elevenlabs":
        os.environ["ELEVENLABS_API_KEY"] = config.api_key

    script_text = config.resolve_script_text()
    if script_text.startswith("\ufeff"):
        script_text = script_text.lstrip("\ufeff")
    items = parse_script(script_text)
    if not items:
        raise ValueError("No lines starting with 'NA:' or 'セリフ:' were found in the script.")

    paths = PipelinePaths(config.output_root)
    _validate_output_root(paths.output_root)
    paths.ensure_directories()

    cost_log_dir = config.cost_log_dir or paths.logs_dir
    cost_tracker = CostTracker(log_dir=str(cost_log_dir))

    progress = ProgressLogger(config.progress_log_path)
    progress.emit(
        "start",
        level="info",
        stage="init",
        message=f"Pipeline start: output={paths.output_root}",
        output_root=str(paths.output_root),
        tool_versions=_collect_tool_versions(),
    )
    progress.emit(
        "parsed_script",
        level="info",
        message=f"Parsed script items={len(items)}",
        items=len(items),
    )

    stop_event = threading.Event()
    abort_flag = threading.Event()

    def _segment_progress(index: int, total: int) -> None:
        progress.emit(
            "segment_generated",
            level="progress",
            message=f"Generated segment {index}/{total}",
            index=index,
            total=total,
        )
        progress.maybe_heartbeat()

    def heartbeat_worker() -> None:
        while not stop_event.wait(1.0):
            progress.maybe_heartbeat()

    heartbeat_thread = threading.Thread(target=heartbeat_worker, daemon=True)
    heartbeat_thread.start()

    previous_sigint = signal.getsignal(signal.SIGINT)
    previous_sigterm = signal.getsignal(signal.SIGTERM)

    def signal_handler(sig: int, _frame) -> None:
        if not abort_flag.is_set():
            progress.emit(
                "aborted",
                level="error",
                message=f"Aborted due to signal {sig}",
                signal=sig,
            )
            abort_flag.set()
        stop_event.set()
        raise KeyboardInterrupt()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    _enable_debug_logging(config)

    try:
        cost_summary: Optional[str] = None
        bgm_tracks: List[Path] = []
        se_tracks: List[Path] = []
        bgm_errors: List[str] = []

        provider = (config.provider or "azure").lower()

        try:
            if config.fake_tts:
                estimated_seconds = max(2.5 * len(items), 3.0)
                paths.audio_path = _generate_silent_audio(paths.audio_path, estimated_seconds)
                piece_files: List[Path] = []
                progress.emit(
                    "audio_synth",
                    level="info",
                    mode="fake",
                    message=f"Generated silent audio (duration≈{estimated_seconds:.1f}s)",
                    estimated_seconds=estimated_seconds,
                )
            else:
                progress.emit(
                    "audio_synth",
                    level="info",
                    mode="tts",
                    message=f"Synthesizing audio segments={len(items)} via {provider}",
                    items=len(items),
                    concurrency=config.concurrency,
                    provider=provider,
                )
                if provider == "elevenlabs":
                    audio_path, raw_piece_files = tts_elevenlabs_per_line(
                        items,
                        out_dir=str(paths.audio_dir),
                        rate=config.rate,
                        cost_tracker=cost_tracker,
                        enable_voice_parsing=config.enable_voice_parsing,
                        voice_preset=config.voice_preset,
                        concurrency=config.concurrency,
                        on_rate_limit=lambda rl: progress.emit(
                            "rate_limit",
                            level="warn",
                            message=f"Rate limit hit: retry {rl.retry_after}s",
                            retry_after=rl.retry_after,
                            remaining=rl.remaining,
                            suggested_concurrency=rl.suggested_concurrency,
                        ),
                        on_progress=_segment_progress,
                    )
                elif provider == "azure":
                    audio_path, raw_piece_files = tts_azure_per_line(
                        items,
                        out_dir=str(paths.audio_dir),
                        rate=config.rate,
                        enable_voice_parsing=config.enable_voice_parsing,
                        concurrency=config.concurrency,
                        on_progress=_segment_progress,
                    )
                else:
                    raise RuntimeError(f"Unsupported TTS provider: {config.provider}")

                paths.audio_path = Path(audio_path)
                piece_files = [Path(p) for p in raw_piece_files]
        except RateLimitError as exc:
            progress.emit(
                "rate_limit",
                level="warn",
                message=f"Rate limit hit: retry {exc.retry_after}s",
                retry_after=exc.retry_after,
                remaining=exc.remaining,
                suggested_concurrency=exc.suggested_concurrency,
            )
            paths.audio_path = _generate_silent_audio(paths.audio_path, max(2.5 * len(items), 3.0))
            piece_files = []
            cost_summary = f"Rate limit hit: retry after {exc.retry_after}s."
            progress.emit(
                "audio_complete",
                level="warn",
                mode="rate_limit",
                message="Audio fallback due to rate limit",
                segments=0,
            )
        except (TTSError, AzureTTSError) as exc:
            paths.audio_path = _generate_silent_audio(paths.audio_path, max(2.5 * len(items), 3.0))
            piece_files = []
            cost_summary = f"TTS failed: {exc}. Fallback silent audio generated."
            progress.emit(
                "warning",
                level="warn",
                stage="audio",
                message=str(exc),
            )
            progress.emit(
                "audio_complete",
                level="warn",
                mode="fallback",
                message="Audio fallback due to TTS failure",
                segments=0,
            )
        except KeyboardInterrupt:
            if not abort_flag.is_set():
                progress.emit(
                    "aborted",
                    level="error",
                    message="Aborted by user",
                    reason="keyboard_interrupt",
                )
                abort_flag.set()
            raise
        else:
            if not config.fake_tts and provider == "elevenlabs":
                cost_summary = cost_tracker.get_cost_summary()
            progress.emit(
                "audio_complete",
                level="info",
                mode="fake" if config.fake_tts else "tts",
                message=f"Audio complete segments={len(piece_files)}",
                segments=len(piece_files),
                provider=provider,
            )

        if config.enable_bgm_workflow and config.bgm_plan_path:
            plan_path = Path(config.bgm_plan_path).expanduser()
            if plan_path.exists():
                progress.emit(
                    "bgm_plan",
                    level="info",
                    message="Loaded BGM/SE plan",
                    plan=str(plan_path),
                )
                try:
                    bgm_tracks_raw, se_tracks_raw, bgm_errors = generate_bgm_and_se(plan_path)
                    bgm_tracks = [Path(p) for p in bgm_tracks_raw]
                    se_tracks = [Path(p) for p in se_tracks_raw]
                    for track in bgm_tracks:
                        progress.emit(
                            "bgm_generated",
                            level="info",
                            message=f"BGM saved",
                            path=str(track),
                        )
                    progress.emit(
                        "bgm_complete",
                        level="info",
                        message="BGM generation finished",
                        tracks=len(bgm_tracks),
                    )
                    for track in se_tracks:
                        progress.emit(
                            "se_generated",
                            level="info",
                            message="SE saved",
                            path=str(track),
                        )
                    progress.emit(
                        "se_complete",
                        level="info",
                        message="SE generation finished",
                        tracks=len(se_tracks),
                    )
                    for err in bgm_errors:
                        progress.emit(
                            "bgm_warning",
                            level="warn",
                            stage="bgm",
                            message=err,
                        )
                except StableAudioDependencyError as exc:
                    bgm_errors = [str(exc)]
                    progress.emit(
                        "bgm_error",
                        level="error",
                        stage="bgm",
                        message=str(exc),
                    )
                except StableAudioAPIKeyError as exc:
                    bgm_errors = [str(exc)]
                    progress.emit(
                        "bgm_error",
                        level="error",
                        stage="bgm",
                        message=str(exc),
                    )
                except StableAudioAPIError as exc:
                    bgm_errors = [str(exc)]
                    progress.emit(
                        "bgm_error",
                        level="error",
                        stage="bgm",
                        message=str(exc),
                    )
                except BGMGenerationError as exc:
                    bgm_errors = [str(exc)]
                    progress.emit(
                        "bgm_error",
                        level="error",
                        stage="bgm",
                        message=str(exc),
                    )
            else:
                progress.emit(
                    "bgm_warning",
                    level="warn",
                    stage="bgm",
                    message=f"BGM/SE plan not found: {plan_path}",
                )
                bgm_errors = [f"Plan not found: {plan_path}"]

        subtitle_cards: List[Dict[str, Sequence[str]]] = []
        roles: List[str] = []
        for item in items:
            cards = split_text_to_multiple_subtitles(item["text"])
            for card in cards:
                subtitle_cards.append({"text_2line": card})
                roles.append(item["role"])

        audio_segment = _get_audio_segment()
        audio_duration = audio_segment.from_file(paths.audio_path).duration_seconds
        cue_windows = distribute_by_audio_length(len(subtitle_cards), audio_duration, 1.8)
        cues = [
            Cue(idx=i, start=window[0], end=window[1], lines=subtitle_cards[i - 1]["text_2line"], role=roles[i - 1])
            for i, window in enumerate(cue_windows, start=1)
        ]
        subtitles = build_srt(cues)
        _atomic_write_text(paths.subtitles_path, subtitles)

        plain_lines = ["".join(card["text_2line"]) for card in subtitle_cards]
        _atomic_write_text(paths.plain_subtitles_path, "\n".join(plain_lines))

        storyboard_payload = {
            "items": items,
            "audio_path": str(paths.audio_path),
            "pieces": [str(p) for p in piece_files],
            "subtitles": subtitle_cards,
            "subtitle_count": len(subtitle_cards),
            "original_item_count": len(items),
        }
        storyboard_payload["metadata"] = {
            "project_id": config.project_id,
            "provider": config.provider,
            "target": config.target,
            "frame_rate": config.frame_rate,
            "sample_rate": config.sample_rate,
        }
        storyboard_payload["tool_versions"] = _collect_tool_versions()
        _atomic_write_text(
            paths.storyboard_pack_path,
            json.dumps(storyboard_payload, ensure_ascii=False, indent=2),
        )

        progress.emit(
            "subtitles_built",
            level="info",
            message=f"Generated subtitles cues={len(cues)}",
            cards=len(subtitle_cards),
            audio_duration=audio_duration,
            cues=len(cues),
        )

        usage_log = None
        if not config.fake_tts and piece_files:
            usage_log = Path(cost_tracker.save_usage_log())

        result = PipelineResult(
            audio_path=paths.audio_path,
            audio_segments=[Path(p) for p in piece_files],
            subtitles_path=paths.subtitles_path,
            plain_subtitles_path=paths.plain_subtitles_path,
            storyboard_pack_path=paths.storyboard_pack_path,
            subtitle_cards=subtitle_cards,
            original_items=items,
            cost_summary=cost_summary,
            usage_log_path=usage_log,
            bgm_tracks=bgm_tracks,
            se_tracks=se_tracks,
            bgm_errors=bgm_errors,
            extra={
                "output_root": str(paths.output_root),
                "audio_duration": audio_duration,
                "tool_versions": storyboard_payload["tool_versions"],
                "bgm_tracks": [str(path) for path in bgm_tracks],
                "se_tracks": [str(path) for path in se_tracks],
                "bgm_errors": bgm_errors,
            },
        )

        _finalize_debug_logging(config)
        if not abort_flag.is_set():
            progress.emit(
                "done",
                level="info",
                message="Pipeline finished",
                audio=str(paths.audio_path),
                srt=str(paths.subtitles_path),
                subtitles=len(subtitle_cards),
            )
        return result
    finally:
        stop_event.set()
        heartbeat_thread.join(timeout=1.0)
        signal.signal(signal.SIGINT, previous_sigint)
        signal.signal(signal.SIGTERM, previous_sigterm)
        if config.provider.lower() == "elevenlabs":
            if prev_eleven_api_key is None:
                os.environ.pop("ELEVENLABS_API_KEY", None)
            else:
                os.environ["ELEVENLABS_API_KEY"] = prev_eleven_api_key


__all__ = [
    "PipelineConfig",
    "PipelinePaths",
    "PipelineResult",
    "parse_script",
    "perform_self_check",
    "run_pipeline",
]
