from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Iterable, Optional

from .config.voice_presets import VoicePresetManager
from .pipeline import PipelineConfig, perform_self_check, run_pipeline


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="DaVinci Auto pipeline CLI")

    parser.add_argument("--config", help="設定 JSON ファイルへのパス", default=None)
    parser.add_argument("--self-check", action="store_true", help="環境セルフチェックを実行して終了")

    # 入力/出力
    parser.add_argument("--script", help="入力スクリプトファイル")
    parser.add_argument("--script-text", help="スクリプト本文を直接渡す（オプション）")
    parser.add_argument("--output", dest="output", help="出力ディレクトリ")
    parser.add_argument("--output-root", dest="output_root", help="互換オプション: --output と同等")
    parser.add_argument("--progress-log", help="進捗 JSONL を書き出すパス")

    # 音声関連
    parser.add_argument("--fake-tts", action="store_true", help="TTS を実行せず無音を生成")
    parser.add_argument("--rate", type=float, default=1.0, help="再生速度倍率")
    parser.add_argument("--voice-preset", help="音声プリセット名")
    parser.add_argument("--disable-voice-parsing", action="store_true", help="台本内の音声指示解析を無効化")

    # サブタイトル/シーン
    parser.add_argument("--subtitle-lang", default=None, help="字幕言語 (BCP47)")
    parser.add_argument("--format", dest="subtitle_format", default=None, help="字幕フォーマット (例: srt)")
    parser.add_argument("--audio-format", default=None, help="音声出力フォーマット (例: mp3)")
    parser.add_argument("--subtitle-text", help="字幕本文ファイルを指定")
    parser.add_argument("--subtitle-srt", help="既存 SRT を利用")
    parser.add_argument("--scene-plan", help="シーン構成 Markdown を指定")
    parser.add_argument("--bgm-plan", help="BGM/SE プラン JSON を指定")
    parser.add_argument("--timeline-csv", help="既存タイムライン CSV を指定")

    # 制御
    parser.add_argument("--provider", default=None, help="TTS プロバイダ名 (既定: azure)")
    parser.add_argument("--target", default="resolve", help="出力ターゲット (resolve/premiere 等)")
    parser.add_argument("--frame-rate", type=float, default=23.976, help="タイムラインのフレームレート")
    parser.add_argument("--sample-rate", type=int, default=48000, help="サンプルレート (Hz)")
    parser.add_argument("--concurrency", type=int, default=1, help="TTS 並列度")
    parser.add_argument("--api-key", help="プロバイダ API キー (BYOK)")
    parser.add_argument("--no-bgm-workflow", action="store_true", help="BGM/SE 自動生成を無効化")

    # デバッグ
    parser.add_argument("--debug-llm", action="store_true", help="LLM 整形処理のデバッグ出力")
    parser.add_argument("--verbose-debug", action="store_true", help="追加デバッグ出力")
    parser.add_argument("--list-presets", action="store_true", help="利用可能な音声プリセット一覧を表示して終了")
    parser.add_argument("--project-id", help="任意のプロジェクト ID")

    return parser


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    config_json: dict[str, object] = {}
    if args.config:
        config_path = Path(args.config)
        if not config_path.exists():
            parser.error(f"config file not found: {config_path}")
        try:
            config_json = json.loads(config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:  # pragma: no cover
            parser.error(f"failed to decode config JSON: {exc}")

    if args.list_presets:
        manager = VoicePresetManager()
        print("🎤 利用可能な音声プリセット:")
        for name, info in manager.list_presets().items():
            print(f"  {name}: {info['name']} - {info['description']}")
        return 0

    if args.self_check:
        info = perform_self_check()
        print(json.dumps(info, ensure_ascii=False))
        return 0 if info.get("ok", False) else 1

    config = assemble_config(args, config_json)

    try:
        result = run_pipeline(config)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except PermissionError as exc:
        print(f"Permission error: {exc}", file=sys.stderr)
        return 3
    except RuntimeError as exc:
        lowered = str(exc).lower()
        if any(token in lowered for token in ("auth", "unauthorized", "forbidden")):
            print(exc, file=sys.stderr)
            return 3
        print(exc, file=sys.stderr)
        return 4
    except KeyboardInterrupt:
        print("Interrupted", file=sys.stderr)
        return 5
    except Exception as exc:  # pragma: no cover - unexpected
        print(f"Unexpected error: {exc}", file=sys.stderr)
        return 4

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


def assemble_config(args: argparse.Namespace, config_json: dict[str, object]) -> PipelineConfig:
    def get_json(path: str, default=None):
        keys = path.split(".")
        node: object = config_json
        for key in keys:
            if isinstance(node, dict) and key in node:
                node = node[key]
            else:
                return default
        return node

    script_path = args.script or get_json("script")
    if not script_path and not args.script_text:
        raise ValueError("--script または --script-text を指定してください")

    output = args.output or args.output_root or get_json("output_root", "output")
    progress_log = args.progress_log or get_json("progress_log_path")

    pcfg = PipelineConfig(
        script_path=Path(script_path).expanduser() if script_path else None,
        script_text=args.script_text or get_json("script_text"),
        output_root=Path(output).expanduser(),
        fake_tts=args.fake_tts or bool(get_json("fake_tts", False)),
        rate=args.rate,
        voice_preset=args.voice_preset or get_json("voice_preset"),
        enable_voice_parsing=not args.disable_voice_parsing,
        debug_llm=args.debug_llm or bool(get_json("debug_llm", False)),
        verbose_debug=args.verbose_debug or bool(get_json("verbose_debug", False)),
        progress_log_path=Path(progress_log).expanduser() if progress_log else None,
        concurrency=int(args.concurrency),
        project_id=args.project_id or get_json("project_id"),
        provider=args.provider or get_json("provider", "azure"),
        target=args.target or get_json("target", "resolve"),
        frame_rate=float(args.frame_rate),
        sample_rate=int(args.sample_rate),
        api_key=args.api_key or get_json("api_key"),
        subtitle_lang=args.subtitle_lang or get_json("subtitle_lang", "ja-JP"),
        subtitle_format=args.subtitle_format or get_json("subtitle_format", "srt"),
        audio_format=args.audio_format or get_json("audio_format", "mp3"),
        subtitle_text_path=_opt_path(args.subtitle_text or get_json("subtitle_text_path")),
        subtitle_srt_path=_opt_path(args.subtitle_srt or get_json("subtitle_srt_path")),
        bgm_plan_path=_opt_path(args.bgm_plan or get_json("bgm_plan_path")),
        scene_plan_path=_opt_path(args.scene_plan or get_json("scene_plan_path")),
        timeline_csv_path=_opt_path(args.timeline_csv or get_json("timeline_csv_path")),
        enable_bgm_workflow=not args.no_bgm_workflow,
    )
    return pcfg


def _opt_path(value: Optional[str]) -> Optional[Path]:
    if not value:
        return None
    return Path(value).expanduser()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
