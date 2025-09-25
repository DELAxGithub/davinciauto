from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from importlib import metadata
from pathlib import Path
from typing import Iterable, Optional, Tuple

from davinciauto_core.pipeline import PipelineConfig, perform_self_check, run_pipeline


def _resolve_version() -> str:
    override = os.environ.get("DAVINCIAUTO_CLI_VERSION") or os.environ.get("BUILD_VERSION")
    if override:
        return override
    candidates = []
    try:
        candidates.append(Path(sys.argv[0]).resolve().parent / "VERSION")
    except Exception:
        pass
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / "VERSION")
    for candidate in candidates:
        if candidate and candidate.exists():
            text = candidate.read_text(encoding="utf-8").strip()
            if text:
                return text
    candidates = ["davinciauto-cli", "davinciauto-core"]
    for name in candidates:
        try:
            return metadata.version(name)
        except metadata.PackageNotFoundError:
            continue
    return "0.0.0"


def _resolve_tool(tool: str, cli_arg: Optional[str] = None) -> Tuple[str, str]:
    """Locate external tool with deterministic precedence."""

    def candidate(value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        if os.path.exists(value):
            return value
        resolved = shutil.which(value)
        return resolved

    if cli_arg:
        resolved = candidate(cli_arg)
        if resolved:
            return resolved, "flag"
        raise SystemExit(f"{tool} specified via flag but not found: {cli_arg}")

    env_map = {
        "ffmpeg": ["DAVINCIAUTO_FFMPEG", "DAVA_FFMPEG_PATH", "FFMPEG"],
        "ffprobe": ["DAVINCIAUTO_FFPROBE", "DAVA_FFPROBE_PATH", "FFPROBE"],
    }
    for env_name in env_map[tool]:
        resolved = candidate(os.getenv(env_name))
        if resolved:
            return resolved, f"env:{env_name}"

    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        bundled = Path(meipass) / "bin" / tool
        if bundled.exists():
            return str(bundled), "bundle"

    resolved = shutil.which(tool)
    if resolved:
        return resolved, "path"

    raise SystemExit(
        f"{tool} not found. Provide --{tool} or set one of "
        f"{', '.join(env_map[tool])}"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="davinciauto-cli",
        description="DaVinci Auto pipeline command-line interface",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"davinciauto-cli {_resolve_version()}"
    )
    parser.add_argument(
        "--self-check",
        action="store_true",
        help="run environment diagnostics and exit",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit JSON payloads for --self-check",
    )

    sub = parser.add_subparsers(dest="command")

    run_cmd = sub.add_parser(
        "run",
        help="execute the pipeline for a given script",
    )
    run_cmd.add_argument("--script", required=True, help="path to input script file")
    run_cmd.add_argument("--output", required=True, help="output directory root")
    run_cmd.add_argument(
        "--provider",
        default=None,
        help="TTS provider identifier (default: azure)",
    )
    run_cmd.add_argument("--bgm-plan", help="BGM/SE plan JSON path", dest="bgm_plan")
    run_cmd.add_argument(
        "--target",
        default="resolve",
        help="output target (resolve/premiere)",
    )
    run_cmd.add_argument(
        "--fake-tts",
        action="store_true",
        help="generate silent audio instead of contacting a provider",
    )
    run_cmd.add_argument(
        "--concurrency",
        type=int,
        default=1,
        help="TTS concurrency (>=1)",
    )
    run_cmd.add_argument(
        "--frame-rate",
        type=float,
        default=23.976,
        help="timeline frame rate",
    )
    run_cmd.add_argument(
        "--rate",
        type=float,
        default=1.0,
        help="speech speed multiplier",
    )
    run_cmd.add_argument(
        "--voice-preset",
        help="voice preset name to use (optional)",
    )
    run_cmd.add_argument(
        "--project-id",
        help="optional project identifier stored in results",
    )
    run_cmd.add_argument(
        "--api-key",
        help="TTS provider API key (overrides ELEVENLABS_API_KEY when provider=elevenlabs)",
    )
    run_cmd.add_argument(
        "--progress-log",
        help="path to write JSONL progress events",
    )
    run_cmd.add_argument("--ffmpeg", help="path to ffmpeg executable")
    run_cmd.add_argument("--ffprobe", help="path to ffprobe executable")

    return parser


def _self_check(json_mode: bool) -> int:
    info = perform_self_check()

    bundle_dir = Path(sys.argv[0]).resolve().parent
    internal_dir = Path(getattr(sys, "_MEIPASS", bundle_dir))
    licenses_candidates = [internal_dir / "licenses", bundle_dir / "licenses"]
    licenses_present = any(path.exists() for path in licenses_candidates)

    frozen = internal_dir != bundle_dir
    issues = info.setdefault("issues", []) if isinstance(info, dict) else []
    if frozen and not licenses_present:
        issues.append("licenses-missing")

    info["licenses"] = {
        "present": licenses_present,
        "paths_checked": [str(p) for p in licenses_candidates],
    }
    info["bundle"] = {
        "layout": "pyinstaller/onedir" if frozen else "editable",
        "root": str(bundle_dir if frozen else Path.cwd()),
        "binary_dir": str(bundle_dir),
        "internal_dir": str(internal_dir),
        "is_frozen": frozen,
    }
    if frozen and not licenses_present:
        info["ok"] = False

    try:
        ffmpeg_path, ffmpeg_source = _resolve_tool("ffmpeg")
        os.environ.setdefault("DAVA_FFMPEG_PATH", ffmpeg_path)
        os.environ.setdefault("DAVINCIAUTO_FFMPEG", ffmpeg_path)
        info["ffmpeg"] = {"path": ffmpeg_path, "source": ffmpeg_source}
        info["ffmpeg_path"] = ffmpeg_path
    except SystemExit:
        info.setdefault("issues", []).append("ffmpeg-not-found")

    try:
        ffprobe_path, ffprobe_source = _resolve_tool("ffprobe")
        os.environ.setdefault("DAVA_FFPROBE_PATH", ffprobe_path)
        os.environ.setdefault("DAVINCIAUTO_FFPROBE", ffprobe_path)
        info["ffprobe"] = {"path": ffprobe_path, "source": ffprobe_source}
        info["ffprobe_path"] = ffprobe_path
    except SystemExit:
        info.setdefault("issues", []).append("ffprobe-not-found")

    info["version"] = info.get("version") or _resolve_version()

    payload = json.dumps(info, ensure_ascii=False, indent=None if json_mode else 2)
    print(payload)
    return 0 if info.get("ok", False) else 1


def _run_pipeline(args: argparse.Namespace) -> int:
    config = PipelineConfig(
        script_path=Path(args.script),
        output_root=Path(args.output),
        provider=(args.provider or "azure"),
        target=args.target,
        fake_tts=args.fake_tts,
        concurrency=max(1, args.concurrency),
        frame_rate=args.frame_rate,
        rate=args.rate,
        voice_preset=args.voice_preset,
        project_id=args.project_id,
        progress_log_path=Path(args.progress_log) if args.progress_log else None,
        api_key=args.api_key,
        bgm_plan_path=Path(args.bgm_plan).expanduser() if args.bgm_plan else None,
    )

    ffmpeg_path, _ = _resolve_tool("ffmpeg", args.ffmpeg)
    ffprobe_path, _ = _resolve_tool("ffprobe", args.ffprobe)
    os.environ["DAVA_FFMPEG_PATH"] = ffmpeg_path
    os.environ["DAVINCIAUTO_FFMPEG"] = ffmpeg_path
    os.environ["DAVA_FFPROBE_PATH"] = ffprobe_path
    os.environ["DAVINCIAUTO_FFPROBE"] = ffprobe_path

    try:
        result = run_pipeline(config)
    except Exception as exc:  # pragma: no cover - runtime errors propagate to CLI
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    summary = {
        "audio": str(result.audio_path),
        "subtitles": str(result.subtitles_path),
        "plain_subtitles": str(result.plain_subtitles_path),
        "storyboard": str(result.storyboard_pack_path),
        "extra": result.extra,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.self_check:
        return _self_check(args.json)

    if args.command == "run":
        return _run_pipeline(args)

    parser.print_help()
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
