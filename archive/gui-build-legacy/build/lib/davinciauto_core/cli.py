from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Iterable, Optional

from .config.voice_presets import VoicePresetManager
from .pipeline import PipelineConfig, perform_self_check, run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="DaVinci Auto pipeline CLI")
    parser.add_argument("--self-check", action="store_true", help="環境セルフチェックをJSONで出力")
    parser.add_argument("--script", help="入力スクリプトファイル")
    parser.add_argument("--output-root", default="output", help="出力ディレクトリのルート (default: output)")
    parser.add_argument("--rate", type=float, default=1.0, help="再生速度倍率")
    parser.add_argument("--fake-tts", action="store_true", help="TTSをスキップして無音を生成（デバッグ用）")
    parser.add_argument("--voice-preset", help="音声品質プリセット名")
    parser.add_argument("--disable-voice-parsing", action="store_true", help="音声指示解析を無効化")
    parser.add_argument("--debug-llm", action="store_true", help="LLM整形プロセスのデバッグ情報を表示")
    parser.add_argument("--verbose-debug", action="store_true", help="--debug-llm時に詳細デバッグ出力を有効化")
    parser.add_argument("--list-presets", action="store_true", help="利用可能な音声プリセット一覧を表示して終了")
    parser.add_argument("--progress-log", help="進捗JSONLを書き出すパス")
    parser.add_argument("--project-id", help="任意のプロジェクト識別子")
    parser.add_argument("--provider", default="elevenlabs", help="TTSプロバイダ名")
    parser.add_argument("--target", default="resolve", help="出力ターゲット (resolve/premiere 等)")
    parser.add_argument("--frame-rate", type=float, default=23.976, help="タイムラインのフレームレート")
    parser.add_argument("--sample-rate", type=int, default=48000, help="サンプルレート (Hz)")
    parser.add_argument("--concurrency", type=int, default=1, help="TTS並列度 (>=1)")
    parser.add_argument("--api-key", help="プロバイダAPIキー (BYOK)")
    return parser


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list_presets:
        manager = VoicePresetManager()
        print("🎤 利用可能な音声プリセット:")
        for name, info in manager.list_presets().items():
            print(f"  {name}: {info['name']} - {info['description']}")
        return 0

    if args.self_check:
        info = perform_self_check()
        print(json.dumps(info, ensure_ascii=False))
        return 0 if info.get("ok", False) else os.EX_UNAVAILABLE

    if not args.script:
        parser.error("--script is required unless using --list-presets")

    if args.concurrency < 1:
        print("Runtime error: --concurrency must be >= 1", file=sys.stderr)
        return os.EX_USAGE

    config = PipelineConfig(
        script_path=Path(args.script),
        output_root=Path(args.output_root),
        fake_tts=args.fake_tts,
        rate=args.rate,
        voice_preset=args.voice_preset,
        enable_voice_parsing=not args.disable_voice_parsing,
        debug_llm=args.debug_llm,
        verbose_debug=args.verbose_debug,
        progress_log_path=Path(args.progress_log) if args.progress_log else None,
        project_id=args.project_id,
        provider=args.provider,
        target=args.target,
        frame_rate=args.frame_rate,
        sample_rate=args.sample_rate,
        concurrency=args.concurrency,
        api_key=args.api_key,
    )

    try:
        result = run_pipeline(config)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return os.EX_USAGE
    except PermissionError as exc:
        print(f"Permission error: {exc}", file=sys.stderr)
        return os.EX_CANTCREAT
    except RuntimeError as exc:
        print(f"Runtime error: {exc}", file=sys.stderr)
        return os.EX_UNAVAILABLE
    except KeyboardInterrupt:
        print("Interrupted", file=sys.stderr)
        return os.EX_TEMPFAIL
    except Exception as exc:  # pragma: no cover - unexpected
        print(f"Unexpected error: {exc}", file=sys.stderr)
        return os.EX_TEMPFAIL

    print("✅ Completed.")
    print(f"- Audio:     {result.audio_path}")
    print(f"- Segments:  {[str(p) for p in result.audio_segments]}")
    print(f"- SRT:       {result.subtitles_path}")
    print(f"- Plain TXT: {result.plain_subtitles_path}")
    print(f"- Storyboard:{result.storyboard_pack_path}")
    if result.cost_summary:
        print(result.cost_summary)
    if result.usage_log_path:
        print(f"- Usage log: {result.usage_log_path}")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
