"""Utility helpers to scaffold sample projects."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

SAMPLE_MD = """# Sample Episode

ようこそ、サンプルエピソードへ。
これは雛形用のごく短い原稿です。
"""

SAMPLE_SRT = """1
00:00:00,000 --> 00:00:04,000
サンプルの字幕です。

2
00:00:04,000 --> 00:00:08,000
タイムコードの確認用です。
"""


def scaffold_project(target: Path, overwrite: bool = False) -> Path:
    target = target.resolve()
    project_inputs = target / "inputs"
    project_exports = target / "exports"
    project_outputs = target / "output"

    for directory in (project_inputs, project_exports, project_outputs):
        directory.mkdir(parents=True, exist_ok=True)

    files: Iterable[tuple[Path, str]] = (
        (project_inputs / "sample.md", SAMPLE_MD),
        (project_inputs / "sample.srt", SAMPLE_SRT),
        (target / "README.md", "# Sample Orion Project\n\nこのプロジェクトは雛形生成で作られました。\n"),
    )

    for path, content in files:
        if path.exists() and not overwrite:
            continue
        path.write_text(content, encoding="utf-8")

    return target
