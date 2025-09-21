#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 <collector_dir> [dmg_name]" >&2
  exit 1
fi

COLLECT_DIR="$1"
DMG_NAME="${2:-davinciauto-cli}"

if [ ! -d "$COLLECT_DIR" ]; then
  echo "Collector directory '$COLLECT_DIR' not found" >&2
  exit 1
fi

DIST_DIR="dist"
mkdir -p "$DIST_DIR"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

cp -R "$COLLECT_DIR" "$TMP_DIR/$DMG_NAME"
hdiutil create -volname "$DMG_NAME" -srcfolder "$TMP_DIR/$DMG_NAME" -format UDZO -ov "$DIST_DIR/$DMG_NAME.dmg"
echo "DMG packaged at $DIST_DIR/$DMG_NAME.dmg"
