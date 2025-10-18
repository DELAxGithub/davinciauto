#!/usr/bin/env python3
"""Generic TTS generation script for Orion episodes.

Usage:
    python generate_tts.py --episode 12
    python generate_tts.py --episode 13 --limit 10  # Test first 10 segments
    python generate_tts.py --episode 12 --delay 5.0  # Increase delay between requests
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent
SCRIPTS_DIR = REPO_ROOT.parent / "scripts"
EXPERIMENTS_DIR = REPO_ROOT.parent / "experiments"

# Add to path
for path in [SCRIPTS_DIR, EXPERIMENTS_DIR]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from tts_config_loader import load_merged_tts_config  # type: ignore  # noqa: E402
from orion_tts_generator import OrionTTSGenerator  # type: ignore  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def load_yaml_segments(yaml_path: Path, limit: int | None = None) -> list[dict]:
    """Load segments from YAML file.

    Args:
        yaml_path: Path to YAML file (e.g., ep12nare.yaml)
        limit: Maximum number of segments to load (None = all)

    Returns:
        List of segment dictionaries with speaker, voice, text, style_prompt
    """
    with yaml_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    segments = data.get("gemini_tts", {}).get("segments", [])
    if not segments:
        raise ValueError(f"No segments found in {yaml_path}")

    logger.info("Total segments in YAML: %d", len(segments))

    if limit and limit < len(segments):
        logger.info("Loading first %d segments (limit specified)", limit)
        return segments[:limit]

    logger.info("Loading all %d segments", len(segments))
    return segments


def generate_tts_for_episode(
    episode_num: int,
    limit: int | None = None,
    request_delay: float = 3.0
) -> None:
    """Generate TTS audio for an episode.

    Args:
        episode_num: Episode number (e.g., 12)
        limit: Maximum number of segments to generate (None = all)
        request_delay: Delay in seconds between TTS requests (default: 3.0)
    """
    episode_name = f"OrionEp{episode_num:02d}"

    logger.info("=" * 64)
    logger.info("Orion TTS Generation - %s", episode_name)
    logger.info("=" * 64)

    # Project directory
    project_dir = REPO_ROOT / "projects" / episode_name
    if not project_dir.exists():
        logger.error("Project directory not found: %s", project_dir)
        logger.error("Please create the project directory first with:")
        logger.error("  mkdir -p %s/{inputs,output/audio,exports}", project_dir)
        return

    # Input YAML file
    yaml_path = project_dir / "inputs" / f"ep{episode_num}nare.yaml"
    if not yaml_path.exists():
        logger.error("YAML file not found: %s", yaml_path)
        logger.error("Expected format: ep{N}nare.yaml")
        return

    # Load TTS configuration
    try:
        config = load_merged_tts_config(episode_name)
        logger.info("✅ Loaded TTS configuration for %s", episode_name)
    except Exception as exc:
        logger.error("Failed to load TTS config: %s", exc)
        logger.info("Using default configuration")
        config = None

    # Load YAML segments
    try:
        segments = load_yaml_segments(yaml_path, limit=limit)
    except Exception as exc:
        logger.error("Failed to load YAML segments: %s", exc)
        return

    # Setup output directory
    output_dir = project_dir / "output" / "audio"
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info("📁 Output directory: %s", output_dir)

    # Initialize TTS generator
    generator = OrionTTSGenerator(config)
    logger.info("⚙️  Request delay: %.1fs between segments", request_delay)

    # Generate audio
    success = 0
    prev_scene: str | None = None

    for idx, segment in enumerate(segments):
        segment_no = idx + 1
        speaker = segment.get("speaker", "ナレーター")
        text = segment.get("text", "")
        voice = segment.get("voice")
        style_prompt = segment.get("style_prompt")
        scene = segment.get("scene")

        # Scene transition marker
        if scene and scene != prev_scene:
            logger.info("")
            logger.info("=" * 64)
            logger.info("SCENE: %s", scene)
            logger.info("=" * 64)
            prev_scene = scene

        # Output filename
        output_file = output_dir / f"{episode_name}_{segment_no:03d}.mp3"

        logger.info("")
        logger.info("[%03d/%03d] Generating: %s", segment_no, len(segments), output_file.name)
        logger.info("  Speaker: %s", speaker)
        logger.info("  Voice: %s", voice or "default")
        logger.info("  Text: %s", text[:60] + "..." if len(text) > 60 else text)

        try:
            success_flag = generator.generate(
                text=text,
                character=speaker,
                output_path=output_file,
                segment_no=segment_no,
                scene=scene,
                prev_scene=prev_scene,
                gemini_voice=voice,
                gemini_style_prompt=style_prompt
            )

            if success_flag and output_file.exists():
                file_size = output_file.stat().st_size / 1024  # KB
                logger.info("  ✅ Generated: %s (%.1f KB)", output_file.name, file_size)
                success += 1

                # Delay between requests
                if segment_no < len(segments):
                    import time
                    time.sleep(request_delay)
            else:
                logger.warning("  ❌ Failed to generate audio")

        except Exception as exc:
            logger.error("  ❌ Error generating audio: %s", exc)
            continue

    logger.info("")
    logger.info("=" * 64)
    logger.info("✅ Generation complete: %d/%d segments successful", success, len(segments))
    logger.info("=" * 64)
    logger.info("📁 Audio files saved to: %s", output_dir)


def main():
    parser = argparse.ArgumentParser(description="Generate TTS audio for Orion episodes")
    parser.add_argument(
        "--episode",
        type=int,
        required=True,
        help="Episode number (e.g., 12 for OrionEp12)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of segments to generate (for testing)"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=3.0,
        help="Delay in seconds between TTS requests (default: 3.0)"
    )

    args = parser.parse_args()

    generate_tts_for_episode(
        episode_num=args.episode,
        limit=args.limit,
        request_delay=args.delay
    )


if __name__ == "__main__":
    main()
