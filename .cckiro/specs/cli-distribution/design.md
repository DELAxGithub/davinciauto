# Design: CLI Distribution Readiness

## Overview
Deliver two parallel distribution channels:
1. **Developer-friendly CLI** – Python virtualenv + make targets that wrap existing `davinciauto_core.cli` entry points.
2. **Packaged CLI bundle** – PyInstaller-generated binary embedding Python runtime, dependencies, and ffmpeg/ffprobe for offline use.

## Components

### A. Repository bootstrap tooling
- **`Makefile` (or `justfile`)**
  - Targets: `setup`, `self-check`, `fake-tts`, `run`, `bundle`, `clean`.
  - Encapsulates python path, env var exports, default script/output paths, and provider selection.
- **`scripts/bootstrap_cli.sh`**
  - Detects Python 3.11 (via `pyenv`, `brew`, or system), creates `.venv`, installs editable project, and installs ffmpeg if absent (optionally prompt).
  - Emits instructions for exporting `DAVA_FFMPEG_PATH`/`DAVA_FFPROBE_PATH` if using system binaries.
- **Sample data**
  - Reuse existing `projects/OrionEp2/inputs/script_timed.md` or create trimmed sample script for smoke test to avoid large assets.

### B. Documentation
- `docs/CLI_SETUP.md`: Step-by-step instructions with screenshots/terminal snippets; highlight BYOK credentials, env vars, verifying outputs.
- `docs/CLI_BUNDLE.md`: Bundle usage, first-run Gatekeeper instructions (`xattr -d`), log locations, limitations (Fake-TTS only if no key, etc.).
- README badge linking to CLI docs.

### C. Testing
- `scripts/smoke_fake_tts.sh` triggered by `make smoke`.
- GitHub Actions workflow (`.github/workflows/cli.yaml`) running on `macos-latest` for bootstrap + smoke + PyInstaller build (artifact upload optional).
- Local test ensures pipeline writes to temporary workspace and cleans up.

### D. PyInstaller bundle
- **Spec file** (`pyinstaller/davinciauto_cli.spec`)
  - Entry: `davinciauto_core.cli:main` with console mode.
  - Includes `Resources/bin/ffmpeg`, `Resources/bin/ffprobe`, `davinciauto_core/prompts/*.jsonl` and other required data files.
  - Sets custom runtime hook to configure env vars (`PYTHONHOME`, `PYTHONPATH`, `DAVA_FFMPEG_PATH`, `DAVA_FFPROBE_PATH`).
  - Writes caches to `$HOME/Library/Application Support/davinciauto-cli`.
- **Bundle wrapper**
  - Optional: simple shell script `davinciauto-cli` that wraps binary and exposes help.
  - DMG creation via `scripts/package_dmg.sh` using `hdiutil` or `create-dmg`.
- **Signing**
  - Default ad-hoc sign using `codesign --force --sign -`.
  - Document Developer ID signing in `CLI_BUNDLE.md`.

### E. Configuration management
- `.env.example` updates referencing BYOK keys and concurrency.
- Provide `config/cli_defaults.yaml` if we want to store default provider/voice mapping outside code (optional stretch; can reuse existing config modules).

### F. Logging & Diagnostics
- Ensure CLI default logs to stderr with timestamps.
- Add `--diagnostics` flag or `make diag` target to dump env info minus secrets.

## Data Flow
1. **Bootstrap**: `make setup` → `.venv` creation → install editable `davinciauto-core` → confirm ffmpeg paths.
2. **Execution**: `make run SCRIPT=... OUTPUT=... PROVIDER=elevenlabs` → wraps CLI call with env and arguments.
3. **Packaging**: `make bundle` → PyInstaller spec → output `dist/davinciauto-cli` → optional DMG packaging.
4. **Runtime**: Packaged binary executed on target Mac → env hooks set `DAVA_FFMPEG_PATH` to bundled binary → CLI runs Self-Check → user provides script & output path via command-line options.

## Alternatives Considered
- **Homebrew formula** – rejected for now (requires hosting tap, harder to embed ffmpeg).
- **Conda distribution** – heavier dependency, not default on macOS.
- **Nuitka packaging** – slower, more complex; PyInstaller sufficient for CLI.

## Open Questions / Follow-ups
- Should we ship both console binary and `.app` wrapper? (Binary likely enough; revisit if Gatekeeper friction is high.)
- How to handle concurrency/performance defaults for machines without high CPU? Possibly default to 1; allow override via CLI flags.
- Should bundle include Fake-TTS assets or rely solely on CLI flag? Current plan is to keep CLI identical to repo version; no extra assets needed.

