"""Utility to generate the structured script CSV for Orion Episode 7."""
from __future__ import annotations

import csv
from pathlib import Path


def create_orion_ep7_script() -> Path:
    """Create the initial script CSV for Orion Ep7 (first 10 segments)."""

    script_data = [
        {
            "no": 1,
            "character": "ナレーター",
            "text": "会議の前に、なぜか結論が決まっている——そんな経験はありませんか",
            "scene": "アバン",
            "timecode_start": "00:00:00",
            "timecode_end": "00:00:05",
        },
        {
            "no": 2,
            "character": "ナレーター",
            "text": "非効率で不透明。それとも和を保つ知恵。ようこそ、オリオンの会議室へ",
            "scene": "アバン",
            "timecode_start": "00:00:05",
            "timecode_end": "00:00:10",
        },
        {
            "no": 3,
            "character": "ナレーター",
            "text": "今夜のテーマは「根回しという日本の叡智」",
            "scene": "アバン",
            "timecode_start": "00:00:10",
            "timecode_end": "00:00:15",
        },
        {
            "no": 4,
            "character": "ナレーター",
            "text": "古今東西の叡智を星座のように結び、現代の悩みに新しい視座を見つける8分間",
            "scene": "アバン",
            "timecode_start": "00:00:15",
            "timecode_end": "00:00:20",
        },
        {
            "no": 5,
            "character": "ナレーター",
            "text": "今夜の星々——ルネサンス期の政治思想家が説いた「権謀術数の現実主義」",
            "scene": "アバン",
            "timecode_start": "00:00:20",
            "timecode_end": "00:00:25",
        },
        {
            "no": 6,
            "character": "ナレーター",
            "text": "古代中国の兵法家による「戦わずして勝つ戦略」",
            "scene": "アバン",
            "timecode_start": "00:00:25",
            "timecode_end": "00:00:30",
        },
        {
            "no": 7,
            "character": "ナレーター",
            "text": "現代ドイツの哲学者が追求した「理想的対話の条件」",
            "scene": "アバン",
            "timecode_start": "00:00:30",
            "timecode_end": "00:00:35",
        },
        {
            "no": 8,
            "character": "ナレーター",
            "text": "そして戦国時代の茶人が体現した「一期一会の政治学」が",
            "scene": "アバン",
            "timecode_start": "00:00:35",
            "timecode_end": "00:00:40",
        },
        {
            "no": 9,
            "character": "ナレーター",
            "text": "理想と現実の狭間で生きる処世術の物語を紡ぎ始めます",
            "scene": "アバン",
            "timecode_start": "00:00:40",
            "timecode_end": "00:00:45",
        },
        {
            "no": 10,
            "character": "ナレーター",
            "text": "金曜日の夕方、廊下での立ち話。課長「来週の会議の件だけど",
            "scene": "日常",
            "timecode_start": "00:01:00",
            "timecode_end": "00:01:05",
            "note": "シーン転換後の最初のセリフ",
        },
    ]

    output_path = Path("projects/OrionEp7/inputs/orion_ep7_script.csv")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = ["no", "character", "text", "scene", "timecode_start", "timecode_end", "note"]
    with output_path.open("w", encoding="utf-8-sig", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in script_data:
            writer.writerow(row)

    print(f"\u2713 Created: {output_path}")
    print(f"\u2713 Total segments: {len(script_data)}")

    return output_path


if __name__ == "__main__":
    create_orion_ep7_script()
