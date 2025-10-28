#!/usr/bin/env python3
"""Fix Ep15 SRT timecode distribution properly."""

from pathlib import Path
import subprocess
import re


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
                'text': text
            })

    return entries


def format_timecode(seconds: float) -> str:
    """Format seconds to SRT timecode HH:MM:SS,mmm."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def distribute_timecodes(entries: list[dict], audio_files: list[Path]) -> list[dict]:
    """Distribute SRT entries across audio files proportionally.

    Strategy:
    - Audio files represent actual spoken segments
    - Distribute SRT entries proportionally based on audio duration
    - Each audio file gets at least one SRT entry
    """
    total_audio_duration = sum(get_audio_duration(f) for f in audio_files)
    num_entries = len(entries)
    num_audio = len(audio_files)

    print(f"\n📊 Distribution Strategy:")
    print(f"   Audio files: {num_audio}")
    print(f"   SRT entries: {num_entries}")
    print(f"   Total duration: {total_audio_duration:.2f}s")
    print(f"   Ratio: {num_entries/num_audio:.2f} entries/audio")

    # Calculate how many entries each audio file should get
    entries_per_audio = []
    cumulative_duration = 0.0

    for i, audio_file in enumerate(audio_files):
        duration = get_audio_duration(audio_file)
        cumulative_duration += duration

        # Calculate expected number of entries for this audio file
        expected_entries = (cumulative_duration / total_audio_duration) * num_entries

        if i == 0:
            # First audio file: assign entries from start to expected
            count = max(1, round(expected_entries))
        else:
            # Subsequent files: assign from previous cumulative to current
            prev_cumulative = sum(entries_per_audio)
            count = max(1, round(expected_entries) - prev_cumulative)

        entries_per_audio.append(count)

    # Adjust last audio file to ensure we use all entries
    total_assigned = sum(entries_per_audio)
    if total_assigned != num_entries:
        entries_per_audio[-1] += (num_entries - total_assigned)

    # Assign timecodes
    current_time = 0.0
    entry_idx = 0
    updated_entries = []

    for i, audio_file in enumerate(audio_files):
        duration = get_audio_duration(audio_file)
        num_entries_for_audio = entries_per_audio[i]

        # Calculate time per entry for this audio file
        time_per_entry = duration / num_entries_for_audio if num_entries_for_audio > 0 else duration

        for j in range(num_entries_for_audio):
            if entry_idx >= num_entries:
                break

            entry = entries[entry_idx].copy()
            start_time = current_time
            end_time = current_time + time_per_entry

            entry['timecode'] = f"{format_timecode(start_time)} --> {format_timecode(end_time)}"
            updated_entries.append(entry)

            current_time = end_time
            entry_idx += 1

        if entry_idx >= num_entries:
            break

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
    """Fix Ep15 SRT timecode distribution."""
    # Paths
    audio_dir = Path('orion/projects/OrionEp15/output/audio')
    srt_input = Path('orion/projects/OrionEp15/generated/teleop_raw.srt')
    srt_output = Path('orion/projects/OrionEp15/output/OrionEp15_timecode.srt')

    # Check files
    if not srt_input.exists():
        print(f"❌ SRT not found: {srt_input}")
        return

    if not audio_dir.exists():
        print(f"❌ Audio directory not found: {audio_dir}")
        return

    # Get audio files
    audio_files = sorted(audio_dir.glob('OrionEp15_*.mp3'))
    if not audio_files:
        print(f"❌ No audio files found in {audio_dir}")
        return

    print(f"📖 Reading SRT: {srt_input}")
    entries = parse_srt(srt_input)
    print(f"✅ Parsed {len(entries)} entries")

    print(f"📂 Found {len(audio_files)} audio files")

    # Distribute timecodes
    print("\n🔧 Distributing timecodes proportionally...")
    updated_entries = distribute_timecodes(entries, audio_files)

    # Write output
    write_srt(updated_entries, srt_output)

    # Get final duration
    final_duration = get_audio_duration(audio_files[-1])
    total_duration = sum(get_audio_duration(f) for f in audio_files)

    print(f"\n✅ Updated: {srt_output}")
    print(f"📊 Entries: {len(updated_entries)}")
    print(f"⏱️  Duration: {int(total_duration//60)}:{int(total_duration%60):02d}")


if __name__ == '__main__':
    main()
