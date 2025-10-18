"""Configuration handling for the PySide6 GUI."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Dict, Optional

import appdirs
import keyring

CONFIG_VERSION = 1
SERVICE_NAME = "davinciauto_gui"
AZURE_ACCOUNT = "azure_speech"
ELEVEN_ACCOUNT = "eleven_labs"


@dataclass
class PathsConfig:
    output_dir: Optional[str] = None
    script: Optional[str] = None
    subtitle_srt: Optional[str] = None
    scene_plan: Optional[str] = None
    bgm_plan: Optional[str] = None


@dataclass
class AppConfig:
    version: int = CONFIG_VERSION
    provider: str = "azure"
    voice_preset: Optional[str] = None
    subtitle_lang: str = "ja-JP"
    subtitle_format: str = "srt"
    audio_format: str = "mp3"
    concurrency: int = 1
    enable_bgm_workflow: bool = True
    fake_tts: bool = False
    paths: PathsConfig = field(default_factory=PathsConfig)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["paths"] = asdict(self.paths)
        return data

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "AppConfig":
        paths = data.get("paths", {})
        return AppConfig(
            version=data.get("version", CONFIG_VERSION),
            provider=data.get("provider", "azure"),
            voice_preset=data.get("voice_preset"),
            subtitle_lang=data.get("subtitle_lang", "ja-JP"),
            subtitle_format=data.get("subtitle_format", "srt"),
            audio_format=data.get("audio_format", "mp3"),
            concurrency=data.get("concurrency", 1),
            enable_bgm_workflow=data.get("enable_bgm_workflow", True),
            fake_tts=data.get("fake_tts", False),
            paths=PathsConfig(**{k: paths.get(k) for k in PathsConfig().__dict__.keys()}),
        )


class ConfigManager:
    """Load/save configuration and manage secrets via keyring."""

    def __init__(self) -> None:
        config_dir = Path(appdirs.user_config_dir("davinciauto_gui", "davinciauto"))
        config_dir.mkdir(parents=True, exist_ok=True)
        self._config_path = config_dir / "config.json"

    @property
    def path(self) -> Path:
        return self._config_path

    def load(self) -> AppConfig:
        if not self._config_path.exists():
            return AppConfig()
        try:
            content = json.loads(self._config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            # 破損した場合はバックアップして初期化
            backup = self._config_path.with_suffix(".broken")
            self._config_path.rename(backup)
            return AppConfig()
        config = AppConfig.from_dict(content)
        if config.version != CONFIG_VERSION:
            config.version = CONFIG_VERSION
        return config

    def save(self, config: AppConfig) -> None:
        data = config.to_dict()
        tmp_path = self._config_path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp_path, self._config_path)

    # ------------------------------------------------------------------
    # Key management
    # ------------------------------------------------------------------
    def set_api_key(self, provider: str, value: str) -> None:
        keyring.set_password(SERVICE_NAME, provider, value)

    def get_api_key(self, provider: str) -> Optional[str]:
        try:
            return keyring.get_password(SERVICE_NAME, provider)
        except keyring.errors.KeyringError:
            return None

    def delete_api_key(self, provider: str) -> None:
        try:
            keyring.delete_password(SERVICE_NAME, provider)
        except keyring.errors.PasswordDeleteError:
            pass

    # Convenience for Azure/Eleven Labs
    def set_azure_key(self, value: str) -> None:
        self.set_api_key(AZURE_ACCOUNT, value)

    def get_azure_key(self) -> Optional[str]:
        return self.get_api_key(AZURE_ACCOUNT)

    def set_eleven_labs_key(self, value: str) -> None:
        self.set_api_key(ELEVEN_ACCOUNT, value)

    def get_eleven_labs_key(self) -> Optional[str]:
        return self.get_api_key(ELEVEN_ACCOUNT)
