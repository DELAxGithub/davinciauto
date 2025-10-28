#!/usr/bin/env python3
"""Regenerate SRT timecode for Orion episodes (New Pipeline compatible).

This script regenerates accurate timecodes for SRT files based on actual audio file durations.
Uses the duration-based proportional allocation logic in orion/pipeline/writers/srt.py.

Compatible with:
- YAML narration files (ep{N}nare.yaml) - Priority
- Markdown narration files (Ep{N}.md) - Fallback
- TimelineCalculator for proper timeline generation

Usage:
    python regenerate_srt_timecode.py OrionEp15
    python regenerate_srt_timecode.py OrionEp14
"""

import sys
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


def main():
    """Regenerate SRT timecode for specified project."""
    if len(sys.argv) < 2:
        print("Usage: python regenerate_srt_timecode.py <project_name>")
        print("Example: python regenerate_srt_timecode.py OrionEp15")
        sys.exit(1)

    project = sys.argv[1]

    # Add orion to path
    sys.path.insert(0, str(Path.cwd() / "orion"))

    from pipeline.parsers.srt import parse_srt_file
    from pipeline.parsers.markdown import parse_narration_file, parse_narration_yaml
    from pipeline.engines.tts import AudioSegment
    from pipeline.engines.timeline import TimelineCalculator, TimelineSegment
    from pipeline.writers.srt import write_timecode_srt

    # Paths
    project_dir = Path(f"orion/projects/{project}")
    inputs_dir = project_dir / "inputs"
    output_dir = project_dir / "output"
    audio_dir = output_dir / "audio"
    generated_dir = project_dir / "generated"

    # Check directories exist
    if not project_dir.exists():
        print(f"❌ Project directory not found: {project_dir}")
        sys.exit(1)

    if not audio_dir.exists():
        print(f"❌ Audio directory not found: {audio_dir}")
        sys.exit(1)

    # Determine episode number
    ep_num = project.replace("OrionEp", "").lstrip("0")

    # Determine source SRT file
    # Priority: generated/teleop_raw.srt > inputs/epXX.srt
    srt_source = None
    if (generated_dir / "teleop_raw.srt").exists():
        srt_source = generated_dir / "teleop_raw.srt"
        print(f"📖 Using generated SRT: {srt_source}")
    else:
        # Try to find inputs/epXX.srt
        input_srt = inputs_dir / f"ep{ep_num}.srt"
        if input_srt.exists():
            srt_source = input_srt
            print(f"📖 Using input SRT: {srt_source}")
        else:
            print(f"❌ No source SRT found. Tried:")
            print(f"   - {generated_dir / 'teleop_raw.srt'}")
            print(f"   - {input_srt}")
            sys.exit(1)

    # Load source subtitles
    print(f"📖 Loading subtitles from: {srt_source}")
    source_subs = parse_srt_file(srt_source)
    print(f"✅ Loaded {len(source_subs)} subtitles")

    # Load narration segments
    # Priority: YAML > Markdown
    narration_segments = None
    nare_script_path = None

    yaml_candidates = [
        inputs_dir / f"ep{ep_num}nare.yaml",
        inputs_dir / f"Ep{ep_num}nare.yaml",
    ]

    for yaml_path in yaml_candidates:
        if yaml_path.exists():
            print(f"📄 Loading narration YAML: {yaml_path}")
            narration_segments = parse_narration_yaml(yaml_path)
            print(f"✅ Loaded {len(narration_segments)} narration segments from YAML")
            break

    if narration_segments is None:
        # Fallback to Markdown
        md_candidates = [
            inputs_dir / f"Ep{ep_num}.md",
            inputs_dir / f"ep{ep_num}.md",
        ]

        for md_path in md_candidates:
            if md_path.exists():
                print(f"📄 Loading narration Markdown: {md_path}")
                narration_segments = parse_narration_file(md_path)
                nare_script_path = md_path
                print(f"✅ Loaded {len(narration_segments)} narration segments from Markdown")
                break

    if narration_segments is None:
        print(f"⚠️  No narration file found (YAML or Markdown)")
        print(f"   Will use duration-based fallback allocation only")

    # Build audio segments and timeline
    print(f"\n📂 Building audio segments from files...")
    audio_files = sorted(audio_dir.glob(f"{project}_*.mp3"))

    if not audio_files:
        print(f"❌ No audio files found in {audio_dir}")
        sys.exit(1)

    audio_segments = []
    timeline = None

    if narration_segments:
        # Build audio segments from narration + actual audio files
        for seg in narration_segments:
            audio_path = audio_dir / seg.audio_filename(project)
            if not audio_path.exists():
                print(f"⚠️  Audio file not found for segment {seg.index}: {audio_path.name}")
                break
            audio_segments.append(
                AudioSegment.from_existing_file(seg.index, seg.text, audio_path)
            )

        print(f"✅ Built {len(audio_segments)} audio segments")

        # Calculate timeline using TimelineCalculator
        print(f"\n🔧 Calculating timeline (29.97 fps, 3.0s lead-in)...")
        timeline_calc = TimelineCalculator(fps=29.97, scene_lead_in_sec=3.0)
        timeline = timeline_calc.calculate_timeline(
            audio_segments,
            narration_segments=narration_segments[:len(audio_segments)]
        )

        total_duration = timeline[-1].end_time_sec if timeline else 0.0
        print(f"✅ Timeline: {len(timeline)} segments")
        print(f"⏱️  Total duration: {total_duration:.2f}s ({int(total_duration//60)}:{int(total_duration%60):02d})")
    else:
        # Fallback: build simple timeline from audio files only
        print(f"⚠️  Building simple timeline without narration segments")
        timeline = []
        current_time = 0.0

        for idx, audio_file in enumerate(audio_files):
            duration = get_audio_duration(audio_file)
            if duration == 0.0:
                print(f"⚠️  Skipping {audio_file.name} (zero duration)")
                continue

            segment = TimelineSegment(
                index=idx,
                audio_filename=audio_file.name,
                audio_duration_sec=duration,
                start_time_sec=current_time,
                end_time_sec=current_time + duration
            )
            timeline.append(segment)
            current_time += duration

        print(f"✅ Timeline: {len(timeline)} segments")
        print(f"⏱️  Total duration: {current_time:.2f}s ({int(current_time//60)}:{int(current_time%60):02d})")

    # Output path
    srt_output = output_dir / f"{project}_timecode.srt"

    # Generate timecode SRT
    print(f"\n🔧 Generating timecode SRT...")
    write_timecode_srt(
        srt_output,
        source_subs,
        timeline,
        nare_script_path=nare_script_path,
        nare_segments=narration_segments[:len(audio_segments)] if (narration_segments and audio_segments) else None
    )

    total_duration = timeline[-1].end_time_sec if timeline else 0.0
    print(f"\n✅ Complete: {srt_output}")
    print(f"📊 Subtitles: {len(source_subs)}")
    print(f"📊 Audio segments: {len(timeline)}")
    print(f"⏱️  Total: {int(total_duration//60)}:{int(total_duration%60):02d}")


if __name__ == "__main__":
    main()
