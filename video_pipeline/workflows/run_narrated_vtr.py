#!/usr/bin/env python3
"""Thin phase runner for narrated VTR projects.

This runner intentionally does not provide an "all" phase. Narrated client work
usually has review gates between script, TTS, Resolve, picture edit, and render.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Iterable

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RESOLVE_CLI = Path("/Users/delaxpro/src/claude-config/skills/davinci-resolve/scripts/resolve_cli.py")


def as_path(base: Path, value: str | None, default: Path | None = None) -> Path:
    if not value:
        if default is None:
            raise ValueError("path value is required")
        return default
    path = Path(value).expanduser()
    return path if path.is_absolute() else (base / path).resolve()


def load_config(path: Path) -> tuple[Path, dict]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return path.parent.resolve(), data


def run(cmd: list[str], cwd: Path) -> int:
    print("+ " + " ".join(cmd), flush=True)
    return subprocess.run(cmd, cwd=cwd).returncode


def project_values(config_base: Path, config: dict) -> dict:
    project_dir = as_path(config_base, config.get("project_dir"))
    project = {
        "project_dir": project_dir,
        "project_id": config["project_id"],
        "title": config["title"],
        "script": as_path(config_base, config.get("script")),
        "fps": float(config.get("fps", 29.97)),
        "target_duration_sec": config.get("target_duration_sec"),
        "pronunciation_rules": as_path(
            config_base,
            config.get("pronunciation_rules"),
            project_dir / "inputs/pronunciation_rules.csv",
        ),
        "tts_yaml": project_dir / "outputs/tts/gemini_tts.yaml",
        "reviewed_tts_yaml": project_dir / "outputs/tts/gemini_tts.reviewed.yaml",
        "audio_dir": project_dir / "outputs/audio/narration",
        "resolve_project": config.get("resolve", {}).get("project", ""),
        "timeline": config.get("resolve", {}).get("timeline", f"{config['project_id']}_v001"),
        "bin_name": config.get("resolve", {}).get("bin_name", config["project_id"]),
        "resolve_cli": as_path(
            config_base,
            config.get("resolve_cli"),
            DEFAULT_RESOLVE_CLI,
        ),
    }
    return project


def module_cmd(module: str, *args: str) -> list[str]:
    return [sys.executable, "-m", module, *args]


def resolve_cmd(project: dict, script: str, globals_json: dict) -> list[str]:
    return [
        sys.executable,
        str(project["resolve_cli"]),
        "run-script",
        "--script",
        str(REPO_ROOT / script),
        "--globals-json",
        json.dumps(globals_json, ensure_ascii=False),
        "--apply",
    ]


def run_phase(phase: str, project: dict, only_indices: str | None, force: bool) -> int:
    project_dir = project["project_dir"]
    if phase == "script-review":
        cmd = module_cmd(
            "video_pipeline.workflows.script_review",
            "--script",
            str(project["script"]),
            "--project-dir",
            str(project_dir),
            "--project-id",
            project["project_id"],
            "--title",
            project["title"],
            "--fps",
            str(project["fps"]),
        )
        if project["target_duration_sec"]:
            cmd.extend(["--target-duration-sec", str(project["target_duration_sec"])])
        return run(cmd, REPO_ROOT)

    if phase == "build-artifacts":
        cmd = module_cmd(
            "video_pipeline.workflows.narrated_vtr",
            "--script",
            str(project["script"]),
            "--project-dir",
            str(project_dir),
            "--project-id",
            project["project_id"],
            "--title",
            project["title"],
            "--fps",
            str(project["fps"]),
            "--pronunciation-rules",
            str(project["pronunciation_rules"]),
        )
        return run(cmd, REPO_ROOT)

    if phase == "pronunciation-review":
        return run(
            module_cmd(
                "video_pipeline.workflows.review_tts_pronunciation",
                "--yaml",
                str(project["tts_yaml"]),
                "--out-yaml",
                str(project["reviewed_tts_yaml"]),
                "--report-csv",
                str(project_dir / "outputs/tts/pronunciation_review.csv"),
                "--rules-csv",
                str(project["pronunciation_rules"]),
            ),
            REPO_ROOT,
        )

    if phase == "tts":
        cmd = module_cmd(
            "video_pipeline.workflows.generate_gemini_tts",
            "--yaml",
            str(project["reviewed_tts_yaml"]),
            "--out-dir",
            str(project["audio_dir"]),
            "--project-id",
            project["project_id"],
        )
        if only_indices:
            cmd.extend(["--only-indices", only_indices])
        if force:
            cmd.append("--force")
        return run(cmd, REPO_ROOT)

    if phase == "recalc":
        return run(
            module_cmd(
                "video_pipeline.workflows.recalculate_from_audio",
                "--project-dir",
                str(project_dir),
                "--project-id",
                project["project_id"],
                "--audio-dir",
                str(project["audio_dir"]),
            ),
            REPO_ROOT,
        )

    if phase in {"resolve-dry-run", "resolve-apply"}:
        return run(
            resolve_cmd(
                project,
                "scripts/apply_narrated_vtr_timeline.py",
                {
                    "PROJECT_DIR": str(project_dir),
                    "EXPECTED_PROJECT": project["resolve_project"],
                    "TIMELINE_NAME": project["timeline"],
                    "BIN_NAME": project["bin_name"],
                    "APPLY": phase == "resolve-apply",
                },
            ),
            REPO_ROOT,
        )

    if phase == "qc":
        return run(
            resolve_cmd(
                project,
                "scripts/report_narrated_vtr_timeline.py",
                {
                    "PROJECT_DIR": str(project_dir),
                    "TIMELINE_NAME": project["timeline"],
                },
            ),
            REPO_ROOT,
        )

    if phase in {"render-job-dry-run", "render-job"}:
        return run(
            resolve_cmd(
                project,
                "scripts/prepare_narrated_vtr_review_render.py",
                {
                    "PROJECT_DIR": str(project_dir),
                    "EXPECTED_PROJECT": project["resolve_project"],
                    "TIMELINE_NAME": project["timeline"],
                    "CUSTOM_NAME": f"{project['timeline']}_review",
                    "ADD_JOB": phase == "render-job",
                },
            ),
            REPO_ROOT,
        )

    raise SystemExit(f"Unknown phase: {phase}")


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one narrated VTR pipeline phase.")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument(
        "phase",
        choices=[
            "script-review",
            "build-artifacts",
            "pronunciation-review",
            "tts",
            "recalc",
            "resolve-dry-run",
            "resolve-apply",
            "qc",
            "render-job-dry-run",
            "render-job",
        ],
    )
    parser.add_argument("--only-indices", help="For tts: comma-separated segment indices to regenerate.")
    parser.add_argument("--force", action="store_true", help="For tts: overwrite existing audio files.")
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    config_base, config = load_config(args.config)
    project = project_values(config_base, config)
    return run_phase(args.phase, project, args.only_indices, args.force)


if __name__ == "__main__":
    raise SystemExit(main())
