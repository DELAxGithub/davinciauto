# CLI Bundle (PyInstaller)

This document captures the steps for producing and validating a standalone CLI bundle using PyInstaller.

## Build Steps

```bash
# assumes `make setup` has been run; CLI_VERSION defaults to pyproject version
CLI_VERSION=0.1.0 CLI_ARCH=$(uname -m) make bundle
```

Artifacts under `dist/`:

- `dist/davinciauto-cli-${version}-${arch}/` – collected binary with `README_FIRST.txt`, `CLI_SETUP.md`, `GUI_LAUNCHER.md`, `DavinciAutoLauncher.command`, `gui_launcher_run.sh`, `samples/`, `licenses/`, `VERSION`
- `dist/davinciauto-cli-${version}-${arch}.dmg` – disk image wrapper (ad-hoc signed by default)
- `dist/davinciauto-cli-${version}-${arch}.tar.gz` – tgz of the directory bundle
- `dist/davinciauto-cli-${version}-${arch}-SHA256SUMS.txt` – SHA256 hashes for DMG + TGZ

Environment overrides during bundling:

- `CLI_VERSION` / `CLI_ARCH` – customise artifact naming
- `DAVINCIAUTO_FFMPEG_BUNDLE` – path to ffmpeg executable to embed (defaults to `which ffmpeg`)
- `DAVINCIAUTO_FFPROBE_BUNDLE` – optional override for ffprobe

## First-Run Instructions
1. Mount the DMG and copy `davinciauto-cli-${version}-${arch}` to a writable location.
2. Clear the quarantine flag if Gatekeeper blocks execution:
   ```bash
   xattr -dr com.apple.quarantine /path/to/davinciauto-cli-${version}-${arch}
   ```
3. Verify the bundle:
   ```bash
   /path/to/davinciauto-cli-${version}-${arch}/davinciauto-cli --self-check --json | jq
   ```
4. Execute a Fake-TTS run:
   ```bash
 /path/to/davinciauto-cli-${version}-${arch}/davinciauto-cli run \
   --script samples/sample_script.txt \
   --output ./out \
   --fake-tts --provider fake --target resolve
 ```
5. Confirm licenses and docs are present:
   ```bash
   ls /path/to/davinciauto-cli-${version}-${arch}/{licenses,CLI_SETUP.md,README_FIRST.txt}
   ```
6. Validate downloads:
   ```bash
   shasum -a 256 -c davinciauto-cli-${version}-${arch}-SHA256SUMS.txt
   ```

## Signing / Notarization
- Default bundles are ad-hoc signed. Use `scripts/devsign_and_notarize.sh` for Developer ID distribution:
  ```bash
  export DEVELOPER_ID_APP="Developer ID Application: Your Name (TEAMID)"
  xcrun notarytool store-credentials AC_NOTARY --apple-id you@example.com --team-id TEAMID --password app-specific
 scripts/devsign_and_notarize.sh dist/davinciauto-cli-${version}-${arch} dist/davinciauto-cli-${version}-${arch}.dmg
  ```
- Validate after stapling:
  ```bash
  spctl -a -vv dist/davinciauto-cli-${version}-${arch}/davinciauto-cli
  codesign -dv --verbose=4 dist/davinciauto-cli-${version}-${arch}/davinciauto-cli
  xcrun stapler validate dist/davinciauto-cli-${version}-${arch}.dmg
  ```
- Keep `licenses/` inside the DMG; CI enforces presence of `FFmpeg-LICENSE.md`.

## Checklist
- [x] PyInstaller spec + runtime hook
- [x] DMG packaging script
- [x] Developer ID signing helper (`scripts/devsign_and_notarize.sh`)
- [x] SHA256 sums emitted for DMG/TGZ
- [ ] Optional: generate consolidated third-party notices via `pip-licenses`

Additional validation contract: see [`docs/SELF_CHECK_SCHEMA.json`](SELF_CHECK_SCHEMA.json) for the JSON structure returned by `--self-check --json`. For a one-shot verification of a built bundle, run `ci/verify_bundle.sh dist/davinciauto-cli-${version}-${arch} dist/davinciauto-cli-${version}-${arch}.dmg`.
