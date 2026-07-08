#!/usr/bin/env python3
"""Transcribe split Platto recorder files and export the standard rough-edit CSV.

The input manifest groups recorder parts by speaker.  The script calculates a
global offset for each part, transcribes every source file, and writes the same
5-column CSV used by the existing Platto Google Sheet uploader.
"""

from __future__ import annotations

import argparse
import array
import csv
import json
import math
import subprocess
import sys
import wave
from pathlib import Path
from typing import Any
from difflib import SequenceMatcher


DEFAULT_MODEL = "mlx-community/whisper-large-v3-turbo"
CSV_HEADER = ["Speaker Name", "イン点", "アウト点", "文字起こし", "色選択"]


def run(cmd: list[str]) -> str:
    completed = subprocess.run(cmd, check=True, text=True, capture_output=True)
    return completed.stdout.strip()


def ffprobe_duration(path: Path) -> float:
    out = run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ]
    )
    return float(out)


def decode_wav(src: Path, dst: Path) -> None:
    if dst.exists() and dst.stat().st_size > 0:
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(src),
            "-ac",
            "1",
            "-ar",
            "16000",
            str(dst),
        ],
        check=True,
    )


def mix_wavs(srcs: list[Path], dst: Path) -> None:
    if dst.exists() and dst.stat().st_size > 0:
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]
    for src in srcs:
        cmd.extend(["-i", str(src)])
    inputs = "".join(f"[{index}:a]" for index in range(len(srcs)))
    filter_complex = (
        f"{inputs}amix=inputs={len(srcs)}:duration=longest:normalize=1,"
        "aresample=16000,aformat=channel_layouts=mono[out]"
    )
    cmd.extend(["-filter_complex", filter_complex, "-map", "[out]", str(dst)])
    subprocess.run(cmd, check=True)


def seconds_to_tc(seconds: float, fps: float) -> str:
    frame = int(round(seconds * fps))
    frames_per_hour = int(round(fps * 60 * 60))
    frames_per_minute = int(round(fps * 60))
    hours, rem = divmod(frame, frames_per_hour)
    minutes, rem = divmod(rem, frames_per_minute)
    secs, frames = divmod(rem, int(round(fps)))
    return f"{hours:02d}:{minutes:02d}:{secs:02d}:{frames:02d}"


def clean_text(text: str) -> str:
    text = " ".join((text or "").replace("\n", " ").split()).strip()
    if not text:
        return text

    japanese_chars = (
        "ぁ-んァ-ン一-龯々〆〤"
        "０-９Ａ-Ｚａ-ｚ"
        "、。！？・「」『』（）【】"
    )
    # Whisper sometimes inserts spaces between Japanese characters.  Remove
    # only those spaces while keeping useful spaces around ASCII words/numbers.
    import re

    pattern = rf"(?<=[{japanese_chars}])\s+(?=[{japanese_chars}])"
    previous = None
    while previous != text:
        previous = text
        text = re.sub(pattern, "", text)
    return text


def comparable_text(text: str) -> str:
    drop_chars = " \t\r\n、。,.!！?？「」『』（）()…ー〜-"
    return "".join(char for char in text if char not in drop_chars)


def is_noise_text(text: str) -> bool:
    compact = text.replace(" ", "").replace("　", "")
    if not compact:
        return True
    common_hallucinations = [
        "ご視聴ありがとうございました",
        "ご清聴ありがとうございました",
        "字幕作成者",
    ]
    if any(phrase in compact for phrase in common_hallucinations):
        return True
    if len(compact) >= 20:
        unique_chars = set(compact)
        if len(unique_chars) <= 3:
            return True
        most_common = max(compact.count(char) for char in unique_chars)
        if most_common / len(compact) >= 0.85:
            return True
    return False


class WavRmsCache:
    def __init__(self) -> None:
        self._cache: dict[Path, tuple[array.array[int], int]] = {}

    def load(self, path: Path) -> tuple[array.array[int], int]:
        if path not in self._cache:
            with wave.open(str(path), "rb") as wav:
                samples = array.array("h")
                samples.frombytes(wav.readframes(wav.getnframes()))
                self._cache[path] = (samples, wav.getframerate())
        return self._cache[path]

    def rms(self, path: Path, start: float, end: float) -> float:
        samples, sample_rate = self.load(path)
        first = max(0, int(start * sample_rate))
        last = min(len(samples), int(end * sample_rate))
        if last <= first:
            return 0.0
        window = samples[first:last]
        step = max(1, len(window) // 16000)
        total = 0
        count = 0
        for value in window[::step]:
            total += value * value
            count += 1
        return math.sqrt(total / max(count, 1))


def load_or_transcribe(wav_path: Path, json_path: Path, model: str, language: str) -> dict[str, Any]:
    if json_path.exists() and json_path.stat().st_size > 0:
        return json.loads(json_path.read_text(encoding="utf-8"))

    import mlx_whisper

    json_path.parent.mkdir(parents=True, exist_ok=True)
    result = mlx_whisper.transcribe(
        str(wav_path),
        path_or_hf_repo=model,
        language=language,
        word_timestamps=False,
    )
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def get_part_durations(manifest: dict[str, Any]) -> dict[str, list[float]]:
    part_durations: dict[str, list[float]] = {}
    for speaker in manifest["speakers"]:
        for part in speaker["parts"]:
            label = part["part"]
            part_durations.setdefault(label, []).append(ffprobe_duration(Path(part["path"])))
    return part_durations


def build_part_offsets(manifest: dict[str, Any]) -> dict[str, float]:
    part_durations = get_part_durations(manifest)

    offsets: dict[str, float] = {}
    elapsed = 0.0
    for label in sorted(part_durations):
        offsets[label] = elapsed
        # Different lav tracks from the same recorder part should be the same
        # length.  Use the longest value so the next part never overlaps.
        elapsed += max(part_durations[label])
    return offsets


def parts_by_label(manifest: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for speaker in manifest["speakers"]:
        for part in speaker["parts"]:
            grouped.setdefault(part["part"], []).append(
                {
                    "speaker": speaker["speaker"],
                    "track": speaker.get("track"),
                    "part": part["part"],
                    "path": part["path"],
                }
            )
    return grouped


def annotate_levels(rows: list[dict[str, Any]], manifest: dict[str, Any], out_dir: Path) -> None:
    speakers = [speaker["speaker"] for speaker in manifest["speakers"]]
    if len(speakers) != 2:
        return
    other_speaker = {speakers[0]: speakers[1], speakers[1]: speakers[0]}
    offsets = build_part_offsets(manifest)
    rms_cache = WavRmsCache()

    for row in rows:
        part = row["part"]
        speaker = row["speaker"]
        local_start = float(row["start"]) - offsets[part]
        local_end = float(row["end"]) - offsets[part]
        own_wav = out_dir / "audio_16k" / f"{part}_{speaker.replace('/', '_')}.wav"
        other_wav = out_dir / "audio_16k" / f"{part}_{other_speaker[speaker].replace('/', '_')}.wav"
        own_rms = rms_cache.rms(own_wav, local_start, local_end)
        other_rms = rms_cache.rms(other_wav, local_start, local_end)
        row["own_rms"] = own_rms
        row["other_rms"] = other_rms
        row["mic_dominance"] = own_rms / (other_rms + 1e-6)


def is_duplicate_pair(a: dict[str, Any], b: dict[str, Any]) -> bool:
    if a["speaker"] == b["speaker"]:
        return False
    overlap = max(0.0, min(float(a["end"]), float(b["end"])) - max(float(a["start"]), float(b["start"])))
    if overlap <= 0:
        return False
    shorter = min(float(a["end"]) - float(a["start"]), float(b["end"]) - float(b["start"]))
    if shorter <= 0 or overlap / shorter < 0.25:
        return False

    text_a = comparable_text(a["text"])
    text_b = comparable_text(b["text"])
    if min(len(text_a), len(text_b)) < 4:
        return False
    similarity = SequenceMatcher(None, text_a, text_b).ratio()
    return similarity >= 0.72 or text_a in text_b or text_b in text_a


def pick_duplicate_winner(
    a: dict[str, Any], b: dict[str, Any], prefer_speaker: str | None = None
) -> dict[str, Any]:
    if prefer_speaker:
        if a["speaker"] == prefer_speaker and b["speaker"] != prefer_speaker:
            return a
        if b["speaker"] == prefer_speaker and a["speaker"] != prefer_speaker:
            return b

    dominance_a = float(a.get("mic_dominance", 1.0))
    dominance_b = float(b.get("mic_dominance", 1.0))
    if max(dominance_a, dominance_b) / max(min(dominance_a, dominance_b), 1e-6) >= 1.15:
        return a if dominance_a > dominance_b else b

    rms_a = float(a.get("own_rms", 0.0))
    rms_b = float(b.get("own_rms", 0.0))
    if max(rms_a, rms_b) / max(min(rms_a, rms_b), 1e-6) >= 1.10:
        return a if rms_a > rms_b else b

    return a if len(a["text"]) >= len(b["text"]) else b


def overlap_duration(a: dict[str, Any], b: dict[str, Any]) -> float:
    return max(0.0, min(float(a["end"]), float(b["end"])) - max(float(a["start"]), float(b["start"])))


def union_overlap_duration(a: dict[str, Any], others: list[dict[str, Any]]) -> float:
    spans = []
    for other in others:
        start = max(float(a["start"]), float(other["start"]))
        end = min(float(a["end"]), float(other["end"]))
        if end > start:
            spans.append((start, end))
    spans.sort()

    merged: list[list[float]] = []
    for start, end in spans:
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    return sum(end - start for start, end in merged)


def find_composite_duplicate_indices(rows: list[dict[str, Any]], prefer_speaker: str | None = None) -> set[int]:
    """Find one long row duplicated by several rows on the other speaker mic."""
    duplicates: set[int] = set()
    for index, row in enumerate(rows):
        duration = float(row["end"]) - float(row["start"])
        if duration < 4:
            continue
        if prefer_speaker and row["speaker"] == prefer_speaker:
            continue

        overlapping = [
            other
            for other in rows
            if other["speaker"] != row["speaker"] and overlap_duration(row, other) > 0.2
        ]
        if prefer_speaker:
            overlapping = [other for other in overlapping if other["speaker"] == prefer_speaker]
        if len(overlapping) < 2:
            continue

        source_text = comparable_text(row["text"])
        combined_text = comparable_text(
            "".join(other["text"] for other in sorted(overlapping, key=lambda item: float(item["start"])))
        )
        if len(source_text) < 12 or len(combined_text) < 12:
            continue

        similarity = SequenceMatcher(None, source_text, combined_text).ratio()
        coverage = union_overlap_duration(row, overlapping) / duration
        if similarity >= 0.52 and coverage >= 0.45:
            duplicates.add(index)
    return duplicates


def dedupe_cross_talk(
    rows: list[dict[str, Any]], prefer_speaker: str | None = None
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    dropped: dict[int, str] = {
        index: "cross_talk_composite_duplicate"
        for index in find_composite_duplicate_indices(rows, prefer_speaker=prefer_speaker)
    }
    for i, row in enumerate(rows):
        if i in dropped:
            continue
        for j in range(i + 1, min(i + 24, len(rows))):
            if j in dropped:
                continue
            candidate = rows[j]
            if float(candidate["start"]) - float(row["end"]) > 12:
                break
            if not is_duplicate_pair(row, candidate):
                continue
            winner = pick_duplicate_winner(row, candidate, prefer_speaker=prefer_speaker)
            loser_index = j if winner is row else i
            dropped[loser_index] = "cross_talk_duplicate"
            if loser_index == i:
                break

    kept_rows = [row for index, row in enumerate(rows) if index not in dropped]
    dropped_rows = []
    for index, reason in dropped.items():
        row = dict(rows[index])
        row["drop_reason"] = reason
        dropped_rows.append(row)
    return kept_rows, sorted(dropped_rows, key=lambda row: (row["start"], row["end"], row["speaker"]))


def transcribe_mixed_dialogue(
    manifest: dict[str, Any], out_dir: Path, model: str, language: str
) -> list[dict[str, Any]]:
    fps = float(manifest.get("fps", 24))
    offsets = build_part_offsets(manifest)
    grouped = parts_by_label(manifest)
    rms_cache = WavRmsCache()
    rows: list[dict[str, Any]] = []
    manifest_report = {
        "episode": manifest.get("episode"),
        "timeline": manifest.get("timeline"),
        "fps": fps,
        "transcription_mode": "mixed_dialogue",
        "part_offsets_seconds": offsets,
        "sources": [],
    }

    for part_label in sorted(grouped):
        entries = grouped[part_label]
        decoded_by_speaker: dict[str, Path] = {}
        durations = []
        for entry in entries:
            src = Path(entry["path"])
            duration = ffprobe_duration(src)
            durations.append(duration)
            safe_speaker = entry["speaker"].replace("/", "_")
            wav_16k = out_dir / "audio_16k" / f"{part_label}_{safe_speaker}.wav"
            decode_wav(src, wav_16k)
            decoded_by_speaker[entry["speaker"]] = wav_16k
            manifest_report["sources"].append(
                {
                    "speaker": entry["speaker"],
                    "track": entry.get("track"),
                    "part": part_label,
                    "source": str(src),
                    "duration_seconds": duration,
                    "global_offset_seconds": offsets[part_label],
                    "decoded_wav": str(wav_16k),
                }
            )

        mix_path = out_dir / "audio_16k" / f"{part_label}_dialogue_mix.wav"
        mix_wavs(list(decoded_by_speaker.values()), mix_path)
        result_json = out_dir / "whisper_json" / f"{part_label}_dialogue_mix.json"
        print(f"transcribing mixed dialogue part {part_label}: {mix_path.name}", flush=True)
        result = load_or_transcribe(mix_path, result_json, model=model, language=language)

        part_duration = max(durations) if durations else 0.0
        for index, seg in enumerate(result.get("segments", [])):
            text = clean_text(seg.get("text", ""))
            if is_noise_text(text):
                continue
            local_start = float(seg["start"])
            local_end = min(float(seg["end"]), part_duration)
            if local_start >= part_duration:
                continue

            levels = {
                speaker: rms_cache.rms(path, local_start, local_end)
                for speaker, path in decoded_by_speaker.items()
            }
            speaker = max(levels, key=levels.get)
            start = offsets[part_label] + local_start
            end = offsets[part_label] + local_end
            rows.append(
                {
                    "speaker": speaker,
                    "start": start,
                    "end": end,
                    "text": text,
                    "part": part_label,
                    "segment_index": index,
                    "source": f"mixed:{mix_path}",
                    "in_tc": seconds_to_tc(start, fps),
                    "out_tc": seconds_to_tc(end, fps),
                    "own_rms": levels[speaker],
                    "other_rms": max((value for name, value in levels.items() if name != speaker), default=0.0),
                    "mic_dominance": levels[speaker]
                    / (max((value for name, value in levels.items() if name != speaker), default=0.0) + 1e-6),
                }
            )

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "split_audio_manifest.resolved.json").write_text(
        json.dumps(manifest_report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    dropped_path = out_dir / f"{manifest.get('episode', 'episode')}_cross_talk_dropped.csv"
    with dropped_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["note"])
        writer.writerow(["mixed_dialogue mode: no cross-talk dedupe applied"])
    return sorted(rows, key=lambda row: (row["start"], row["end"], row["speaker"]))


def transcribe_manifest(manifest: dict[str, Any], out_dir: Path, model: str, language: str) -> list[dict[str, Any]]:
    if manifest.get("transcription_mode") == "mixed_dialogue":
        return transcribe_mixed_dialogue(manifest, out_dir, model=model, language=language)

    fps = float(manifest.get("fps", 24))
    offsets = build_part_offsets(manifest)
    rows: list[dict[str, Any]] = []
    manifest_report = {
        "episode": manifest.get("episode"),
        "timeline": manifest.get("timeline"),
        "fps": fps,
        "part_offsets_seconds": offsets,
        "sources": [],
    }

    for speaker in manifest["speakers"]:
        speaker_name = speaker["speaker"]
        for part in speaker["parts"]:
            part_label = part["part"]
            src = Path(part["path"])
            safe_speaker = speaker_name.replace("/", "_")
            wav_16k = out_dir / "audio_16k" / f"{part_label}_{safe_speaker}.wav"
            result_json = out_dir / "whisper_json" / f"{part_label}_{safe_speaker}.json"

            duration = ffprobe_duration(src)
            decode_wav(src, wav_16k)
            print(f"transcribing {speaker_name} part {part_label}: {src.name}", flush=True)
            result = load_or_transcribe(wav_16k, result_json, model=model, language=language)

            manifest_report["sources"].append(
                {
                    "speaker": speaker_name,
                    "track": speaker.get("track"),
                    "part": part_label,
                    "source": str(src),
                    "duration_seconds": duration,
                    "global_offset_seconds": offsets[part_label],
                    "transcript_json": str(result_json),
                }
            )

            for index, seg in enumerate(result.get("segments", [])):
                text = clean_text(seg.get("text", ""))
                if is_noise_text(text):
                    continue
                local_start = float(seg["start"])
                local_end = min(float(seg["end"]), duration)
                if local_start >= duration:
                    continue
                start = offsets[part_label] + local_start
                end = offsets[part_label] + local_end
                if end <= start:
                    end = start + 0.1
                rows.append(
                    {
                        "speaker": speaker_name,
                        "start": start,
                        "end": end,
                        "text": text,
                        "part": part_label,
                        "segment_index": index,
                        "source": str(src),
                        "in_tc": seconds_to_tc(start, fps),
                        "out_tc": seconds_to_tc(end, fps),
                    }
                )

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "split_audio_manifest.resolved.json").write_text(
        json.dumps(manifest_report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    rows = sorted(rows, key=lambda row: (row["start"], row["end"], row["speaker"]))
    annotate_levels(rows, manifest, out_dir)
    kept_rows, dropped_rows = dedupe_cross_talk(
        rows, prefer_speaker=manifest.get("dedupe_prefer_speaker")
    )
    if dropped_rows:
        dropped_path = out_dir / f"{manifest.get('episode', 'episode')}_cross_talk_dropped.csv"
        with dropped_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "speaker",
                    "in_tc",
                    "out_tc",
                    "start",
                    "end",
                    "text",
                    "part",
                    "segment_index",
                    "own_rms",
                    "other_rms",
                    "mic_dominance",
                    "drop_reason",
                    "source",
                ],
            )
            writer.writeheader()
            writer.writerows(dropped_rows)
    return kept_rows


def write_csvs(rows: list[dict[str, Any]], out_dir: Path, episode: str) -> None:
    merged = out_dir / f"{episode}_whisper_merged.csv"
    with merged.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADER)
        for row in rows:
            writer.writerow([row["speaker"], row["in_tc"], row["out_tc"], row["text"], ""])

    debug = out_dir / f"{episode}_whisper_merged_with_source.csv"
    with debug.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "speaker",
                "in_tc",
                "out_tc",
                "start",
                "end",
                "text",
                "part",
                "segment_index",
                "own_rms",
                "other_rms",
                "mic_dominance",
                "source",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    by_speaker: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_speaker.setdefault(row["speaker"], []).append(row)
    for speaker, speaker_rows in by_speaker.items():
        path = out_dir / f"{speaker}_whisper.csv"
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADER)
            for row in speaker_rows:
                writer.writerow([row["speaker"], row["in_tc"], row["out_tc"], row["text"], ""])


def write_report(rows: list[dict[str, Any]], out_dir: Path, episode: str) -> None:
    if rows:
        duration = max(row["end"] for row in rows)
    else:
        duration = 0.0
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["speaker"]] = counts.get(row["speaker"], 0) + 1

    lines = [
        f"# Platto EP{episode} Whisper Export",
        "",
        f"- Total transcript rows: {len(rows)}",
        f"- Timeline duration estimate: {seconds_to_tc(duration, 24)}",
        "- Speaker rows:",
    ]
    for speaker, count in sorted(counts.items()):
        lines.append(f"  - {speaker}: {count}")
    lines.extend(
        [
            "",
            "## Split-file handling",
            "",
            "Recorder parts are kept as separate source files, but each part is assigned a global offset.",
            "The uploaded CSV therefore uses one continuous timeline timecode, matching the Resolve timeline.",
        ]
    )
    (out_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--language", default="ja")
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    rows = transcribe_manifest(manifest, args.out_dir, model=args.model, language=args.language)
    episode = str(manifest.get("episode", "episode"))
    write_csvs(rows, args.out_dir, episode)
    write_report(rows, args.out_dir, episode)
    print(f"wrote {len(rows)} rows to {args.out_dir / (episode + '_whisper_merged.csv')}")


if __name__ == "__main__":
    main()
