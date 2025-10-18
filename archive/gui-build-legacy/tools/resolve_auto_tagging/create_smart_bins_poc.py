#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Proof-of-concept script for creating Smart Bins in DaVinci Resolve.

This script expects to run inside a DaVinci Resolve scripting environment.
It connects to the current project, optionally removes existing Smart Bins
with a given prefix, and then creates new Smart Bins whose rules match clips
by the "Keywords" metadata field.
"""

import argparse
import csv
import os
import sys
from typing import Dict, List, Optional, Sequence, Tuple

# Resolve の Python モジュールをロードできるようにパスを追加
sys.path.append("/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules/")

try:
    import DaVinciResolveScript as dvr
except ImportError:
    print("DaVinci Resolve scripting module は読み込めませんでした。")
    print("DaVinci Resolve のスクリプトコンソール、または python3 を Resolve 付属のものに切り替えて実行してください。")
    sys.exit(1)


def connect_to_resolve():
    """Return (resolve, project_manager, project) tuple or exit on failure."""
    resolve = dvr.scriptapp("Resolve")
    if not resolve:
        print("Resolve API に接続できませんでした。")
        sys.exit(2)

    pm = resolve.GetProjectManager()
    if not pm:
        print("プロジェクトマネージャの取得に失敗しました。")
        sys.exit(3)

    project = pm.GetCurrentProject()
    if not project:
        print("アクティブなプロジェクトが見つかりません。プロジェクトを開いた状態で実行してください。")
        sys.exit(4)

    return resolve, pm, project


def _smart_bin_api(project, media_pool) -> Tuple[object, object]:
    """Return objects that expose Smart Bin APIs (project, media_pool)."""
    return project, media_pool


def _call_first_available(objs: Sequence[object], method: str, *args, **kwargs):
    """Call the first object that exposes 'method'. Raise AttributeError if none."""
    for obj in objs:
        func = getattr(obj, method, None)
        if callable(func):
            return func(*args, **kwargs)
    raise AttributeError(f"None of the Resolve objects expose method '{method}'")


def existing_smart_bins_by_name(project, media_pool) -> Dict[str, object]:
    """Return a mapping of smart bin names to their Resolve objects."""
    try:
        bins = _call_first_available(_smart_bin_api(project, media_pool), "GetSmartBinList") or []
    except AttributeError:
        return {}
    return {b.GetName(): b for b in bins if hasattr(b, "GetName")}


def remove_bins_with_prefix(project, media_pool, prefix: str) -> int:
    """Remove all smart bins whose names start with the prefix."""
    removed = 0
    for name, bin_obj in existing_smart_bins_by_name(project, media_pool).items():
        if name.startswith(prefix):
            try:
                if _call_first_available(
                    _smart_bin_api(project, media_pool), "DeleteSmartBin", bin_obj
                ):
                    removed += 1
            except AttributeError:
                print("⚠️ Smart Bin API が DeleteSmartBin をサポートしていません。既存ビンは維持します。")
                break
            except Exception as exc:  # noqa: BLE001
                print(f"⚠️ Smart Bin '{name}' の削除中にエラー: {exc}")
    return removed


def build_keyword_rule(keyword: str, *, operator: str = "contains") -> Dict[str, object]:
    """Construct the rule payload for the Smart Bin API."""
    return {
        "Operator": "and",
        "Criteria": {
            "Type": "ClipProperty",
            "Property": "Keywords",
            "Operator": operator,
            "Value": keyword,
        },
    }


def _parse_keywords_field(raw: str) -> List[str]:
    if not raw:
        return []
    normalized = raw.replace("；", ";").replace("，", ",")
    keywords: List[str] = []
    for candidate in normalized.split(","):
        token = candidate.strip()
        if token:
            keywords.append(token)
    return keywords


def create_smart_bin(
    project,
    media_pool,
    name: str,
    *,
    all_keywords: Optional[Sequence[str]] = None,
    any_keywords: Optional[Sequence[str]] = None,
    none_keywords: Optional[Sequence[str]] = None,
):
    """Create a Smart Bin with AND/OR keyword rules."""
    all_keywords = list(all_keywords or [])
    any_keywords = list(any_keywords or [])
    none_keywords = list(none_keywords or [])

    if not any([all_keywords, any_keywords, none_keywords]):
        print(f"⚠️ Smart Bin '{name}' に条件が指定されていません。スキップします。")
        return None

    rules: List[Dict[str, object]] = [build_keyword_rule(kw) for kw in all_keywords]

    if any_keywords:
        rules.append(
            {
                "CombineOp": "Or",
                "Rules": [build_keyword_rule(kw) for kw in any_keywords],
            }
        )

    if none_keywords:
        print(
            f"⚠️ Smart Bin '{name}' の NoneOf 条件は現在サポートされていません。無視します。"
        )

    criteria = {
        "CombineOp": "And",
        "Rules": rules,
    }

    try:
        created = _call_first_available(
            _smart_bin_api(project, media_pool), "CreateSmartBin", name, criteria
        )
        if created:
            print(f"✅ Smart Bin を作成しました: {name}")
        else:
            print(f"❌ Smart Bin '{name}' の作成に失敗しました。")
        return created
    except Exception as exc:  # noqa: BLE001
        print(f"❌ Smart Bin '{name}' の作成中にエラー: {exc}")
        return None


def parse_args():
    parser = argparse.ArgumentParser(description="Create Smart Bins based on Keyword metadata.")
    parser.add_argument(
        "--tags",
        nargs="*",
        help="Smart Bin を生成するキーワード。複数指定で 1 つの Bin を作成します。複数 Bin を作る場合は --tags を繰り返し指定。",
    )
    parser.add_argument(
        "--multi",
        action="append",
        default=[],
        help="カンマ区切りで複数キーワードを指定し、1 Bin にまとめるためのショートカット (例: --multi 都市,夜)。",
    )
    parser.add_argument(
        "--csv",
        action="append",
        default=[],
        help="Smart Bin 定義を読み込む CSV パス (Name;AllOf;AnyOf;NoneOf)。複数指定可。",
    )
    parser.add_argument(
        "--prefix",
        default="AI Keywords/",
        help="生成する Smart Bin 名のプレフィックス (デフォルト: 'AI Keywords/').",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="同じプレフィックスの既存 Smart Bin を削除してから生成します。",
    )
    return parser.parse_args()


def collect_bin_specs(args) -> List[Dict[str, object]]:
    """Translate CLI args to a list of Smart Bin spec dictionaries."""
    bins = []

    for csv_path in args.csv:
        resolved = os.path.expanduser(csv_path)
        if not os.path.exists(resolved):
            print(f"⚠️ CSV が見つかりません: {resolved}")
            continue
        with open(resolved, newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle, delimiter=";")
            expected = {"Name", "AllOf", "AnyOf", "NoneOf"}
            if reader.fieldnames is None or not expected.issubset(reader.fieldnames):
                print(
                    f"⚠️ CSV の列が不足しています ({resolved}). 必須列: Name/AllOf/AnyOf/NoneOf"
                )
                continue
            for row in reader:
                name = (row.get("Name") or "").strip()
                if not name:
                    continue
                bins.append(
                    {
                        "name": f"{args.prefix}{name}",
                        "all": _parse_keywords_field(row.get("AllOf", "")),
                        "any": _parse_keywords_field(row.get("AnyOf", "")),
                        "none": _parse_keywords_field(row.get("NoneOf", "")),
                    }
                )

    if args.tags:
        for tag in args.tags:
            bins.append({"name": f"{args.prefix}{tag}", "all": [tag], "any": [], "none": []})

    for raw in args.multi:
        keywords = [kw.strip() for kw in raw.split(",") if kw.strip()]
        if keywords:
            label = ",".join(keywords)
            bins.append({"name": f"{args.prefix}{label}", "all": keywords, "any": [], "none": []})

    if not bins:
        sample_keywords = ["人物", "屋内"]
        bins.append(
            {
                "name": f"{args.prefix}{' & '.join(sample_keywords)}",
                "all": sample_keywords,
                "any": [],
                "none": [],
            }
        )
        print("ヒント: --tags や --multi または --csv を指定して独自の Smart Bin を作成できます。")

    return bins


def main():
    args = parse_args()
    _, _, project = connect_to_resolve()
    media_pool = project.GetMediaPool()
    if not media_pool:
        print("MediaPool を取得できませんでした。")
        sys.exit(5)

    if args.replace and args.prefix:
        removed = remove_bins_with_prefix(project, media_pool, args.prefix)
        if removed:
            print(f"🧹 既存の Smart Bin を {removed} 個削除しました。 (prefix='{args.prefix}')")

    specs = collect_bin_specs(args)
    for spec in specs:
        create_smart_bin(
            project,
            media_pool,
            spec["name"],
            all_keywords=spec.get("all"),
            any_keywords=spec.get("any"),
            none_keywords=spec.get("none"),
        )

    print("--- Smart Bin PoC 完了 ---")


if __name__ == "__main__":
    main()
