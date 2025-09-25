#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Upsert keywords/comments metadata into Resolve clips from a CSV."""

import argparse
import csv
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from dotenv import find_dotenv, load_dotenv

# Resolve scripting modules
sys.path.append("/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules/")
try:
    import DaVinciResolveScript as dvr_script
except ImportError as exc:  # pragma: no cover - runtime guard
    print("エラー: DaVinci Resolveのスクリプトモジュールが見つかりません。")
    raise SystemExit(1) from exc

# Base dir for optional .env lookup
try:
    _BASE_DIR = Path(__file__).resolve().parent
except NameError:  # pragma: no cover - Resolve console
    _BASE_DIR = Path(os.getcwd())

_ENV_PATH = _BASE_DIR / ".env"
if _ENV_PATH.exists():
    load_dotenv(dotenv_path=_ENV_PATH)
else:
    _found = find_dotenv()
    load_dotenv(_found if _found else None)


class _Tee:
    """Duplicate stdout/stderr to an additional file handle."""

    def __init__(self, *streams: Iterable[object]):
        self._streams = streams

    def write(self, data: str) -> None:  # pragma: no cover - IO passthrough
        for stream in self._streams:
            stream.write(data)

    def flush(self) -> None:  # pragma: no cover - IO passthrough
        for stream in self._streams:
            stream.flush()


def _normalize_path(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    expanded = os.path.expanduser(value.strip())
    normalized = os.path.normpath(expanded)
    return os.path.normcase(normalized)


def _split_keywords(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    raw = raw.replace("；", ";").replace("，", ",")
    tokens: List[str] = []
    for fragment in raw.split(","):
        for token in fragment.split(";"):
            cleaned = token.strip()
            if cleaned and cleaned not in tokens:
                tokens.append(cleaned)
    return tokens


def _collect_clips(folder, breadcrumbs: Optional[List[str]] = None):
    breadcrumbs = breadcrumbs or []
    name = folder.GetName() or ""
    current = breadcrumbs + ([name] if name else [])

    for clip in folder.GetClipList() or []:
        file_path = clip.GetClipProperty("File Path") or ""
        yield {
            "clip": clip,
            "file_path": file_path,
            "clip_name": clip.GetName() or "",
            "bin_path": "/".join(current),
        }

    for sub in folder.GetSubFolderList() or []:
        yield from _collect_clips(sub, current)


def _load_csv_rows(csv_path: str) -> List[Dict[str, str]]:
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return [dict(row) for row in reader]


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve metadata importer (keywords/comments upsert).")
    parser.add_argument("--csv", required=True, help="入力CSVパス (UTF-8, header付き)")
    parser.add_argument("--project", dest="project_name", default=None, help="対象Resolveプロジェクト名")
    parser.add_argument("--update-policy", choices=["append_unique", "replace"], default="append_unique", help="更新ポリシー (既存に追記 or 置換)")
    parser.add_argument("--dry-run", action="store_true", help="書き込みを行わず差分のみ表示")
    parser.add_argument("--log", dest="log_path", default=None, help="ログを書き出すファイルパス")
    parser.add_argument("--batch", type=int, default=0, help="進捗ログを出す件数単位 (0で無効)")
    parser.add_argument("--env", dest="env_file", default=None, help="追加で読み込む .env パス")
    args = parser.parse_args()

    csv_path = os.path.expanduser(args.csv)
    if not os.path.isfile(csv_path):
        print(f"エラー: CSVが見つかりません: {csv_path}")
        return 1

    if args.env_file:
        env_path = os.path.expanduser(args.env_file)
        if os.path.exists(env_path):
            load_dotenv(dotenv_path=env_path, override=True)
        else:
            print(f"警告: 指定の .env が見つかりません: {env_path}")

    original_stdout, original_stderr = sys.stdout, sys.stderr
    log_file = None
    try:
        if args.log_path:
            log_path = os.path.expanduser(args.log_path)
            log_dir = os.path.dirname(log_path) or "."
            os.makedirs(log_dir, exist_ok=True)
            log_file = open(log_path, "a", encoding="utf-8")
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_file.write(f"\n--- import_metadata.py started at {timestamp} ---\n")
            log_file.flush()
            sys.stdout = _Tee(original_stdout, log_file)
            sys.stderr = _Tee(original_stderr, log_file)

        resolve = dvr_script.scriptapp("Resolve")
        project_manager = resolve.GetProjectManager()
        if args.project_name:
            project = project_manager.LoadProject(args.project_name)
            if project is None:
                print(f"エラー: 指定プロジェクトが見つかりません: {args.project_name}")
                return 1
        else:
            project = project_manager.GetCurrentProject()
            if project is None:
                print("エラー: 現在のプロジェクトを取得できません。")
                return 1

        media_pool = project.GetMediaPool()
        root_folder = media_pool.GetRootFolder()
        project_name = args.project_name or project.GetName()
        print(f"対象プロジェクト: {project_name}")

        clip_records = list(_collect_clips(root_folder))
        path_index: Dict[str, Dict[str, object]] = {}
        name_index: Dict[str, List[Dict[str, object]]] = defaultdict(list)

        for record in clip_records:
            file_key = _normalize_path(record["file_path"])
            if file_key:
                path_index[file_key] = record
            clip_name = (record["clip_name"] or "").strip().lower()
            if clip_name:
                name_index[clip_name].append(record)

        rows = _load_csv_rows(csv_path)
        if not rows:
            print("警告: CSVにデータがありません。")
            return 0

        stats = {
            "rows": 0,
            "matched": 0,
            "updated": 0,
            "replaced": 0,
            "unchanged": 0,
            "skipped_missing_key": 0,
            "skipped_not_found": 0,
            "errors": 0,
        }

        for row in rows:
            stats["rows"] += 1
            source_file = (row.get("Source File") or "").strip()
            keywords_raw = row.get("Keywords") or ""
            comments_raw = row.get("Comments") or ""
            clip_name_hint = (row.get("Clip Name") or "").strip()
            bin_hint = (row.get("Bin Path") or "").strip()

            clip_record = None
            matched_by = None

            file_key = _normalize_path(source_file)
            if file_key and file_key in path_index:
                clip_record = path_index[file_key]
                matched_by = "path"
            elif clip_name_hint:
                candidates = name_index.get(clip_name_hint.lower(), [])
                if len(candidates) == 1:
                    clip_record = candidates[0]
                    matched_by = "name"
                elif len(candidates) > 1 and bin_hint:
                    bin_hint_norm = "/".join(part for part in bin_hint.split("/") if part)
                    for candidate in candidates:
                        if candidate["bin_path"].endswith(bin_hint_norm):
                            clip_record = candidate
                            matched_by = "name+bin"
                            break

            if clip_record is None:
                stats["skipped_not_found"] += 1
                print(f"⚠️ クリップが見つかりません: Source File='{source_file}' Clip Name='{clip_name_hint}' Bin='{bin_hint}'")
                continue

            if not keywords_raw and not comments_raw:
                stats["skipped_missing_key"] += 1
                print(f"⚠️ キーワード/コメントが空のためスキップ: Source File='{source_file}'")
                continue

            clip = clip_record["clip"]
            stats["matched"] += 1

            incoming_keywords = _split_keywords(keywords_raw)
            incoming_comment = comments_raw.strip()

            existing_keywords_raw = clip.GetMetadata("Keywords") or clip.GetClipProperty("Keywords") or ""
            existing_keywords = _split_keywords(existing_keywords_raw if isinstance(existing_keywords_raw, str) else ";".join(existing_keywords_raw or []))
            existing_comment = (clip.GetMetadata("Comments") or clip.GetClipProperty("Comments") or "").strip()

            if args.update_policy == "append_unique":
                merged = sorted(set(existing_keywords) | set(incoming_keywords))
                new_comment = existing_comment
                if incoming_comment:
                    new_comment = incoming_comment
                keywords_changed = set(merged) != set(existing_keywords)
            else:  # replace
                merged = incoming_keywords
                new_comment = incoming_comment
                keywords_changed = merged != existing_keywords

            comment_changed = new_comment != existing_comment

            if not keywords_changed and not comment_changed:
                stats["unchanged"] += 1
                continue

            serialized_keywords = "; ".join(merged)
            if args.update_policy == "replace" and keywords_changed:
                stats["replaced"] += 1

            if args.dry_run:
                print(f"[DRY-RUN] {clip_record['clip_name']} ({matched_by}) -> keywords={serialized_keywords} comments='{new_comment}'")
                stats["updated"] += 1
                continue

            success = True
            if keywords_changed:
                success = bool(clip.SetMetadata("Keywords", serialized_keywords)) and success
            if comment_changed:
                success = bool(clip.SetMetadata("Comments", new_comment)) and success

            if success:
                stats["updated"] += 1
            else:
                stats["errors"] += 1
                print(f"❌ メタデータ更新に失敗しました: {clip_record['clip_name']}")

            if args.batch and args.batch > 0 and stats["matched"] % args.batch == 0:
                print(f"... {stats['matched']} 件処理 (更新 {stats['updated']} / 置換 {stats['replaced']} / 未変更 {stats['unchanged']}) ...")

        print("\n--- import_metadata.py summary ---")
        print(
            f"総行数={stats['rows']} / マッチ={stats['matched']} / 更新={stats['updated']} / 置換={stats['replaced']} / "
            f"未変更={stats['unchanged']} / 未指定スキップ={stats['skipped_missing_key']} / 未発見={stats['skipped_not_found']} / エラー={stats['errors']}"
        )

        if log_file:
            log_file.write("--- import_metadata.py finished ---\n")

        return 0 if stats["errors"] == 0 else 1
    finally:
        if log_file:
            log_file.flush()
            log_file.close()
        sys.stdout = original_stdout
        sys.stderr = original_stderr


if __name__ == "__main__":
    sys.exit(main())
