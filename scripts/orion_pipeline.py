#!/usr/bin/env python3
"""Convenience CLI for running the Orion TTS pipeline across projects.

This wrapper lets you trigger `run_tts_pipeline.py` for one or more
Orion episodes (e.g., OrionEp1 ... OrionEp15) or any other project that
follows the same folder structure under `projects/`.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable, List, Sequence


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
PROJECTS_ROOT = REPO_ROOT / "projects"


def discover_projects(pattern: str) -> List[str]:
    """Return project directory names under `projects/` matching the pattern."""
    matches: List[str] = []
    for path in sorted(PROJECTS_ROOT.iterdir()):
        if not path.is_dir():
            continue
        if path.name.startswith(pattern):
            matches.append(path.name)
    return matches


def build_pipeline_args(project: str, opts: argparse.Namespace) -> List[str]:
    """Translate CLI options into arguments for run_tts_pipeline."""
    args: List[str] = ["--project", project]

    def append_opt(flag: str, value: str | None) -> None:
        if value:
            args.extend([flag, value])

    append_opt("--script-md", opts.script_md)
    append_opt("--script-csv", opts.script_csv)
    append_opt("--input-srt", opts.input_srt)
    append_opt("--output-srt", opts.output_srt)
    append_opt("--merged-srt", opts.merged_srt)
    append_opt("--final-srt", opts.final_srt)
    append_opt("--timeline-csv", opts.timeline_csv)
    append_opt("--timeline-xml", opts.timeline_xml)
    append_opt("--export-xml", opts.export_xml)
    append_opt("--output-root", opts.output_root)
    append_opt("--exports-dir", opts.exports_dir)
    append_opt("--audio-dir", opts.audio_dir)

    if opts.sample_name:
        args.extend(["--sample-name", opts.sample_name])

    for path in opts.tts_config or []:
        args.extend(["--tts-config", path])

    if opts.scene_gap is not None:
        args.extend(["--scene-gap", str(opts.scene_gap)])

    if opts.timebase is not None:
        args.extend(["--timebase", str(opts.timebase)])

    if getattr(opts, "no_ntsc", False):
        args.append("--no-ntsc")
    elif getattr(opts, "ntsc", False):
        args.append("--ntsc")

    if opts.skip_csv:
        args.append("--skip-csv")
    if opts.skip_xml:
        args.append("--skip-xml")
    if opts.skip_srt:
        args.append("--skip-srt")

    return args


def run_pipeline_for_projects(projects: Sequence[str], opts: argparse.Namespace) -> None:
    if not projects:
        raise ValueError("No projects selected; specify names or use --all.")

    try:
        from run_tts_pipeline import main as run_tts_main  # type: ignore
    except ImportError as exc:  # pragma: no cover - defensive
        raise RuntimeError("Unable to import run_tts_pipeline") from exc

    failures: List[str] = []
    for project in projects:
        project_dir = PROJECTS_ROOT / project
        if not project_dir.exists():
            print(f"[WARN] Skip {project}: directory not found ({project_dir})", file=sys.stderr)
            failures.append(project)
            continue

        print(f"\n=== Orion TTS Pipeline :: {project} ===")
        pipeline_args = build_pipeline_args(project, opts)
        try:
            run_tts_main(pipeline_args)
        except Exception as exc:  # pragma: no cover - defensive
            failures.append(project)
            print(f"[ERROR] Pipeline failed for {project}: {exc}", file=sys.stderr)

    if failures:
        raise SystemExit(f"Pipeline failed or skipped for: {', '.join(failures)}")


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the Orion narration pipeline for one or more projects."
    )
    parser.add_argument(
        "projects",
        nargs="*",
        help="Project slugs (e.g., OrionEp8).",
    )
    parser.add_argument(
        "--project",
        dest="project_opts",
        action="append",
        help="Additional project slug to include. Can be passed multiple times.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Process all projects whose directory name starts with the pattern.",
    )
    parser.add_argument(
        "--pattern",
        default="OrionEp",
        help="Directory prefix to match when using --all (default: OrionEp).",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Project slug to exclude (can be repeated).",
    )

    parser.add_argument("--script-md")
    parser.add_argument("--script-csv")
    parser.add_argument("--input-srt")
    parser.add_argument("--output-srt")
    parser.add_argument("--merged-srt")
    parser.add_argument("--final-srt")
    parser.add_argument("--timeline-csv")
    parser.add_argument("--timeline-xml")
    parser.add_argument("--export-xml")
    parser.add_argument("--output-root")
    parser.add_argument("--exports-dir")
    parser.add_argument("--audio-dir")
    parser.add_argument("--sample-name")
    parser.add_argument(
        "--tts-config",
        action="append",
        help="Additional TTS config YAML path(s) to merge.",
    )
    parser.add_argument(
        "--scene-gap",
        type=float,
        help="Override scene gap seconds (default: project config / 3.0).",
    )
    parser.add_argument(
        "--timebase",
        type=int,
        help="Timeline timebase (default: 30).",
    )
    parser.add_argument(
        "--no-ntsc",
        action="store_true",
        help="Disable NTSC drop-frame (use integer FPS).",
    )
    parser.add_argument(
        "--ntsc",
        action="store_true",
        help="Explicitly enable NTSC drop-frame timing.",
    )
    parser.add_argument("--skip-srt", action="store_true")
    parser.add_argument("--skip-csv", action="store_true")
    parser.add_argument("--skip-xml", action="store_true")

    return parser.parse_args(argv)


def gather_projects(opts: argparse.Namespace) -> List[str]:
    selected = set(opts.projects or [])
    if opts.project_opts:
        selected.update(opts.project_opts)
    if opts.all:
        selected.update(discover_projects(opts.pattern))
    selected.difference_update(opts.exclude)
    return sorted(selected)


def main(argv: Iterable[str] | None = None) -> None:
    opts = parse_args(argv)
    projects = gather_projects(opts)
    if not projects:
        raise SystemExit("No projects specified. Provide names or use --all.")
    run_pipeline_for_projects(projects, opts)


if __name__ == "__main__":
    main()
