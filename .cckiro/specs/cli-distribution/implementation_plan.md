# Implementation Plan: CLI Distribution Readiness

## Phase 0 – Prep & Inventory (0.5 day)
- Audit current CLI entry point, sample data, and ffmpeg binaries.
- Confirm Python 3.11 availability on dev machine (`python3.11 --version`).
- List required data files for PyInstaller (prompts, config). Document in issue tracker.

## Phase 1 – Developer CLI Tooling (1–1.5 days)
1. Create `Makefile` with targets: `setup`, `self-check`, `fake-tts`, `run`, `smoke`, `bundle`, `clean`.
2. Add `scripts/bootstrap_cli.sh` for guided setup (detect Python, create venv, install editable package).
3. Introduce `.env.example` updates and clarify ffmpeg env vars.
4. Write `docs/CLI_SETUP.md` describing the workflow.
5. Implement smoke test script (`scripts/smoke_fake_tts.sh`) using Fake-TTS and sample script.
6. Update `PROJECT_INDEX.md` or dedicated changelog with CLI section.

## Phase 2 – Automation & CI (1 day)
1. Add GitHub Actions workflow (`.github/workflows/cli.yaml`) running on macOS runner:
   - Checkout, `make setup`, `make self-check`, `make fake-tts` (with Fake-TTS flag).
   - Cache venv to speed up subsequent runs.
2. If creds absent, ensure tests skip but still report clear message.
3. Publish workflow badge in README.

## Phase 3 – PyInstaller Bundle (2 days)
1. Install PyInstaller as dev dependency (`requirements-dev.txt` or extras).
2. Craft `pyinstaller/davinciauto_cli.spec` referencing CLI entry point, data files, and binaries.
3. Write runtime hook to set env vars and App Support cache paths.
4. Add `scripts/package_dmg.sh` for DMG creation; integrate into `make bundle`.
5. Ensure generated bundle includes licenses (copy from `Resources/licenses/*`).
6. Test bundle on local machine (with existing Python uninstalled/ignored) – run `dist/davinciauto-cli --self-check` and Fake-TTS pipeline.

## Phase 4 – Cross-machine Verification (0.5–1 day)
1. Copy bundle to secondary Mac (or macOS VM) with no repo checkout; run self-check and fake-tts.
2. Capture issues (missing dylibs, quarantine flags) and update docs/scripts accordingly.
3. Optionally sign with Developer ID to confirm Gatekeeper flow; document steps.

## Phase 5 – Documentation & Wrap-up (0.5 day)
1. Finalize `docs/CLI_BUNDLE.md` with usage instructions, Gatekeeper guidance, BYOK notes.
2. Update README and `PROJECT_INDEX.md` links.
3. Gather acceptance evidence (screenshots/logs) and attach to issues.
4. Close loop with team on outstanding questions (binary vs .app, future GUI integration).

## Deliverables Checklist
- [ ] Makefile + bootstrap script committed.
- [ ] CLI setup doc and bundle doc in `docs/`.
- [ ] Smoke test script + GitHub Actions workflow.
- [ ] PyInstaller spec + DMG packaging script.
- [ ] Verified bundle running on second machine.
- [ ] License notices reviewed and updated.

## Risks & Mitigations
- **PyInstaller missing binaries** → use runtime hook tests and verbose logs; keep list of hidden imports/data files in spec.
- **ffmpeg licensing** → bundle LGPL build, include license copy, allow replacement via env vars.
- **CI macOS runner limitations** → cache PyInstaller outputs, fallback to local testing if runtime > job limits.
- **Gatekeeper blocking ad-hoc signed bundle** → document `xattr -d` workaround; plan for Developer ID signing later.

