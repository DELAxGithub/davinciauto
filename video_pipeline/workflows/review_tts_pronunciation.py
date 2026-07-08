#!/usr/bin/env python3
"""Create a reviewed Gemini TTS YAML with explicit Japanese readings."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Iterable

import yaml

from video_pipeline.workflows.pronunciation import apply_pronunciation_rules, load_rules, normalize_tts_breaks


def review_tts_yaml(
    yaml_path: Path,
    out_yaml: Path,
    report_csv: Path,
    rules_csv: Path | None = None,
) -> dict[str, int]:
    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    segments = data.get("gemini_tts", {}).get("segments", [])
    rules = load_rules(rules_csv)
    rows: list[dict[str, str]] = []

    for index, segment in enumerate(segments, start=1):
        original = str(segment.get("text", ""))
        reviewed, hits = apply_pronunciation_rules(normalize_tts_breaks(original), rules)
        segment["text"] = reviewed
        segment["display_text"] = original
        for hit in hits:
            rows.append(
                {
                    "segment_index": str(index),
                    "scene": str(segment.get("scene", "")),
                    "surface": hit["surface"],
                    "reading": hit["reading"],
                    "count": hit["count"],
                    "note": hit["note"],
                    "original_text": original,
                    "reviewed_text": reviewed,
                }
            )

    out_yaml.parent.mkdir(parents=True, exist_ok=True)
    report_csv.parent.mkdir(parents=True, exist_ok=True)
    out_yaml.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    with report_csv.open("w", encoding="utf-8", newline="") as handle:
        columns = [
            "segment_index",
            "scene",
            "surface",
            "reading",
            "count",
            "note",
            "original_text",
            "reviewed_text",
        ]
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    return {"segments": len(segments), "hits": len(rows)}


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Review Gemini TTS YAML pronunciation before synthesis.")
    parser.add_argument("--yaml", required=True, type=Path)
    parser.add_argument("--out-yaml", type=Path)
    parser.add_argument("--report-csv", type=Path)
    parser.add_argument("--rules-csv", type=Path)
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    out_yaml = args.out_yaml or args.yaml.with_name(args.yaml.stem + ".reviewed.yaml")
    report_csv = args.report_csv or args.yaml.with_name("pronunciation_review.csv")
    summary = review_tts_yaml(args.yaml, out_yaml, report_csv, args.rules_csv)
    print(
        "Pronunciation review complete: "
        f"segments={summary['segments']}, hits={summary['hits']}, "
        f"yaml={out_yaml}, report={report_csv}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
