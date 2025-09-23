#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$SCRIPT_DIR"
CLI="${CLI_PATH:-$ROOT_DIR/davinciauto-cli}"
LOG_DIR="${LOG_DIR:-$HOME/Library/Logs/davinciauto-cli}"
mkdir -p "$LOG_DIR"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
LOG_FILE="$LOG_DIR/launcher-$TIMESTAMP.log"

MODE=${1:?"usage: gui_launcher_run.sh <mode> [options...]"}
shift || true

exec_cmd() {
  echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LOG_FILE"
  "$@" 2>&1 | tee -a "$LOG_FILE"
}

case "$MODE" in
  self-check)
    exec_cmd "$CLI" --self-check --json
    ;;
  fake-run)
    SCRIPT_PATH=${1:?"missing script path"}
    OUTPUT_DIR=${2:?"missing output dir"}
    PROVIDER=${3:-azure}
    TARGET=${4:-resolve}
    if [[ "$PROVIDER" != "azure" ]]; then
      echo "[WARN] TTS provider override is no longer supported; using azure." | tee -a "$LOG_FILE"
    fi
    exec_cmd "$CLI" run \
      --script "$SCRIPT_PATH" \
      --output "$OUTPUT_DIR" \
      --fake-tts \
      --provider azure \
      --target "$TARGET"
    ;;
  full-run)
    SCRIPT_PATH=${1:?"missing script path"}
    OUTPUT_DIR=${2:?"missing output dir"}
    PROVIDER=${3:-azure}
    TARGET=${4:-resolve}
    if [[ "$PROVIDER" != "azure" ]]; then
      echo "[WARN] TTS provider override is no longer supported; using azure." | tee -a "$LOG_FILE"
    fi
    exec_cmd "$CLI" run \
      --script "$SCRIPT_PATH" \
      --output "$OUTPUT_DIR" \
      --provider azure \
      --target "$TARGET"
    ;;
  *)
    echo "Unknown mode: $MODE" >&2
    exit 1
    ;;
 esac

osascript <<OSA
display dialog "処理が完了しました。ログ: $LOG_FILE" buttons {"OK"} default button "OK"
OSA
