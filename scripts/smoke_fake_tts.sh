#!/usr/bin/env bash
set -euo pipefail

CLI="${CLI_PATH:-}"
if [ -z "$CLI" ] && command -v davinciauto-cli >/dev/null 2>&1; then
  CLI=$(command -v davinciauto-cli)
fi
if [ -z "$CLI" ]; then
  CLI="./.venv/bin/davinciauto-cli"
fi

FFMPEG_BIN="${DAVA_FFMPEG_PATH:-${FFMPEG_PATH:-}}"
if [ -z "$FFMPEG_BIN" ]; then
  FFMPEG_BIN=$(command -v ffmpeg 2>/dev/null || true)
fi
FFPROBE_BIN="${DAVA_FFPROBE_PATH:-${FFPROBE_PATH:-}}"
if [ -z "$FFPROBE_BIN" ]; then
  FFPROBE_BIN=$(command -v ffprobe 2>/dev/null || true)
fi
if [ -z "$FFMPEG_BIN" ] || [ -z "$FFPROBE_BIN" ]; then
  echo "Warning: ffmpeg/ffprobe not found; Fake-TTS run may fall back to silent audio." >&2
fi

if [ ! -x "$CLI" ]; then
  echo "davinciauto-cli not found. Run 'make setup' first." >&2
  exit 1
fi

OUT_DIR="${APP_OUT:-.out/smoke}"
RUN_DIR="$OUT_DIR/run"
SCRIPT_PATH="$OUT_DIR/script.txt"

mkdir -p "$RUN_DIR"
printf 'NA: これはスモークテストです。\nセリフ: 偽TTSモードが動作しています。\n' > "$SCRIPT_PATH"

set +e
DAVA_FFMPEG_PATH="$FFMPEG_BIN" DAVA_FFPROBE_PATH="$FFPROBE_BIN" "$CLI" --self-check --json
SELF_CHECK_STATUS=$?
set -e

if [ $SELF_CHECK_STATUS -ne 0 ]; then
  echo "Self-check reported issues (exit $SELF_CHECK_STATUS). Continuing to Fake-TTS run." >&2
fi

DAVA_FFMPEG_PATH="$FFMPEG_BIN" DAVA_FFPROBE_PATH="$FFPROBE_BIN" \
  "$CLI" run --script "$SCRIPT_PATH" --output "$RUN_DIR" --fake-tts --provider fake --target resolve

echo "Smoke test complete. Inspect outputs under $RUN_DIR"
