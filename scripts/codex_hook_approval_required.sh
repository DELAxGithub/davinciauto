#!/usr/bin/env bash

# Hook-friendly wrapper to notify on Codex approval/confirmation needs.
# Accepts an optional context message as $1 and an optional details as $2.
# Example usage (from your hooks system):
#   scripts/codex_hook_approval_required.sh "ファイル書き込みが必要" "プロジェクト: X"

set -euo pipefail

CONTEXT=${1:-"承認が必要です"}
DETAILS=${2:-""}

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)

TITLE="Codex"
SUBTITLE="確認/承認のリクエスト"
MESSAGE="${CONTEXT}${DETAILS:+ - ${DETAILS}}"

"${SCRIPT_DIR}/notify_mac.sh" "${TITLE}" "${SUBTITLE}" "${MESSAGE}" "Submarine"

exit 0

