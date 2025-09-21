#!/usr/bin/env bash
set -euo pipefail

if ! command -v python3.11 >/dev/null 2>&1; then
  echo "python3.11 not found. Please install Python 3.11 before running this script." >&2
  exit 1
fi

make setup

echo "\nBootstrap complete. Next steps:"
echo "  make self-check"
echo "  make fake-tts"
