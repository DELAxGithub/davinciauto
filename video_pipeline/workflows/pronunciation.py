"""Japanese pronunciation helpers for narrated VTR TTS prompts."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path


SUB_RE = re.compile(r"<sub\s+alias=['\"][^'\"]+['\"]>.*?</sub>")


@dataclass(frozen=True)
class PronunciationRule:
    surface: str
    reading: str
    note: str


DEFAULT_RULES: tuple[PronunciationRule, ...] = (
    PronunciationRule("雲上書斎", "うんじょうしょさい", "Series title"),
    PronunciationRule("十分", "じゅっぷん", "Duration, not sufficient"),
    PronunciationRule("一万メートル", "いちまんメートル", "Altitude"),
    PronunciationRule("宙づり", "ちゅうづり", "Suspended time"),
    PronunciationRule("時刻表", "じこくひょう", "Railway timetable"),
    PronunciationRule("一刻", "いっとき", "Edo-period temporal unit"),
    PronunciationRule("十九世紀", "じゅうきゅうせいき", "Century"),
    PronunciationRule("衝突事故", "しょうとつじこ", "Railway accident"),
    PronunciationRule("史上", "しじょう", "Historical phrasing"),
    PronunciationRule("一八八四年", "せんはっぴゃくはちじゅうよねん", "1884"),
    PronunciationRule("ワシントン", "ワシントン", "Washington"),
    PronunciationRule("グリニッジ", "グリニッジ", "Greenwich"),
    PronunciationRule("明石", "あかし", "Japan standard-time meridian"),
    PronunciationRule("明治二十一年", "めいじにじゅういちねん", "1888"),
    PronunciationRule("標準時", "ひょうじゅんじ", "Standard time"),
    PronunciationRule("摂理", "せつり", "Providence/principle"),
    PronunciationRule("継ぎ目", "つぎめ", "Boundary seam"),
    PronunciationRule("今日の一冊", "きょうのいっさつ", "Closing fixed phrase"),
)


def load_rules(path: Path | None = None) -> list[PronunciationRule]:
    rules = list(DEFAULT_RULES)
    if not path:
        return rules
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            surface = (row.get("surface") or "").strip()
            reading = (row.get("reading") or "").strip()
            if not surface or not reading:
                continue
            rules.append(PronunciationRule(surface, reading, (row.get("note") or "").strip()))
    return rules


def _replace_outside_sub(text: str, surface: str, reading: str) -> tuple[str, int]:
    count = 0
    parts: list[str] = []
    cursor = 0
    for match in SUB_RE.finditer(text):
        before = text[cursor:match.start()]
        replaced, hits = _replace_plain(before, surface, reading)
        parts.append(replaced)
        parts.append(match.group(0))
        count += hits
        cursor = match.end()
    replaced, hits = _replace_plain(text[cursor:], surface, reading)
    parts.append(replaced)
    count += hits
    return "".join(parts), count


def _replace_plain(text: str, surface: str, reading: str) -> tuple[str, int]:
    replacement = f"<sub alias='{reading}'>{surface}</sub>"
    return text.replace(surface, replacement), text.count(surface)


def apply_pronunciation_rules(
    text: str,
    rules: list[PronunciationRule],
) -> tuple[str, list[dict[str, str]]]:
    reviewed = text
    hits: list[dict[str, str]] = []
    for rule in sorted(rules, key=lambda item: len(item.surface), reverse=True):
        reviewed, count = _replace_outside_sub(reviewed, rule.surface, rule.reading)
        if count:
            hits.append(
                {
                    "surface": rule.surface,
                    "reading": rule.reading,
                    "count": str(count),
                    "note": rule.note,
                }
            )
    return reviewed, hits


def normalize_tts_breaks(text: str) -> str:
    """Normalize script-only pause notation before pronunciation aliases."""
    return text.replace("十分、、、", "十分<break time='1200ms'/>")
