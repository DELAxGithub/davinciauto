# Implementation Plan: GUI Launcher

## Phase 0 – Prep (0.5 day)
- Audit current CLI flags, environment variables, and log files.
- Identify bundle paths for ffmpeg/ffprobe to prefill launcher options.
- Draft user flow wireframes for Automator dialogs.

## Phase 1 – Automator/AppleScript Launcher (1 day)
1. Create `scripts/gui_launcher_run.sh` to wrap CLI execution (handles env, logging, error popups).
2. Build Automator app (`resources/DavinciAutoLauncher.app`) with dialogs for API key, script, output, run mode.
3. Add the launcher & helper script to PyInstaller spec / Makefile packaging.
4. Update docs (`docs/GUI_LAUNCHER.md`) explaining how to use the launcher.
5. Smoke test DMG (arm64/x86_64) ensuring two-click workflow works.

## Phase 2 – SwiftUI Lite Launcher (2–3 days, optional if time permits)
1. Add new Swift target (or reuse trimmed EditAutoApp) that focuses on setup/run tasks.
2. Implement tabs: Self-Check, API Keys, Run. Reuse `KeychainService`, `ProcessExec`.
3. Surface CLI logs in UI + export button.
4. Integrate codesign/notarization for the new app and ensure PyInstaller bundle still works (or ship Swift app separately).
5. Regression test: CLI bundle, Automator app, and Swift app all function and share the same helper script.

## Phase 3 – Documentation & Rollout (0.5 day)
- Update README/PROJECT_INDEX with launcher availability.
- Provide step-by-step “GUI導入手順” for production teams (linking to docs/GUI_LAUNCHER.md).
- Capture screenshots/gif for training deck.

## Acceptance Criteria
- Automator app included in DMG, double-click launches the wizard and runs CLI successfully.
- (If implemented) SwiftUI launcher saves API keys, runs self-check, and triggers CLI runs with progress feedback.
- CLI-only flow remains available; launcher references the same `ci/verify_bundle.sh` checks.
- Documentation published & reviewed by production stakeholders.

