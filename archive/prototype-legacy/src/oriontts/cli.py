"""Command line interface for the Orion TTS pipeline prototype."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import click

from .pipeline import PipelineConfig, run_pipeline


@click.group()
def app() -> None:
    """Orion TTS pipeline tools."""


@app.command("run")
@click.option("--project-root", type=click.Path(path_type=Path), required=True, help="プロジェクトのルートディレクトリ")
@click.option("--config", type=click.Path(path_type=Path), help="パイプライン設定 YAML")
@click.option("--dry-run", is_flag=True, help="処理結果を生成せず、解析ログのみ出力")
def run_command(project_root: Path, config: Optional[Path], dry_run: bool) -> None:
    """サンプルプロジェクトに対してパイプラインを実行します。"""
    pipeline_config = PipelineConfig.from_paths(project_root=project_root, config_path=config)
    summary = run_pipeline(pipeline_config, dry_run=dry_run)
    click.echo(json.dumps(summary, ensure_ascii=False, indent=2))


@app.command("scaffold")
@click.argument("target", type=click.Path(path_type=Path))
@click.option("--overwrite", is_flag=True, help="既存ファイルを上書き")
def scaffold_command(target: Path, overwrite: bool) -> None:
    """最小プロジェクト構成を生成します。"""
    from .scaffold import scaffold_project  # local import to avoid side-effects

    result = scaffold_project(target, overwrite=overwrite)
    click.echo(f"Scaffolded project at {result}")


if __name__ == "__main__":  # pragma: no cover
    app()
