#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${ELEVENLABS_API_KEY:-}" ]]; then
  echo "[error] ELEVENLABS_API_KEY is not set. Add it to your .env or export it in the shell." >&2
  exit 1
fi

if command -v uvx >/dev/null 2>&1; then
  exec uvx elevenlabs-mcp
else
  exec python -m elevenlabs_mcp
fi
