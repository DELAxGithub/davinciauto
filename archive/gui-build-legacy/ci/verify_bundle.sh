#!/usr/bin/env bash
set -euo pipefail

BUNDLE_DIR="${1:?Usage: $0 dist/davinciauto-cli-<ver>-<arch> <dmg>}"
DMG_PATH="${2:?Usage: $0 <bundle_dir> <dmg>}"
CLI="$BUNDLE_DIR/davinciauto-cli"

if [ ! -x "$CLI" ]; then
  echo "CLI binary not found at $CLI" >&2
  exit 1
fi

# 1) Architecture check
file "$CLI"
arch_line=$(file "$CLI")
case "$arch_line" in
  *"arm64"*|*"x86_64"*) ;;
  *) echo "Unexpected architecture in $CLI" >&2; exit 1;;
 esac

# 2) Self-check validation
OUT=$("$CLI" --self-check --json)
echo "$OUT"
SELF_CHECK_JSON="$OUT" python - <<'PY'
import json, os
schema_keys = {"ok", "version", "bundle", "ffmpeg", "licenses"}
obj = json.loads(os.environ["SELF_CHECK_JSON"])
missing = schema_keys - set(obj)
if missing:
    raise SystemExit(f"missing keys: {sorted(missing)}")
if not obj.get("ok", False):
    raise SystemExit("self-check reported failure")
licenses = obj.get("licenses", {})
if not licenses.get("present", False):
    raise SystemExit("licenses missing in bundle")
ffmpeg = obj.get("ffmpeg", {})
path = ffmpeg.get("path") if isinstance(ffmpeg, dict) else ffmpeg
if not path or path == "NOT_FOUND":
    raise SystemExit("ffmpeg path missing")
PY

# 3) DMG contents
MNT=$(mktemp -d /tmp/davinciauto-verify.XXXX)
cleanup() { hdiutil detach "$MNT" -quiet || true; rm -rf "$MNT"; }
trap cleanup EXIT
hdiutil attach "$DMG_PATH" -mountpoint "$MNT" -nobrowse -quiet
for f in README_FIRST.txt licenses/FFmpeg-LICENSE.md; do
  if [ ! -f "$MNT/$f" ]; then
    echo "DMG missing $f" >&2
    exit 1
  fi
 done
hdiutil detach "$MNT" -quiet
trap - EXIT
rm -rf "$MNT"

# 4) Fake run smoke
"$CLI" run --script "$BUNDLE_DIR/samples/sample_script.txt" \
  --output "$BUNDLE_DIR/../.out_verify" --provider fake --target resolve --fake-tts

# 5) Hashes (if available)
if [ -f "${BUNDLE_DIR}-SHA256SUMS.txt" ]; then
  shasum -a 256 -c "${BUNDLE_DIR}-SHA256SUMS.txt"
fi

echo "RC verify OK"
