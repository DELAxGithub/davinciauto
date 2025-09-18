#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Proof-of-concept script for creating Smart Bins in DaVinci Resolve.

This script expects to run inside a DaVinci Resolve scripting environment.
It connects to the current project, optionally removes existing Smart Bins
with a given prefix, and then creates new Smart Bins whose rules match clips
by the "Keywords" metadata field.
"""

import argparse
import sys
from typing import Dict, List, Sequence, Tuple

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
    bins = _call_first_available(_smart_bin_api(project, media_pool), "GetSmartBinList") or []
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
            except Exception as exc:  # noqa: BLE001
                print(f"⚠️ Smart Bin '{name}' の削除中にエラー: {exc}")
    return removed


def build_keyword_rule(keyword: str) -> Dict[str, object]:
    """Construct the rule payload for the Smart Bin API."""
    return {
        "Operator": "and",
        "Criteria": {
            "Type": "ClipProperty",
            "Property": "Keywords",
            "Operator": "contains",
            "Value": keyword,
        },
    }


def create_smart_bin(project, media_pool, name: str, keywords: Sequence[str]):
    """Create a Smart Bin matching clips whose Keywords contain all specified values."""
    if not keywords:
        print(f"⚠️ Smart Bin '{name}' にキーワードが指定されていません。スキップします。")
        return None

    # Smart Bin の検索条件は CombineOp と複数ルールから成る辞書を渡す形式。
    criteria = {
        "CombineOp": "And",
        "Rules": [build_keyword_rule(kw) for kw in keywords],
    }

    try:
        created = _call_first_available(
            _smart_bin_api(project, media_pool), "CreateSmartBin", name, criteria
        )
        if created:
            print(f"✅ Smart Bin を作成しました: {name} -> {', '.join(keywords)}")
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
    """Translate CLI args to a list of {'name': str, 'keywords': List[str]} dicts."""
    bins = []

    if args.tags:
        # --tags k1 k2 k3 ... => それぞれ単一キーワードで Smart Bin
        for tag in args.tags:
            bins.append({"name": f"{args.prefix}{tag}", "keywords": [tag]})

    for raw in args.multi:
        keywords = [kw.strip() for kw in raw.split(",") if kw.strip()]
        if keywords:
            label = ",".join(keywords)
            bins.append({"name": f"{args.prefix}{label}", "keywords": keywords})

    if not bins:
        # フォールバックの PoC 例
        sample_keywords = ["人物", "屋内"]
        bins.append({"name": f"{args.prefix}{' & '.join(sample_keywords)}", "keywords": sample_keywords})
        print("ヒント: --tags や --multi を指定して独自の Smart Bin を作成できます。")

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
        create_smart_bin(project, media_pool, spec["name"], spec["keywords"])

    print("--- Smart Bin PoC 完了 ---")


if __name__ == "__main__":
    main()
