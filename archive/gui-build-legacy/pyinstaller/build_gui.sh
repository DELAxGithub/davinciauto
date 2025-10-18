#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
VENV=${VENV:-$ROOT/.venv}
PYINSTALLER=${PYINSTALLER:-$VENV/bin/pyinstaller}
SPEC_GUI=$ROOT/pyinstaller/davinciauto_gui.spec
DIST_DIR=${DIST_DIR:-$ROOT/dist}
WORK_DIR=${WORK_DIR:-$ROOT/build/pyinstaller_gui}
APP_NAME="DaVinciAuto GUI.app"
APP_PATH="$DIST_DIR/$APP_NAME"
DMG_PATH="$DIST_DIR/DaVinciAuto_GUI.dmg"

if [ ! -x "$PYINSTALLER" ]; then
  echo "pyinstaller binary not found. run 'make setup' first." >&2
  exit 1
fi

rm -rf "$APP_PATH" "$DIST_DIR/davinciauto_gui" "$DIST_DIR/davinciauto_gui_bundle" "$DMG_PATH" "$WORK_DIR"

"$PYINSTALLER" "$SPEC_GUI" \
  --noconfirm \
  --distpath "$DIST_DIR" \
  --workpath "$WORK_DIR" \
  --clean

if [ ! -d "$APP_PATH" ]; then
  echo "PyInstaller did not produce $APP_PATH" >&2
  exit 1
fi

echo "PyInstaller bundle produced at $APP_PATH"

DMG_STAGE=$(mktemp -d "$ROOT/tmp_davinciauto_gui.XXXX")
trap 'rm -rf "$DMG_STAGE"' EXIT

mkdir -p "$DMG_STAGE"
cp -R "$APP_PATH" "$DMG_STAGE/"
ln -s /Applications "$DMG_STAGE/Applications"

hdiutil create -volname "DaVinciAuto GUI" -srcfolder "$DMG_STAGE" -ov -format UDZO "$DMG_PATH"

echo "DMG created at $DMG_PATH"
