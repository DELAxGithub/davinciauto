"""Core orchestration logic for the Orion TTS pipeline prototype."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import yaml


@dataclass
class PipelineConfig:
    project_root: Path
    config_path: Optional[Path] = None
    output_dir: Optional[Path] = None
    dry_run: bool = False
    extra: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_paths(cls, project_root: Path, config_path: Optional[Path]) -> "PipelineConfig":
        project_root = project_root.resolve()
        data: Dict[str, str] = {}
        if config_path and config_path.exists():
            with config_path.open(encoding="utf-8") as fh:
                loaded = yaml.safe_load(fh) or {}
            if not isinstance(loaded, dict):
                raise ValueError("config must be a mapping")
            data = {str(k): str(v) for k, v in loaded.items() if v is not None}
        output_dir = Path(data.get("output_dir", project_root / "outputs"))
        return cls(project_root=project_root, config_path=config_path, output_dir=output_dir, extra=data)


@dataclass
class PipelineSummary:
    scripts: List[Path]
    srts: List[Path]
    audio_dir: Optional[Path]
    actions: List[str]

    def to_dict(self) -> Dict[str, str]:
        return {
            "scripts": ",".join(str(p) for p in self.scripts),
            "srts": ",".join(str(p) for p in self.srts),
            "audio_dir": str(self.audio_dir) if self.audio_dir else "",
            "actions": ";".join(self.actions),
        }


def run_pipeline(config: PipelineConfig, dry_run: bool) -> Dict[str, str]:
    """Collect inputs and (in the future) execute synthesis.

    現時点では入力整合性の確認のみを行い、実際の TTS は未実装です。
    """
    project_root = config.project_root
    inputs_dir = project_root / "inputs"
    exports_dir = project_root / "exports"
    audio_dir = project_root / "audio"

    scripts = sorted(inputs_dir.glob("*.md"))
    srts = sorted(inputs_dir.glob("*.srt"))

    actions = [
        "validated inputs directory",
        "collected markdown scripts",
        "collected srt files",
    ]
    if dry_run:
        actions.append("dry-run: synthesis skipped")
    else:
        actions.append("TODO: integrate synthesis backend")

    summary = PipelineSummary(scripts=scripts, srts=srts, audio_dir=audio_dir, actions=actions)
    return summary.to_dict()
