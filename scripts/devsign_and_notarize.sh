#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 2 ]; then
  echo "Usage: $0 <bundle_dir> <bundle_dmg>" >&2
  exit 1
fi

DIST_DIR="$1"
DMG_PATH="$2"
IDENT="${DEVELOPER_ID_APP:?Set DEVELOPER_ID_APP='Developer ID Application: Your Name (TEAMID)'}"
PROFILE_NAME="${AC_PROFILE:-AC_NOTARY}"

if [ ! -d "$DIST_DIR" ]; then
  echo "Distribution directory '$DIST_DIR' not found" >&2
  exit 1
fi
if [ ! -f "$DMG_PATH" ]; then
  echo "DMG '$DMG_PATH' not found" >&2
  exit 1
fi

echo "Signing executables under $DIST_DIR"
while IFS= read -r -d '' file; do
  codesign --force --timestamp --options runtime --sign "$IDENT" "$file"
done < <(find "$DIST_DIR" -type f \( -perm -111 -o -name "*.dylib" -o -name "*.so" \) -print0)

codesign --verify --strict --deep -v "$DIST_DIR/davinciauto-cli"
if ! spctl --assess --type execute -vv "$DIST_DIR/davinciauto-cli"; then
  echo "spctl assessment produced warnings (continuing)."
fi

echo "Submitting $DMG_PATH for notarization via profile '$PROFILE_NAME'"
xcrun notarytool submit "$DMG_PATH" --keychain-profile "$PROFILE_NAME" --wait
xcrun stapler staple "$DMG_PATH"
echo "Signed & notarized: $DMG_PATH"
