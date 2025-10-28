#!/usr/bin/env python3
"""Fix Ep15 SRT timecode by aligning with YAML segments."""

from pathlib import Path
import subprocess
import re
import yaml


def get_audio_duration(audio_path: Path) -> float:
    """Get audio duration in seconds using ffprobe."""
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(audio_path)
            ],
            capture_output=True,
            text=True,
            check=True
        )
        return float(result.stdout.strip())
    except (subprocess.CalledProcessError, ValueError) as e:
        print(f"⚠️  Failed to get duration for {audio_path.name}: {e}")
        return 0.0


def load_yaml_segments(yaml_path: Path) -> list[str]:
    """Load YAML segments text."""
    with yaml_path.open('r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    segments = data.get('gemini_tts', {}).get('segments', [])
    return [seg['text'] for seg in segments]


def parse_srt(srt_path: Path) -> list[dict]:
    """Parse SRT file into entries."""
    with srt_path.open('r', encoding='utf-8') as f:
        content = f.read()

    entries = []
    raw_entries = content.strip().split('\n\n')

    for raw in raw_entries:
        lines = raw.split('\n')
        if len(lines) >= 3:
            seq_num = lines[0].strip()
            timecode = lines[1].strip()
            text = '\n'.join(lines[2:])
            entries.append({
                'seq': seq_num,
                'timecode': timecode,
                'text': text,
                'text_normalized': text.replace('\n', ' ').replace(' ', '')
            })

    return entries


def normalize_text(text: str) -> str:
    """Normalize text for comparison (remove spaces, punctuation, etc)."""
    # Remove spaces, newlines, punctuation
    text = text.replace(' ', '').replace('\n', '').replace('　', '')
    text = text.replace('、', '').replace('。', '').replace('，', '').replace('！', '').replace('？', '')
    text = text.replace(',', '').replace('.', '').replace('!', '').replace('?', '')
    return text


def match_srt_to_yaml(yaml_segments: list[str], srt_entries: list[dict]) -> dict[int, list[int]]:
    """Match SRT entries to YAML segments.

    Returns:
        Dict mapping YAML segment index to list of SRT entry indices
    """
    mapping = {}
    used_srt_indices = set()

    for yaml_idx, yaml_text in enumerate(yaml_segments):
        yaml_normalized = normalize_text(yaml_text)
        matching_srt_indices = []

        # Try to find SRT entries that match this YAML segment
        accumulated_text = ""
        for srt_idx, srt_entry in enumerate(srt_entries):
            if srt_idx in used_srt_indices:
                continue

            srt_normalized = normalize_text(srt_entry['text'])
            accumulated_text += srt_normalized

            # Check if accumulated SRT text matches YAML segment
            if accumulated_text in yaml_normalized or yaml_normalized.startswith(accumulated_text):
                matching_srt_indices.append(srt_idx)
                used_srt_indices.add(srt_idx)

                # If we've matched the complete YAML segment, stop
                if accumulated_text == yaml_normalized:
                    break

        if matching_srt_indices:
            mapping[yaml_idx] = matching_srt_indices

    return mapping


def format_timecode(seconds: float) -> str:
    """Format seconds to SRT timecode HH:MM:SS,mmm."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def assign_timecodes(
    yaml_segments: list[str],
    srt_entries: list[dict],
    audio_files: list[Path],
    yaml_to_srt_mapping: dict[int, list[int]]
) -> list[dict]:
    """Assign timecodes to SRT entries based on YAML-audio alignment."""

    updated_entries = []
    current_time = 0.0

    for yaml_idx, audio_file in enumerate(audio_files):
        if yaml_idx >= len(yaml_segments):
            print(f"⚠️  More audio files ({len(audio_files)}) than YAML segments ({len(yaml_segments)})")
            break

        audio_duration = get_audio_duration(audio_file)
        srt_indices = yaml_to_srt_mapping.get(yaml_idx, [])

        if not srt_indices:
            print(f"⚠️  No SRT entries for YAML segment {yaml_idx}: {yaml_segments[yaml_idx][:50]}...")
            current_time += audio_duration
            continue

        # Distribute audio duration evenly across SRT entries for this segment
        num_srt_entries = len(srt_indices)
        time_per_entry = audio_duration / num_srt_entries

        for i, srt_idx in enumerate(srt_indices):
            entry = srt_entries[srt_idx].copy()
            start_time = current_time + (i * time_per_entry)
            end_time = start_time + time_per_entry

            entry['timecode'] = f"{format_timecode(start_time)} --> {format_timecode(end_time)}"
            updated_entries.append(entry)

        current_time += audio_duration

    return updated_entries


def write_srt(entries: list[dict], output_path: Path):
    """Write entries to SRT file."""
    with output_path.open('w', encoding='utf-8') as f:
        for entry in entries:
            f.write(f"{entry['seq']}\n")
            f.write(f"{entry['timecode']}\n")
            f.write(f"{entry['text']}\n")
            f.write("\n")


def main():
    """Fix Ep15 SRT timecode by aligning with YAML segments."""
    # Paths
    yaml_path = Path('orion/projects/OrionEp15/inputs/ep15nare.yaml')
    audio_dir = Path('orion/projects/OrionEp15/output/audio')
    srt_input = Path('orion/projects/OrionEp15/generated/teleop_raw.srt')
    srt_output = Path('orion/projects/OrionEp15/output/OrionEp15_timecode.srt')

    # Load data
    print(f"📖 Loading YAML segments: {yaml_path}")
    yaml_segments = load_yaml_segments(yaml_path)
    print(f"✅ Loaded {len(yaml_segments)} YAML segments")

    print(f"\n📖 Parsing SRT: {srt_input}")
    srt_entries = parse_srt(srt_input)
    print(f"✅ Parsed {len(srt_entries)} SRT entries")

    print(f"\n📂 Scanning audio files: {audio_dir}")
    audio_files = sorted(audio_dir.glob('OrionEp15_*.mp3'))
    print(f"✅ Found {len(audio_files)} audio files")

    # Match SRT to YAML
    print(f"\n🔗 Matching SRT entries to YAML segments...")
    yaml_to_srt_mapping = match_srt_to_yaml(yaml_segments, srt_entries)

    print(f"\n📊 Mapping Results:")
    for yaml_idx, srt_indices in sorted(yaml_to_srt_mapping.items())[:10]:
        print(f"  YAML {yaml_idx+1:3d} → SRT {[i+1 for i in srt_indices]} | {yaml_segments[yaml_idx][:60]}...")

    total_mapped_srt = sum(len(indices) for indices in yaml_to_srt_mapping.values())
    print(f"  Total mapped SRT entries: {total_mapped_srt}/{len(srt_entries)}")

    # Assign timecodes
    print(f"\n🔧 Assigning timecodes...")
    updated_entries = assign_timecodes(yaml_segments, srt_entries, audio_files, yaml_to_srt_mapping)

    # Write output
    write_srt(updated_entries, srt_output)

    total_duration = sum(get_audio_duration(f) for f in audio_files)
    print(f"\n✅ Updated: {srt_output}")
    print(f"📊 Entries: {len(updated_entries)}")
    print(f"⏱️  Duration: {int(total_duration//60)}:{int(total_duration%60):02d}")


if __name__ == '__main__':
    main()
