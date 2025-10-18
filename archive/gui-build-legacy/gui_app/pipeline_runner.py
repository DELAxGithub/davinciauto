from __future__ import annotations

import json
import os
import shutil
import signal
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

from PySide6.QtCore import QObject, QProcess, QThread, Signal

from .config import AppConfig
from .log_watcher import LogWatcher
from .util.paths import default_cli_executable, resource_path


class PipelineRunner(QObject):
    log_event = Signal(dict)
    stderr = Signal(str)
    finished = Signal(int)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._process: Optional[QProcess] = None
        self._watcher = LogWatcher()
        self._watcher.line.connect(self.log_event.emit)
        self._watcher.error.connect(self.stderr.emit)
        self._log_path: Optional[Path] = None

    def is_running(self) -> bool:
        return self._process is not None and self._process.state() != QProcess.NotRunning

    def start(self, config: AppConfig, azure_key: Optional[str], eleven_key: Optional[str]) -> None:
        if self.is_running():
            return
        self._log_path = Path(tempfile.mkstemp(prefix="davinciauto_progress_", suffix=".jsonl")[1])
        args, env = self._build_cli_args(config, azure_key, eleven_key)

        program = default_cli_executable()
        use_embedded = os.getenv("APP_EMBEDDED") == "1"

        self._process = QProcess(self)
        if use_embedded and program == Path(sys.executable):
            # Embedded: run python -m davinciauto_core.cli
            self._process.setProgram(sys.executable)
            self._process.setArguments(["-m", "davinciauto_core.cli", *args])
        elif program == Path(sys.executable):
            # Development fallback (no bundled CLI)
            self._process.setProgram(sys.executable)
            self._process.setArguments(["-m", "davinciauto_core.cli", *args])
        else:
            self._process.setProgram(str(program))
            self._process.setArguments(args)

        # Environment
        env_map = os.environ.copy()
        env_map.update(env)
        env_object = self._process.processEnvironment()
        env_object.clear()
        for key, value in env_map.items():
            env_object.insert(key, value)
        self._process.setProcessEnvironment(env_object)

        self._process.readyReadStandardError.connect(self._handle_stderr)
        self._process.finished.connect(self._on_finished)

        self._watcher.start(self._log_path)
        self._process.start()

    def stop(self) -> None:
        if not self.is_running():
            return
        assert self._process is not None
        if sys.platform.startswith("win"):
            self._process.terminate()
            if not self._process.waitForFinished(3000):
                self._process.kill()
        else:
            self._process.terminate()
            if not self._process.waitForFinished(3000):
                self._process.kill()

    # ------------------------------------------------------------------
    def _on_finished(self, exit_code: int, _status: QProcess.ExitStatus) -> None:
        self._watcher.stop()
        if self._log_path and self._log_path.exists():
            self._log_path.unlink(missing_ok=True)
        self.finished.emit(exit_code)
        self._process = None

    def _handle_stderr(self) -> None:
        if not self._process:
            return
        data = self._process.readAllStandardError().data()
        text = data.decode("utf-8", errors="replace")
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                self.stderr.emit(line)
            else:
                self.log_event.emit(event)

    def _build_cli_args(self, config: AppConfig, azure_key: Optional[str], eleven_key: Optional[str]) -> tuple[List[str], Dict[str, str]]:
        assert self._log_path is not None
        args: List[str] = ["--progress-log", str(self._log_path)]

        paths = config.paths
        if paths.script:
            args += ["--script", paths.script]
        if paths.output_dir:
            args += ["--output", paths.output_dir]
        if paths.subtitle_srt:
            args += ["--subtitle-srt", paths.subtitle_srt]
        if paths.scene_plan:
            args += ["--scene-plan", paths.scene_plan]
        if paths.bgm_plan:
            args += ["--bgm-plan", paths.bgm_plan]

        args += ["--subtitle-lang", config.subtitle_lang]
        args += ["--format", config.subtitle_format]
        args += ["--audio-format", config.audio_format]
        args += ["--concurrency", str(config.concurrency)]
        args += ["--provider", config.provider]
        if config.voice_preset:
            args += ["--voice-preset", config.voice_preset]
        if not config.enable_bgm_workflow:
            args += ["--no-bgm-workflow"]
        if config.fake_tts:
            args += ["--fake-tts"]

        env: Dict[str, str] = {}
        if azure_key:
            env["AZURE_SPEECH_KEY"] = azure_key
        if eleven_key:
            env["ELEVENLABS_API_KEY"] = eleven_key
        ffmpeg = resource_path("Resources/bin/ffmpeg")
        ffprobe = resource_path("Resources/bin/ffprobe")
        if ffmpeg.exists():
            env.setdefault("DAVA_FFMPEG_PATH", str(ffmpeg))
            env.setdefault("DAVINCIAUTO_FFMPEG", str(ffmpeg))
        if ffprobe.exists():
            env.setdefault("DAVA_FFPROBE_PATH", str(ffprobe))
            env.setdefault("DAVINCIAUTO_FFPROBE", str(ffprobe))
        return args, env
