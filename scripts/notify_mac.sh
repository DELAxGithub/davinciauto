#!/usr/bin/env bash

# Lightweight macOS notification helper using AppleScript.
# Usage:
#   scripts/notify_mac.sh "Title" "Subtitle" "Message" [sound_name]
# Example:
#   scripts/notify_mac.sh "Codex" "承認が必要" "ネットワークアクセスを許可してください" "Submarine"

set -euo pipefail

TITLE=${1:-"Codex"}
SUBTITLE=${2:-"通知"}
MESSAGE=${3:-""}
SOUND=${4:-""}

if [[ -n "${SOUND}" ]]; then
  osascript -e "display notification \"${MESSAGE}\" with title \"${TITLE}\" subtitle \"${SUBTITLE}\" sound name \"${SOUND}\""
else
  osascript -e "display notification \"${MESSAGE}\" with title \"${TITLE}\" subtitle \"${SUBTITLE}\""
fi

exit 0

