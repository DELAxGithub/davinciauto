# CLI Setup Guide

This guide explains how to run the DaVinci Auto pipeline via the new `davinciauto-cli` command.

## Prerequisites
- macOS with Python 3.11 installed (via python.org, Homebrew, pyenv, etc.).
- `ffmpeg` and `ffprobe` available on the system path (Homebrew `brew install ffmpeg` works). You can override the discovery path by exporting `DAVA_FFMPEG_PATH` and `DAVA_FFPROBE_PATH`.
- Clone of this repository.

## Quick Start
```bash
./scripts/bootstrap_cli.sh  # creates .venv and installs editable package
make self-check             # verifies Python + ffmpeg availability
make fake-tts               # runs a fake TTS pipeline using samples/sample_script.txt
```

Outputs from `make fake-tts` are written to `.out/fake_tts/` (audio, subtitles, storyboard JSON).

## Using the CLI directly
After bootstrap, the CLI binary lives at `.venv/bin/davinciauto-cli`.

```bash
# Run environment diagnostics (JSON output)
.venv/bin/davinciauto-cli --self-check --json

# Execute fake TTS run
.venv/bin/davinciauto-cli run \
  --script samples/sample_script.txt \
  --output .out/manual_run \
  --fake-tts \
  --provider fake \
  --target resolve
```

Pass `--api-key` when invoking `run` to supply a provider key (or set `ELEVENLABS_API_KEY` in the environment). Additional arguments map directly to `PipelineConfig` fields (see `davinciauto_core.pipeline`).

## Smoke Test Script
`make smoke` executes `scripts/smoke_fake_tts.sh`, which:
1. Generates a small script in `.out/smoke/`.
2. Runs `davinciauto-cli --self-check --json`.
3. Runs `davinciauto-cli run --fake-tts` against the generated script.

Use this smoke test before sharing the CLI bundle with collaborators.

## Next Steps
- `docs/CLI_BUNDLE.md` walks through creating versioned bundles, DMGs, and hashes.
- `Makefile` contains additional helper targets (`make run ARGS=...` / `make bundle`).
