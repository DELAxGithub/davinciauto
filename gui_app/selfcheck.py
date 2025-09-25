"""Self-check routines executed on application startup."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import appdirs

from .util.paths import resource_path


@dataclass
class SelfCheckResult:
    ok: bool
    details: Dict[str, Dict[str, str]]


class SelfCheck:
    def __init__(self) -> None:
        self._results: Dict[str, Dict[str, str]] = {}

    def run(self) -> SelfCheckResult:
        checks: List[bool] = []
        checks.append(self._check_qt())
        checks.append(self._check_ffmpeg())
        checks.append(self._check_speech_sdk())
        checks.append(self._check_config_write())
        ok = all(item.get("status") == "ok" for item in self._results.values())
        return SelfCheckResult(ok=ok, details=self._results)

    def _record(self, key: str, status: str, message: str) -> None:
        self._results[key] = {"status": status, "message": message}

    def _check_qt(self) -> bool:
        try:
            from PySide6.QtWidgets import QApplication, QWidget  # noqa: F401
        except Exception as exc:  # pragma: no cover
            self._record("qt", "error", f"PySide6 import failed: {exc}")
            return False
        self._record("qt", "ok", "PySide6 available")
        return True

    def _check_ffmpeg(self) -> bool:
        ffmpeg_path = shutil.which("ffmpeg") or str(resource_path("Resources/bin/ffmpeg"))
        if not ffmpeg_path:
            self._record("ffmpeg", "error", "ffmpeg not found")
            return False
        try:
            subprocess.run([ffmpeg_path, "-version"], capture_output=True, check=True)
        except Exception as exc:  # pragma: no cover
            self._record("ffmpeg", "error", f"ffmpeg failed: {exc}")
            return False
        ffprobe_path = shutil.which("ffprobe") or str(resource_path("Resources/bin/ffprobe"))
        if not ffprobe_path:
            self._record("ffprobe", "warn", "ffprobe not found")
        else:
            try:
                subprocess.run([ffprobe_path, "-version"], capture_output=True, check=True)
            except Exception as exc:
                self._record("ffprobe", "warn", f"ffprobe failed: {exc}")
            else:
                self._record("ffprobe", "ok", "ffprobe available")
        self._record("ffmpeg", "ok", "ffmpeg available")
        return True

    def _check_speech_sdk(self) -> bool:
        try:
            import azure.cognitiveservices.speech  # noqa: F401
        except Exception as exc:
            self._record("azure_speech", "warn", f"Azure Speech SDK import failed: {exc}")
            return False
        self._record("azure_speech", "ok", "Azure Speech SDK available")
        return True

    def _check_config_write(self) -> bool:
        try:
            target_dir = Path(appdirs.user_config_dir("davinciauto_gui", "davinciauto"))
            target_dir.mkdir(parents=True, exist_ok=True)
            test_file = target_dir / "selfcheck.tmp"
            test_file.write_text(json.dumps({"ping": "pong"}), encoding="utf-8")
            test_file.unlink(missing_ok=True)
        except Exception as exc:
            self._record("write", "error", f"Config write failed: {exc}")
            return False
        self._record("write", "ok", "Config write ok")
        return True
