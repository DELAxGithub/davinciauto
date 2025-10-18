#!/usr/bin/env python3
"""General-purpose TTS pipeline runner.

This script parses a markdown script, synthesises segment audio using the
shared `OrionTTSGenerator`, and writes out timeline CSV / XML / SRT assets.
It is designed to be driven via CLI arguments so multiple projects can share
the same implementation without leaving per-project logic behind.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import yaml
from xml.dom import minidom
import xml.etree.ElementTree as ET


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent

if str(REPO_ROOT / "experiments") not in sys.path:
    sys.path.append(str(REPO_ROOT / "experiments"))
if str(SCRIPT_DIR) not in sys.path:
    sys.path.append(str(SCRIPT_DIR))

from tts_config_loader import load_merged_tts_config  # type: ignore  # noqa: E402
from orion_tts_generator import OrionTTSGenerator  # type: ignore  # noqa: E402
from srt_merge import align_srt_files, merge_srt_files  # type: ignore  # noqa: E402


@dataclass
class PipelineContext:
    project: str
    project_dir: Path
    inputs_dir: Path
    output_root: Path
    exports_dir: Path
    audio_dir: Path
    script_md: Path
    script_csv: Path
    input_srt: Optional[Path]
    output_srt: Optional[Path]
    merged_srt: Optional[Path]
    final_srt: Optional[Path]
    timeline_csv: Optional[Path]
    timeline_xml: Optional[Path]
    export_xml: Optional[Path]
    sample_name: str
    scene_lead_in_sec: float
    timebase: int
    ntsc: bool
    tts_config_paths: List[Path]
    fps: float = field(init=False)

    def __post_init__(self) -> None:
        self.fps = self.timebase * 1000 / 1001 if self.ntsc else float(self.timebase)


@dataclass
class Segment:
    index: int
    segment_id: str
    raw_speaker: str
    character: str
    role: str
    voice_direction: Optional[str]
    text: str
    raw_text: str
    subtitle_lines: List[str]
    scene: Optional[str]
    lead_in_pause_sec: float = 0.0
    filename: str = ""
    audio_path: Optional[Path] = None
    duration_sec: float = 0.0
    duration_frames: int = 0
    start_frame: int = 0
    end_frame: int = 0
    sample_rate: int = 0
    gemini_voice: Optional[str] = None
    gemini_style_prompt: Optional[str] = None


PAUSE_PATTERN = re.compile(r"\(間([0-9.]+)\)")
PAUSE_TO_PUNCT = {
    "0.4": "、",
    "0.5": "、",
    "0.7": "。",
    "1.0": "。",
    "1": "。",
    "2.0": "。",
    "2": "。",
}

QUESTION_SUFFIXES = (
    "か",
    "かね",
    "かい",
    "かな",
    "かしら",
    "ないか",
    "ませんか",
    "でしょうか",
    "のか",
    "なのか",
    "できるか",
    "ますか",
)


def camel_to_snake(name: str) -> str:
    snake = re.sub("([a-z0-9])([A-Z])", r"\1_\2", name)
    snake = snake.replace("-", "_")
    return snake.lower()


def find_default_file(inputs_dir: Path, candidates: List[str], glob_pattern: str) -> Path:
    for pattern in candidates:
        candidate = inputs_dir / pattern
        if candidate.exists():
            return candidate
    matches = list(inputs_dir.glob(glob_pattern))
    if len(matches) == 1:
        return matches[0]
    if len(matches) == 0:
        raise FileNotFoundError(f"No files matching {glob_pattern} under {inputs_dir}")
    raise FileNotFoundError(
        f"Multiple candidates for {glob_pattern} under {inputs_dir}; specify explicitly."
    )


def discover_tts_configs(inputs_dir: Path) -> List[Path]:
    configs = sorted(inputs_dir.glob("*tts*.yaml"))
    return configs


def ensure_tts_config_env(ctx: PipelineContext) -> None:
    if ctx.tts_config_paths:
        os.environ["TTS_CONFIG_PATHS"] = ",".join(str(p) for p in ctx.tts_config_paths)


def relpath(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def convert_pauses_to_text(raw: str, auto_finalize: bool) -> str:
    if not raw:
        return ""

    def repl(match: re.Match[str]) -> str:
        value = match.group(1)
        return PAUSE_TO_PUNCT.get(value, "")

    text = PAUSE_PATTERN.sub(repl, raw)
    text = text.replace(" ", "").replace("\u3000", "")
    text = re.sub(r"、+", "、", text)
    text = re.sub(r"。。+", "。", text)
    text = text.strip()
    if not text:
        return text

    suffix = ""
    while text and text[-1] in "」』】）":
        suffix = text[-1] + suffix
        text = text[:-1]

    if auto_finalize and text and text[-1] not in "。！？…♪":
        if any(text.endswith(sfx) for sfx in QUESTION_SUFFIXES):
            text += "？"
        else:
            text += "。"

    return (text + suffix).strip()


def normalize_speaker_label(label: str) -> str:
    base = label.strip()
    if "/" in base:
        base = base.split("/", 1)[0]
    base = base.split("（", 1)[0]
    base = base.strip()
    aliases = {
        "若手社員": "若手",
        "若手/若手社員": "若手",
    }
    return aliases.get(base, base)


def parse_script(ctx: PipelineContext) -> List[Segment]:
    text = ctx.script_md.read_text(encoding="utf-8")
    segments: List[Segment] = []
    current_scene: Optional[str] = None
    prev_scene: Optional[str] = None
    index = 1

    dialogue_pattern = re.compile(r"([^：]+)：")

    lines_iter = iter(text.splitlines())
    for raw_line in lines_iter:
        line = raw_line.strip()
        if not line:
            continue
        if re.fullmatch(r"-+", line) or re.fullmatch(r"[ー~〜━‐－─—―]+", line):
            # Skip Markdown or decorative horizontal rules (e.g., --- or ーーーー)
            continue
        if line.startswith("【"):
            bracket_match = re.match(r"^【([^】]+)】\s*(.*)$", line)
            if bracket_match:
                tag, remainder = bracket_match.groups()
                tag = (tag or "").strip()
                remainder = (remainder or "").strip(" 。．.　")
                is_scene_heading = bool(re.search(r"\d", tag)) or "scene" in tag.lower()
                if is_scene_heading:
                    if remainder:
                        current_scene = remainder
                    elif tag:
                        current_scene = tag
            continue
        if line.startswith("#"):
            heading = line.lstrip("#").strip()
            if heading and any(keyword in heading for keyword in ("使用上の注意", "Gemini TTS全編版")):
                # Skip remaining sections such as usage notes / appendix blocks.
                break
            if line.startswith("##"):
                current_scene = heading
            continue
        if line.startswith("```yaml"):
            yaml_lines: List[str] = []
            for block_line in lines_iter:
                if block_line.strip().startswith("```"):
                    break
                yaml_lines.append(block_line)
            yaml_text = "\n".join(yaml_lines)
            yaml_entries = _parse_yaml_entries(yaml_text)
            for entry in yaml_entries:
                if entry.get("scene"):
                    scene_name = entry["scene"].strip()
                    if scene_name:
                        current_scene = scene_name
                speaker_label = entry.get("speaker", "ナレーター")
                speaker_core = speaker_label.split("（", 1)[0].strip()
                base_speaker = normalize_speaker_label(speaker_core or "ナレーター")
                role = "NA" if base_speaker == "ナレーター" else "DL"

                for chunk in entry.get("segments", []):
                    clean_text = convert_pauses_to_text(chunk, auto_finalize=True).strip()
                    if not clean_text:
                        continue

                    lead_in = 0.0
                    if segments and current_scene and current_scene != prev_scene:
                        lead_in = ctx.scene_lead_in_sec

                    subtitle_lines = [ln.strip() for ln in chunk.splitlines() if ln.strip()]
                    segment = Segment(
                        index=index,
                        segment_id=f"No.{index:03d}",
                        raw_speaker=speaker_label,
                        character=base_speaker,
                        role=role,
                        voice_direction=entry.get("voice_direction")
                        or entry.get("gemini_style_prompt"),
                        text=clean_text,
                        raw_text=chunk,
                        subtitle_lines=subtitle_lines or [clean_text],
                        scene=current_scene,
                        lead_in_pause_sec=lead_in,
                        gemini_voice=entry.get("gemini_voice"),
                        gemini_style_prompt=entry.get("gemini_style_prompt"),
                    )
                    segments.append(segment)
                    index += 1
                    prev_scene = current_scene
            continue

        matches = list(dialogue_pattern.finditer(line))
        entries: List[tuple[str, str]] = []
        if matches:
            for i, match in enumerate(matches):
                speaker_label = match.group(1).strip()
                start = match.end()
                end = matches[i + 1].start() if i + 1 < len(matches) else len(line)
                content = line[start:end].strip()
                if content:
                    entries.append((speaker_label, content))
        else:
            entries.append(("ナレーター", line))

        for speaker_label, content in entries:
            speaker_core = speaker_label.split("（", 1)[0].strip()
            base_speaker = normalize_speaker_label(speaker_core or "ナレーター")
            role = "NA" if base_speaker == "ナレーター" else "DL"

            clean_text = convert_pauses_to_text(content, auto_finalize=True).strip()
            if not clean_text:
                continue

            lead_in = 0.0
            if segments and current_scene and current_scene != prev_scene:
                lead_in = ctx.scene_lead_in_sec

            segment = Segment(
                index=index,
                segment_id=f"No.{index:03d}",
                raw_speaker=speaker_label,
                character=base_speaker,
                role=role,
                voice_direction=None,
                text=clean_text,
                raw_text=content,
                subtitle_lines=[clean_text],
                scene=current_scene,
                lead_in_pause_sec=lead_in,
            )
            segments.append(segment)
            index += 1
            prev_scene = current_scene

    return segments


def _parse_yaml_entries(yaml_text: str) -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    if not yaml_text or not yaml_text.strip():
        return entries

    try:
        loaded = yaml.safe_load(yaml_text)
    except yaml.YAMLError:
        return _parse_yaml_entries_fallback(yaml_text)

    if loaded is None:
        return entries

    def handle(node: Any, scene_name: str | None = None) -> None:
        if isinstance(node, dict):
            if isinstance(node.get("scenes"), list):
                for scene in node["scenes"]:
                    if isinstance(scene, dict):
                        handle(scene, scene_name=scene.get("name") or scene_name)
                return

            if isinstance(node.get("segments"), list):
                for segment in node["segments"]:
                    handle(segment, scene_name=scene_name)
                return

            segments: List[str] = []
            text_value = node.get("text")
            if isinstance(text_value, list):
                segments.extend(str(element).strip() for element in text_value if str(element).strip())
            elif isinstance(text_value, str) and text_value.strip():
                raw = text_value.strip("\n")
                for chunk in re.split(r"\n\s*\n", raw):
                    chunk = chunk.strip()
                    if chunk:
                        segments.append(chunk)

            if not segments:
                ssml_value = node.get("ssml")
                if isinstance(ssml_value, str) and ssml_value.strip():
                    segments = [_ssml_to_text(ssml_value)]

            if not segments:
                return

            entry: Dict[str, Any] = {
                "speaker": node.get("speaker", "ナレーター"),
                "segments": segments,
            }

            for key in ("gemini_voice", "voice", "voice_direction", "emotion"):
                value = node.get(key)
                if isinstance(value, str) and value.strip():
                    if key == "voice":
                        entry["gemini_voice"] = value.strip()
                    elif key == "emotion":
                        entry["voice_direction"] = value.strip()
                    else:
                        entry[key] = value.strip()

            style_prompt = node.get("style_prompt") or node.get("gemini_style_prompt")
            if isinstance(style_prompt, str) and style_prompt.strip():
                entry["gemini_style_prompt"] = style_prompt.strip()

            if scene_name:
                entry["scene"] = scene_name

            entries.append(entry)

        elif isinstance(node, list):
            for sub in node:
                handle(sub, scene_name=scene_name)

    handle(loaded)
    return entries


def _parse_yaml_entries_fallback(yaml_text: str) -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    current: Dict[str, Any] | None = None
    pending_lines: List[str] = []
    text_mode = False

    def finalize_text(target: Dict[str, Any]) -> None:
        nonlocal pending_lines
        if not pending_lines:
            return
        joined = "\n".join(pending_lines).strip()
        pending_lines = []
        if not joined:
            return
        for chunk in re.split(r"\n\s*\n", joined):
            chunk = chunk.strip()
            if chunk:
                target.setdefault("segments", []).append(chunk)

    def finalize_entry() -> None:
        nonlocal current, text_mode
        if not current:
            return
        if text_mode:
            finalize_text(current)
        text_mode = False
        if not current.get("segments"):
            current = None
            return
        current.setdefault("speaker", "ナレーター")
        entries.append(current)  # type: ignore[arg-type]
        current = None

    def assign_key_value(target: Dict[str, Any], key: str, value: str) -> None:
        cleaned = value.strip()
        if cleaned and cleaned[0] in {'"', "'"} and cleaned[-1:] == cleaned[0]:
            cleaned = cleaned[1:-1]
        if key == "text":
            target.setdefault("segments", []).append(cleaned.strip())
        else:
            target[key] = cleaned.strip()

    for raw_line in yaml_text.splitlines():
        line = raw_line.rstrip("\n")
        stripped = line.strip()

        if not stripped or stripped.startswith("#"):
            if text_mode and not stripped:
                pending_lines.append("")
            continue

        if stripped.startswith("- "):
            finalize_entry()
            current = {"segments": []}
            pending_lines = []
            text_mode = False
            remainder = stripped[2:].strip()
            if remainder:
                if ":" in remainder:
                    key, value = remainder.split(":", 1)
                    key = key.strip()
                    value = value.strip()
                    if key == "text" and value in {"|", ">", ""}:
                        text_mode = True
                        pending_lines = []
                    elif key == "text":
                        assign_key_value(current, key, value)
                    else:
                        assign_key_value(current, key, value)
            continue

        if current is None:
            continue

        if ":" in stripped and not stripped.startswith(('"', "'")):
            key, value = stripped.split(":", 1)
            key = key.strip()
            value = value.strip()
            if key == "text" and value in {"|", ">", ""}:
                if text_mode:
                    finalize_text(current)
                text_mode = True
                pending_lines = []
            elif key == "text":
                if text_mode:
                    finalize_text(current)
                    text_mode = False
                assign_key_value(current, key, value)
            else:
                if text_mode:
                    finalize_text(current)
                    text_mode = False
                assign_key_value(current, key, value)
        else:
            if text_mode:
                pending_lines.append(stripped)
            else:
                if current.setdefault("segments", []):
                    current["segments"][-1] += " " + stripped
                else:
                    current.setdefault("segments", []).append(stripped)

    finalize_entry()
    return entries


_SSML_TAG_RE = re.compile(r"<[^>]+>")
_SSML_BREAK_RE = re.compile(r"<break[^>]*>", re.IGNORECASE)
_SSML_SUB_RE = re.compile(r"<sub alias=\"([^\"]+)\">(.*?)</sub>", re.IGNORECASE)


def _ssml_to_text(ssml: str) -> str:
    text = ssml
    text = re.sub(r"</?speak>", "", text, flags=re.IGNORECASE)

    def replace_sub(match: re.Match[str]) -> str:
        alias = match.group(1).strip()
        inner = match.group(2).strip()
        if inner and alias:
            return f"{inner}（{alias}）"
        return inner or alias

    text = _SSML_SUB_RE.sub(replace_sub, text)
    text = _SSML_BREAK_RE.sub(" 、", text)
    text = _SSML_TAG_RE.sub("", text)
    text = re.sub(r"\s+", " ", text)
    text = text.replace(" 、", "、").replace(" 。", "。")
    text = re.sub(r"、、+", "、", text)
    text = re.sub(r"。。+", "。", text)
    return text.strip()


def synthesize_segments(ctx: PipelineContext, segments: List[Segment]) -> None:
    ensure_tts_config_env(ctx)
    config_dict = load_merged_tts_config(ctx.project)
    generator = OrionTTSGenerator(config_dict)

    script_texts: Dict[int, str] = {}
    if ctx.script_csv.exists():
        with ctx.script_csv.open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    idx = int(row.get("no", "0"))
                except ValueError:
                    continue
                script_texts[idx] = row.get("text", "").strip()

    ctx.audio_dir.mkdir(parents=True, exist_ok=True)

    prev_scene: Optional[str] = None
    for segment in segments:
        output_name = f"{ctx.sample_name}_{segment.index:03d}.mp3"
        output_path = ctx.audio_dir / output_name

        text = script_texts.get(segment.index) or segment.raw_text or segment.text

        if output_path.exists():
            duration, sample_rate = probe_audio_metadata(output_path)
            segment.filename = output_name
            segment.audio_path = output_path
            segment.duration_sec = duration
            segment.duration_frames = max(1, int(round(duration * ctx.fps)))
            segment.sample_rate = sample_rate
            prev_scene = segment.scene
            print(
                f"[{segment.index:03d}] {segment.segment_id} ({segment.character}) : "
                f"{duration:.2f}s -> {relpath(output_path)} (cached)"
            )
            continue

        success = generator.generate(
            text=text,
            character=segment.character,
            output_path=output_path,
            segment_no=segment.index,
            scene=segment.scene,
            prev_scene=prev_scene,
            gemini_voice=segment.gemini_voice,
            gemini_style_prompt=segment.gemini_style_prompt,
        )

        if not success:
            raise RuntimeError(f"Failed to synthesise segment {segment.index}")

        prev_scene = segment.scene

        segment.filename = output_name
        segment.audio_path = output_path

        duration, sample_rate = probe_audio_metadata(output_path)
        segment.duration_sec = duration
        segment.duration_frames = max(1, int(round(duration * ctx.fps)))
        segment.sample_rate = sample_rate
        print(
            f"[{segment.index:03d}] {segment.segment_id} ({segment.character}) : "
            f"{duration:.2f}s -> {relpath(output_path)}"
        )


def probe_audio_metadata(audio_path: Path) -> tuple[float, int]:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "a:0",
        "-show_entries",
        "stream=sample_rate:format=duration",
        "-of",
        "json",
        str(audio_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)
    try:
        duration = float(data["format"]["duration"])
        sample_rate = int(data["streams"][0]["sample_rate"])
    except (KeyError, ValueError, IndexError, TypeError) as exc:
        raise RuntimeError(f"ffprobe failed to parse metadata for {audio_path}") from exc
    return duration, sample_rate


def assign_timeline_positions(ctx: PipelineContext, segments: List[Segment]) -> None:
    current = 0
    for segment in segments:
        if segment.lead_in_pause_sec:
            current += int(round(segment.lead_in_pause_sec * ctx.fps))
        segment.start_frame = current
        segment.end_frame = current + segment.duration_frames
        current = segment.end_frame


def frames_to_timecode(ctx: PipelineContext, frames: int) -> str:
    seconds_total, frame_part = divmod(frames, ctx.timebase)
    hours, remainder = divmod(seconds_total, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frame_part:02d}"


def frames_to_srt_timestamp(ctx: PipelineContext, frames: int) -> str:
    total_ms = int(round(frames * 1000 / ctx.fps))
    hours = total_ms // 3600000
    minutes = (total_ms % 3600000) // 60000
    seconds = (total_ms % 60000) // 1000
    milliseconds = total_ms % 1000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def write_csv(ctx: PipelineContext, segments: List[Segment]) -> None:
    if ctx.timeline_csv is None:
        return
    ctx.timeline_csv.parent.mkdir(parents=True, exist_ok=True)
    headers = [
        "Speaker Name",
        "イン点",
        "アウト点",
        "文字起こし",
        "色選択",
        "filename",
        "role",
        "character",
        "voice_direction",
        "text",
        "timeline_in",
        "timeline_out",
        "duration_sec",
        "original_in",
        "original_out",
    ]
    with ctx.timeline_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for seg in segments:
            writer.writerow(
                [
                    seg.raw_speaker,
                    frames_to_timecode(ctx, 0),
                    frames_to_timecode(ctx, seg.duration_frames),
                    seg.text,
                    f"SEG_{seg.index:03d}",
                    seg.filename,
                    seg.role,
                    seg.character,
                    seg.voice_direction or "",
                    seg.text,
                    frames_to_timecode(ctx, seg.start_frame),
                    frames_to_timecode(ctx, seg.end_frame),
                    f"{seg.duration_sec:.3f}",
                    "",
                    "",
                ]
            )
    print(f"Wrote timeline CSV: {relpath(ctx.timeline_csv)}")


def build_xml(ctx: PipelineContext, segments: List[Segment]) -> None:
    if ctx.timeline_xml is None and ctx.export_xml is None:
        return

    total_duration = segments[-1].end_frame if segments else 0

    xmeml = ET.Element("xmeml", version="4")
    sequence = ET.SubElement(xmeml, "sequence")
    ET.SubElement(sequence, "uuid").text = f"{ctx.sample_name}_timeline"
    ET.SubElement(sequence, "duration").text = str(total_duration)
    ET.SubElement(sequence, "name").text = f"{ctx.sample_name}_timeline"

    rate = ET.SubElement(sequence, "rate")
    ET.SubElement(rate, "timebase").text = str(ctx.timebase)
    ET.SubElement(rate, "ntsc").text = "TRUE" if ctx.ntsc else "FALSE"

    media = ET.SubElement(sequence, "media")
    video = ET.SubElement(media, "video")
    ET.SubElement(video, "format")
    audio_parent = ET.SubElement(media, "audio")
    track = ET.SubElement(audio_parent, "track")

    clip_counter = 1
    file_counter = 1

    for seg in segments:
        if seg.audio_path is None:
            raise RuntimeError(f"Segment {seg.index} missing audio path.")

        clip = ET.SubElement(track, "clipitem", id=f"clipitem-{clip_counter}")
        clip_counter += 1

        ET.SubElement(clip, "name").text = seg.filename
        ET.SubElement(clip, "enabled").text = "TRUE"
        ET.SubElement(clip, "duration").text = str(seg.duration_frames)

        clip_rate = ET.SubElement(clip, "rate")
        ET.SubElement(clip_rate, "timebase").text = str(ctx.timebase)
        ET.SubElement(clip_rate, "ntsc").text = "TRUE" if ctx.ntsc else "FALSE"

        ET.SubElement(clip, "start").text = str(seg.start_frame)
        ET.SubElement(clip, "end").text = str(seg.end_frame)
        ET.SubElement(clip, "in").text = "0"
        ET.SubElement(clip, "out").text = str(seg.duration_frames)

        file_el = ET.SubElement(clip, "file", id=f"file-{file_counter}")
        file_counter += 1
        ET.SubElement(file_el, "name").text = seg.filename
        ET.SubElement(file_el, "pathurl").text = seg.audio_path.resolve().as_uri()

        sample_rate = seg.sample_rate or 44100
        file_rate = ET.SubElement(file_el, "rate")
        ET.SubElement(file_rate, "timebase").text = str(sample_rate)
        ET.SubElement(file_rate, "ntsc").text = "FALSE"

        file_media = ET.SubElement(file_el, "media")
        audio_meta = ET.SubElement(file_media, "audio")
        ET.SubElement(audio_meta, "channelcount").text = "1"
        sample_chars = ET.SubElement(audio_meta, "samplecharacteristics")
        ET.SubElement(sample_chars, "samplerate").text = str(sample_rate)
        ET.SubElement(sample_chars, "samplesize").text = "16"

        sourcetrack = ET.SubElement(clip, "sourcetrack")
        ET.SubElement(sourcetrack, "mediatype").text = "audio"
        ET.SubElement(sourcetrack, "trackindex").text = "1"

        add_audio_filters(clip, seg.duration_frames)
        ET.SubElement(clip, "comments")

    if ctx.timeline_xml is not None:
        write_pretty_xml(xmeml, ctx.timeline_xml)
        print(f"Wrote FCP7 XML: {relpath(ctx.timeline_xml)}")
    if ctx.export_xml is not None:
        ctx.export_xml.parent.mkdir(parents=True, exist_ok=True)
        write_pretty_xml(xmeml, ctx.export_xml)
        print(f"Wrote FCP7 XML: {relpath(ctx.export_xml)}")


def write_pretty_xml(root: ET.Element, path: Path) -> None:
    xml_bytes = ET.tostring(root, encoding="utf-8")
    parsed = minidom.parseString(xml_bytes)
    pretty_bytes = parsed.toprettyxml(indent="  ", encoding="utf-8")
    path.write_bytes(pretty_bytes)


def add_audio_filters(clip: ET.Element, duration_frames: int) -> None:
    filter_gain = ET.SubElement(clip, "filter")
    ET.SubElement(filter_gain, "enabled").text = "TRUE"
    ET.SubElement(filter_gain, "start").text = "0"
    ET.SubElement(filter_gain, "end").text = str(duration_frames)
    effect_gain = ET.SubElement(filter_gain, "effect")
    ET.SubElement(effect_gain, "name").text = "Audio Levels"
    ET.SubElement(effect_gain, "effectid").text = "audiolevels"
    ET.SubElement(effect_gain, "effecttype").text = "audiolevels"
    ET.SubElement(effect_gain, "mediatype").text = "audio"
    ET.SubElement(effect_gain, "effectcategory").text = "audiolevels"
    param_gain = ET.SubElement(effect_gain, "parameter")
    ET.SubElement(param_gain, "name").text = "Level"
    ET.SubElement(param_gain, "parameterid").text = "level"
    ET.SubElement(param_gain, "value").text = "1"
    ET.SubElement(param_gain, "valuemin").text = "0"
    ET.SubElement(param_gain, "valuemax").text = "3.98109"

    filter_pan = ET.SubElement(clip, "filter")
    ET.SubElement(filter_pan, "enabled").text = "TRUE"
    ET.SubElement(filter_pan, "start").text = "0"
    ET.SubElement(filter_pan, "end").text = str(duration_frames)
    effect_pan = ET.SubElement(filter_pan, "effect")
    ET.SubElement(effect_pan, "name").text = "Audio Pan"
    ET.SubElement(effect_pan, "effectid").text = "audiopan"
    ET.SubElement(effect_pan, "effecttype").text = "audiopan"
    ET.SubElement(effect_pan, "mediatype").text = "audio"
    ET.SubElement(effect_pan, "effectcategory").text = "audiopan"
    param_pan = ET.SubElement(effect_pan, "parameter")
    ET.SubElement(param_pan, "name").text = "Pan"
    ET.SubElement(param_pan, "parameterid").text = "pan"
    ET.SubElement(param_pan, "value").text = "0"
    ET.SubElement(param_pan, "valuemin").text = "-1"
    ET.SubElement(param_pan, "valuemax").text = "1"


def write_srt(ctx: PipelineContext, segments: List[Segment]) -> None:
    if ctx.output_srt is None:
        return
    lines: List[str] = []
    for idx, seg in enumerate(segments, start=1):
        start_ts = frames_to_srt_timestamp(ctx, seg.start_frame)
        end_ts = frames_to_srt_timestamp(ctx, seg.end_frame)
        lines.append(str(idx))
        lines.append(f"{start_ts} --> {end_ts}")
        display_lines = [ln.strip() for ln in seg.subtitle_lines if ln.strip()]
        if not display_lines:
            display_lines = [seg.text.strip()]
        lines.extend(display_lines)
        lines.append("")
    ctx.output_srt.parent.mkdir(parents=True, exist_ok=True)
    ctx.output_srt.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    print(f"Wrote SRT: {relpath(ctx.output_srt)}")


def create_context(args: argparse.Namespace) -> PipelineContext:
    project_dir = REPO_ROOT / "projects" / args.project
    inputs_dir = project_dir / "inputs"
    output_root = Path(args.output_root) if args.output_root else project_dir / "output"
    exports_dir = Path(args.exports_dir) if args.exports_dir else project_dir / "exports"
    audio_dir = Path(args.audio_dir) if args.audio_dir else output_root / "audio"

    snake = camel_to_snake(args.project)
    md_candidates = []
    if args.script_md:
        script_md = Path(args.script_md)
    else:
        md_candidates = [
            f"{args.project}.md",
            f"{args.project.lower()}.md",
            f"{snake}.md",
        ]
        script_md = find_default_file(inputs_dir, md_candidates, "*.md")

    if args.script_csv:
        script_csv = Path(args.script_csv)
    else:
        csv_candidates = [
            f"{args.project}_script.csv",
            f"{args.project.lower()}_script.csv",
            f"{snake}_script.csv",
        ]
        script_csv = find_default_file(inputs_dir, csv_candidates, "*_script.csv")

    if args.input_srt:
        input_srt = Path(args.input_srt)
    else:
        srt_candidates = [
            f"{args.project}.srt",
            f"{args.project.lower()}.srt",
            f"{snake}.srt",
        ]
        try:
            input_srt = find_default_file(inputs_dir, srt_candidates, "*.srt")
        except FileNotFoundError:
            input_srt = None

    if args.output_srt:
        output_srt = Path(args.output_srt)
    else:
        output_srt = output_root / f"{args.sample_name or args.project}_timecode.srt"

    if args.merged_srt:
        merged_srt = Path(args.merged_srt)
    else:
        merged_srt = exports_dir / f"{snake}_merged.srt"

    final_srt = Path(args.final_srt) if args.final_srt else None

    if args.timeline_csv:
        timeline_csv = Path(args.timeline_csv)
    else:
        timeline_csv = output_root / f"{args.sample_name or args.project}_timeline.csv"

    if args.timeline_xml:
        timeline_xml = Path(args.timeline_xml)
    else:
        timeline_xml = output_root / f"{args.sample_name or args.project}_timeline.xml"

    if args.export_xml:
        export_xml = Path(args.export_xml)
    else:
        export_xml = exports_dir / "timelines" / f"{args.sample_name or args.project}_timeline.xml"

    sample_name = args.sample_name or args.project

    config_paths: List[Path] = [REPO_ROOT / "experiments/tts_config/global.yaml"]
    if args.tts_config:
        config_paths.extend(Path(p) for p in args.tts_config)
    else:
        discovered = discover_tts_configs(inputs_dir)
        if discovered:
            config_paths.extend(discovered)

    return PipelineContext(
        project=args.project,
        project_dir=project_dir,
        inputs_dir=inputs_dir,
        output_root=output_root,
        exports_dir=exports_dir,
        audio_dir=audio_dir,
        script_md=script_md,
        script_csv=script_csv,
        input_srt=input_srt,
        output_srt=output_srt,
        merged_srt=merged_srt,
        final_srt=final_srt,
        timeline_csv=timeline_csv,
        timeline_xml=timeline_xml,
        export_xml=export_xml,
        sample_name=sample_name,
        scene_lead_in_sec=args.scene_gap,
        timebase=args.timebase,
        ntsc=args.ntsc,
        tts_config_paths=config_paths,
    )


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Run the shared TTS pipeline for a project.")
    parser.add_argument("--project", required=True, help="Project slug (e.g., OrionEp7)")
    parser.add_argument("--script-md", help="Path to the markdown script")
    parser.add_argument("--script-csv", help="Path to the narration CSV")
    parser.add_argument("--input-srt", help="Optional source SRT for future processing")
    parser.add_argument("--output-srt", help="Destination SRT path")
    parser.add_argument("--merged-srt", help="Destination merged SRT path")
    parser.add_argument("--final-srt", help="Destination aligned SRT path")
    parser.add_argument("--timeline-csv", help="Destination timeline CSV path")
    parser.add_argument("--timeline-xml", help="Destination XML path inside output/")
    parser.add_argument("--export-xml", help="Destination XML path inside exports/")
    parser.add_argument("--output-root", help="Override output directory")
    parser.add_argument("--exports-dir", help="Override exports directory")
    parser.add_argument("--audio-dir", help="Override audio directory")
    parser.add_argument("--sample-name", help="Base name for generated assets")
    parser.add_argument("--tts-config", action="append", help="Additional TTS config YAML paths")
    parser.add_argument("--scene-gap", type=float, default=3.0, help="Pause (seconds) after scene headings")
    parser.add_argument("--timebase", type=int, default=30, help="Timeline timebase (default: 30)")
    parser.add_argument("--ntsc", dest="ntsc", action="store_true", default=True, help="Use NTSC drop-frame rate (default)")
    parser.add_argument("--no-ntsc", dest="ntsc", action="store_false", help="Disable NTSC rate (use integer FPS)")
    parser.add_argument("--skip-srt", action="store_true", help="Skip writing SRT output")
    parser.add_argument("--skip-csv", action="store_true", help="Skip writing timeline CSV")
    parser.add_argument("--skip-xml", action="store_true", help="Skip writing timeline XML outputs")

    args = parser.parse_args(argv)

    ctx = create_context(args)

    segments = parse_script(ctx)
    print(f"Loaded {len(segments)} segment(s) from {relpath(ctx.script_md)}")

    synthesize_segments(ctx, segments)
    assign_timeline_positions(ctx, segments)

    if not args.skip_csv:
        write_csv(ctx, segments)
    if not args.skip_xml:
        build_xml(ctx, segments)
    if not args.skip_srt:
        write_srt(ctx, segments)
        if ctx.input_srt and ctx.output_srt and ctx.merged_srt:
            try:
                merge_srt_files(ctx.input_srt, ctx.output_srt, ctx.merged_srt, strategy="balanced")
                print(f"Merged SRT: {relpath(ctx.merged_srt)}")
            except Exception as exc:  # pragma: no cover - defensive
                print(f"[WARN] Failed to merge SRT ({exc})")
        if ctx.input_srt and ctx.output_srt and ctx.final_srt:
            try:
                align_srt_files(ctx.input_srt, ctx.output_srt, ctx.final_srt)
                print(f"Aligned SRT: {relpath(ctx.final_srt)}")
            except Exception as exc:  # pragma: no cover - defensive
                print(f"[WARN] Failed to align SRT ({exc})")


if __name__ == "__main__":
    main()
