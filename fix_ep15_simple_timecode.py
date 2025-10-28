#!/usr/bin/env python3
"""Fix Ep15 SRT timecode - simple cumulative approach."""

from pathlib import Path
import subprocess


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


def calculate_audio_boundaries(audio_files: list[Path]) -> list[tuple[float, float]]:
    """Calculate start and end time for each audio file.

    Returns:
        List of (start_time, end_time) tuples for each audio file
    """
    boundaries = []
    current_time = 0.0

    for audio_file in audio_files:
        duration = get_audio_duration(audio_file)
        start_time = current_time
        end_time = current_time + duration
        boundaries.append((start_time, end_time))
        current_time = end_time

    return boundaries


def distribute_srt_entries_simple(
    srt_entries: list[dict],
    audio_boundaries: list[tuple[float, float]]
) -> list[dict]:
    """Distribute SRT entries evenly across total audio duration.

    This is a simple approach:
    - Total audio duration divided by number of SRT entries
    - Each SRT entry gets equal time
    """
    total_duration = audio_boundaries[-1][1]  # End time of last audio file
    num_entries = len(srt_entries)
    time_per_entry = total_duration / num_entries

    updated_entries = []
    for i, entry in enumerate(srt_entries):
        start_time = i * time_per_entry
        end_time = (i + 1) * time_per_entry

        entry_copy = entry.copy()
        entry_copy['timecode'] = f"{format_timecode(start_time)} --> {format_timecode(end_time)}"
        updated_entries.append(entry_copy)

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
    """Fix Ep15 SRT timecode with simple even distribution."""
    # Paths
    audio_dir = Path('orion/projects/OrionEp15/output/audio')
    srt_input = Path('orion/projects/OrionEp15/generated/teleop_raw.srt')
    srt_output = Path('orion/projects/OrionEp15/output/OrionEp15_timecode.srt')

    # Load data
    print(f"📖 Parsing SRT: {srt_input}")
    srt_entries = parse_srt(srt_input)
    print(f"✅ Parsed {len(srt_entries)} SRT entries")

    print(f"\n📂 Scanning audio files: {audio_dir}")
    audio_files = sorted(audio_dir.glob('OrionEp15_*.mp3'))
    print(f"✅ Found {len(audio_files)} audio files")

    # Calculate audio boundaries
    print(f"\n⏱️  Calculating audio boundaries...")
    audio_boundaries = calculate_audio_boundaries(audio_files)

    total_duration = audio_boundaries[-1][1]
    print(f"   Total audio duration: {total_duration:.2f}s ({int(total_duration//60)}:{int(total_duration%60):02d})")
    print(f"   Audio files: {len(audio_files)}")
    print(f"   SRT entries: {len(srt_entries)}")
    print(f"   Ratio: {len(srt_entries)/len(audio_files):.2f} SRT/audio")

    print(f"\n🔧 Distributing timecodes evenly across total duration...")
    updated_entries = distribute_srt_entries_simple(srt_entries, audio_boundaries)

    # Write output
    write_srt(updated_entries, srt_output)

    print(f"\n✅ Updated: {srt_output}")
    print(f"📊 Entries: {len(updated_entries)}")
    print(f"⏱️  Duration: {int(total_duration//60)}:{int(total_duration%60):02d}")

    # Show first few entries for verification
    print(f"\n📋 First 5 entries:")
    for i in range(min(5, len(updated_entries))):
        entry = updated_entries[i]
        text_preview = entry['text'].replace('\n', ' ')[:50]
        print(f"   {entry['seq']:3s}  {entry['timecode']}  {text_preview}")


if __name__ == '__main__':
    main()
