# Requirements: CLI Distribution Readiness

## Background
- Existing workflow relies on `davinciauto_core.cli` which assumes a developer machine with ffmpeg/ffprobe, Python 3.11, and repository checkout.
- GUI packaging stalled; short-term objective is to let collaborators run the pipeline via CLI on another Mac without touching SwiftUI.
- Distribution target: BYOK (bring-your-own-key) users who can supply API credentials and run pipelines offline apart from provider calls.

## Goals
1. Simplify local setup for pipeline execution (`--self-check`, Fake-TTS dry runs, real runs) on clean macOS systems.
2. Provide scripted automation so setup is reproducible (no manual pip gymnastics).
3. Produce a self-contained CLI bundle (PyInstaller-based) that can be shared as a DMG/zip and run without Python preinstalled.
4. Document licensing, ffmpeg requirements, and expected environment variables for redistribution.

## Constraints
- Prefer Python 3.11 (compatibility with pyaudioop/pydub); avoid Python 3.13 until dependencies catch up.
- Keep deliverable size reasonable (<400 MB target, <300 MB ideal) by pruning unused packages/assets.
- No automated downloading at runtime; bundled resources only.
- Credentials must remain user-supplied via env vars/files; never embed keys.
- CLI should run without GUI dependencies (no Tkinter/PyObjC).

## Functional Requirements
- **FR-1**: Provide a bootstrap script (`make setup` or `./scripts/bootstrap_cli.sh`) that creates a virtualenv, installs project in editable mode, and verifies ffmpeg availability.
- **FR-2**: Expose convenience commands (`make self-check`, `make fake-tts`, `make run SCRIPT=... OUTPUT=...`) wrapping `davinciauto_core.cli` with required env vars.
- **FR-3**: Offer documentation with copy-paste commands for alternate machines, including how to point at system or bundled ffmpeg.
- **FR-4**: Include automated smoke tests covering `--self-check` and Fake-TTS run against sample data (skippable if credentials missing).
- **FR-5**: Provide a PyInstaller spec that bundles Python runtime, dependencies, ffmpeg/ffprobe binaries, and CLI entry-point, emitting a macOS `.app` or standalone binary.
- **FR-6**: Generated bundle must run on at least macOS 13+ (Apple Silicon), pass a CLI self-check, and write outputs outside the bundle (~/Documents by default).
- **FR-7**: Supply a redistribution README summarizing licensing obligations (MIT project, ffmpeg LGPL notice, third-party licenses).

## Packaging & Infrastructure Requirements
- **PKG-1**: Create reproducible build commands (`make bundle`) producing artifacts in `dist/` plus checksums.
- **PKG-2**: Embed ffmpeg/ffprobe binaries in bundle with execute permissions; support override via env vars.
- **PKG-3**: Ensure PyInstaller artefact respects relative paths, temp directories (`$TMPDIR`), and caches under `~/Library/Application Support/davinciauto-cli`.
- **PKG-4**: Provide code-signing guidance, even if default build is ad-hoc; document notarization steps for future.
- **PKG-5**: Implement CI guard (GitHub Actions) that runs bootstrap + fake-tts smoke test on macOS runner.

## Documentation Requirements
- **DOC-1**: Publish `docs/CLI_SETUP.md` covering setup script usage, sample commands, troubleshooting.
- **DOC-2**: Publish `docs/CLI_BUNDLE.md` describing PyInstaller bundle usage, trust settings (Gatekeeper), and known limitations.
- **DOC-3**: Maintain change log section for CLI distribution updates (can reuse existing `PROJECT_INDEX.md` or new `docs/CLI_CHANGELOG.md`).

## Acceptance Criteria
- Running `make setup && make self-check` on a clean macOS VM finishes without manual intervention.
- `make bundle` produces a signed (ad-hoc acceptable) binary that runs `davinciauto_core.cli --self-check` successfully on a second machine without Python installed.
- Documentation reviewed for accuracy and stored under version control.
- Smoke test suite covers bootstrap script and bundle invocation in CI.
