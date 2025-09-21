# Implementation Plan: mac-app-store-readiness

## Phase 0 – Repository Preparation
- [ ] Audit current repo to identify core pipeline modules (`minivt_pipeline`, `backend`) and experiments/tools slated for exclusion from the shipping bundle.
- [ ] Extract pipeline logic into new Python package `davinciauto_core` with `run_pipeline(config)` entry and shared utilities (voice mapping, manifests, exporters, caching).
- [ ] Produce `pyproject.toml` for `davinciauto_core`; add scripts for separate arm64/x86_64 builds fused via `delocate-fuse` (macOS). Document Linux use of `auditwheel` only for internal CI, not MAS build.
- [ ] Add CI grep to flag dynamic-code pathways (`uvicorn`, `flask`, `exec`, `importlib.reload`, `subprocess .*pip`, etc.) and ensure they are pruned from shipping package.

## Phase 1 – SwiftUI Shell & Bootstrap
- [ ] Scaffold Xcode project `DavinciAutoApp` with SwiftUI lifecycle and hardened runtime entitlements (`network.client`, `files.user-selected.read-write`).
- [ ] Implement `bootstrapPython()` setting `PYTHONHOME`, `PYTHONPATH` (Resources/python/site-packages only), `PYTHONDONTWRITEBYTECODE=1`, `PYTHONPYCACHEPREFIX=<Container>/Library/Caches/pyc`, `XDG_CACHE_HOME=<Container>/Library/Caches`, and `LC_ALL=en_US_POSIX`; call `PythonLibrary.useLibrary(<embedded>/Python)` before any PythonKit import.
- [ ] Add unit test verifying bootstrap runs prior to PythonKit usage and that `.pyc` files appear in sandbox cache, not bundle.

## Phase 2 – Configuration & Keychain
- [ ] Implement `ConfigurationStore` with persisted settings in `Application Support/.../appconfig/` plus BYOK messaging displayed in onboarding and settings.
- [ ] Implement `KeychainCredentialStore` for provider credentials (add/remove/test connection) including explicit delete buttons, irreversible deletion warnings, and BYOK reminder.
- [ ] Build onboarding flow UI to collect provider choice, API keys, voice preset selection, workflow target, and surface BYOK payment clarification.

## Phase 3 – Voice & Provider Abstractions
- [ ] Define JSON schema for abstract voice presets mapping to provider IDs (`{"voice":"NarratorA","providers":{"elevenlabs":"...","azure":"..."}}`). Warn in UI if mapping missing for active provider.
- [ ] Implement provider adapters (ElevenLabs, Azure) that normalize text (trim, collapse whitespace, normalize newlines) before hash generation and respect segmentation rules.
- [ ] Expose segmentation policy (e.g., 1 line = 1 segment) as configuration to keep cache keys stable.

## Phase 4 – Bookmark & File Access
- [ ] Implement `BookmarkManager` handling folder selection, security-scoped bookmarks, `isStale` detection, and automatic re-authorization prompts when stale.
- [ ] Update pipeline job creation to pass bookmark-resolved paths with `startAccessing`/`stopAccessing` lifecycle management.
- [ ] Add CI/runtime guard ensuring writes occur only in sandbox container or bookmarked folders; writing into `.app` causes test failure.

## Phase 5 – Pipeline Execution Bridge
- [ ] Implement `PipelineBridge` protocol and `PythonKitBridge` concrete class that serializes `PipelineJob` JSON (provider, voices, target_nle, frame_rate, retry policy, manifest paths, parallelism).
- [ ] Stream stdout JSONL events (schema: `type`, `segment_id`, `progress`, `message`, `retry_after`, `remaining_requests`, etc.), ignoring unknown keys. UI displays retry/backoff info and allows cancellation.
- [ ] Implement cancellation handling: UI stop button cancels Python task, terminates spawned processes (ffmpeg), and ensures Python runner halts after current segment.
- [ ] Add concurrency knob for parallel TTS generation with automatic backoff when rate limits trigger.

## Phase 6 – Manifest & Resumable Generation
- [ ] Implement manifest writer/reader in Python storing SHA-256 hashes composed of provider, voice, language, normalized text, sample_rate, template_version, frame_rate.
- [ ] Cache directory structure under `Application Support/.../cache/<project>/`; dedupe segments via manifest lookup. Changes in template or frame_rate prompt full regeneration warning.
- [ ] Provide Swift-side controls to clear cache/manifest and force rebuild when desired.

## Phase 7 – NLE Templates & Export
- [ ] Package Resolve templates (FCPXML) and Premiere guidance (FCPXML + README conversion instructions) under Resources with `template_version` metadata.
- [ ] Implement exporter modules generating 48 kHz WAV, UTF-8 (BOM-less) SRT with optional frame-boundary snapping, and FCPXML with fixed version; run lightweight XML schema validation.
- [ ] Validate outputs import successfully in DaVinci Resolve; follow README conversion steps to confirm Premiere workflow.

## Phase 8 – Diagnostics & Logging
- [ ] Implement structured logging in Swift & Python (JSONL) stored under sandbox `Logs/`.
- [ ] Build `MaskingEngine` using centralized pattern list (`api_key`, `authorization`, `bearer`, `token`, case-insensitive) and apply to all diagnostics content.
- [ ] Create diagnostics UI flow with summary preview (file count, size, categories), default-off option to include input scripts, user confirmation, and zip generation with reveal option.

## Phase 9 – Build & CI Pipeline
- [ ] Set up CI jobs for building arm64/x86_64 wheels and fusing via `delocate-fuse`; verify `.so/.dylib` dependencies with `otool -L` to ensure sanctioned `@rpath`.
- [ ] Automate FFmpeg universal build (LGPL configuration), ensure executable bit, codesign, and include license text.
- [ ] Add CI checks: bundle size guard (≤400 MB) with offender report, `codesign --verify --strict --deep -v`, `spctl -a -vvv`, Privacy manifest schema validation, Required Reason API grep, ATS exception detection, dynamic-code keyword scan.
- [ ] Script notarization dry run and artifact archival.

## Phase 10 – Documentation & Packaging
- [ ] Draft in-app help covering BYOK billing, Keychain management, permissions, network failure guidance (IPv6/proxy/retry messaging), and diagnostics instructions.
- [ ] Author `Resources/templates/premiere/README.md` with step-by-step conversion guidance and supported versions; include limitations.
- [ ] Implement in-app licenses panel referencing FFmpeg and other third-party notices.
- [ ] Prepare App Store metadata checklist (privacy responses, demo credentials, support contact).

## Phase 11 – QA & Submission Prep
- [ ] Execute end-to-end smoke tests on both Apple Silicon and Intel Macs; verify outputs (audio, SRT, timeline) match across architectures.
- [ ] Test cancellation/restart flow ensuring reruns generate only missing segments and no double billing.
- [ ] Validate offline launch (no downloads on first run) and sandbox entitlements via `spctl`, proxy/IPv6 scenarios, and absence of local HTTP listeners.
- [ ] Run App Review rehearsal: demo API keys, Resolve-only walkthrough, Premiere README path.
- [ ] Compile final release candidate `.app`, notarize, and prep for App Store submission.

## Definition of Done (overall checks)
- Local HTTP servers absent; app operates with `network.client` entitlement only.
- No writes to `.app`; bytecode/caches stay within container or bookmarked folders.
- Identical inputs + settings produce identical outputs; diff detected via hash check.
- Interrupted runs can resume and process only outstanding segments.
- Resolve import succeeds; Premiere conversion succeeds following bundled README.
- App launches and completes first workflow without runtime downloads.
- Bundle size ≤400 MB at submission build.


## Phase 12 – Post-Implementation Archival
- [ ] Catalogue modules/scripts/assets no longer used in the MAS build (e.g., experimental GUI steps, obsolete backend services).
- [ ] Move retained-but-historic items into `archives/` (or dedicated branch) with README notes on purpose and last-known compatibility.
- [ ] Purge remaining unused assets from the main repository, updating packaging manifests and CI to exclude them.
- [ ] Update documentation (PROJECT_INDEX.md, README) to reflect the lean bundle and point to archives for legacy tooling.
- [ ] Run final `git clean` / dependency audit to confirm no orphaned files linger in the shipping tree.

