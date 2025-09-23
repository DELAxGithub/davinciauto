# Requirements: GUI Launcher Initiative

## Background
- Non-technical production staff needs an easier entry point than the CLI.
- Current distribution provides `davinciauto-cli` bundles with command-line usage.
- Goal is to reduce friction by offering a simple GUI or launcher that wraps the existing CLI without large rewrites.

## Objectives
1. Provide a guided interface for three core actions:
   - Configure API keys (BYOK) safely.
   - Select input script and output folder.
   - Run Fake-TTS test / real pipeline.
2. Minimise engineering effort: reuse CLI behaviour; avoid duplicating pipeline logic.
3. Ensure the solution fits into existing release packaging (PyInstaller bundle + DMG).

## Constraints
- Must run on macOS 13/14 (Apple silicon & Intel).
- No additional network services or background daemons.
- Prefer native macOS UX (SwiftUI) but Automator/AppleScript launcher acceptable for first milestone.
- Keychain storage already exists in Swift code; should be reused if SwiftUI route selected.
- Launcher must surface logs/self-check results so support can diagnose issues.

## User Scenarios
- **First-time setup:** Staff downloads DMG, opens launcher, pastes API key, runs self-check + fake run.
- **Daily use:** Staff double-clicks launcher, selects script/output, runs pipeline, reviews summary.
- **Support case:** Staff exports diagnostic info (self-check JSON + run log) for engineers.

## Success Criteria
- Produce a launcher artifact that ships alongside CLI bundle and allows core workflow without manual terminal usage.
- Documentation updated with GUI-specific instructions.
- Self-check/fake-run reachable in ≤3 clicks.
- No additional install steps beyond current DMG copy.

