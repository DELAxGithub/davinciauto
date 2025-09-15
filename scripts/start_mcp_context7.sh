#!/usr/bin/env bash
set -euo pipefail

# Context7 commonly uses Upstash Vector env vars. Adjust as needed.
missing=0
for k in UPSTASH_VECTOR_REST_URL UPSTASH_VECTOR_REST_TOKEN UPSTASH_VECTOR_INDEX; do
  if [[ -z "${!k:-}" ]]; then
    echo "[warn] $k is not set" >&2
    missing=1
  fi
done
if [[ "$missing" = "1" ]]; then
  echo "Continuing anyway (server may still start depending on your setup)." >&2
fi

exec npx -y @upstash/context7-mcp@latest
