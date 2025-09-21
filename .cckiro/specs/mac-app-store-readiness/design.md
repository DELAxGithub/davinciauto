# Design: mac-app-store-readiness

## 1. High-Level Architecture
- **SwiftUI main app (`DavinciAutoApp`)** provides onboarding, configuration, execution, status, and diagnostics UI.
- **Embedded Python core** (packaged wheel under `Contents/Resources/python`) exposes CLI entry `davinciauto-run` plus a thin C-bridge module callable via PythonKit.
- **Execution bridge layer** (Swift `PipelineRunner`) orchestrates pipeline runs by invoking Python in-process through PythonKit while setting explicit CPython environment variables (`PYTHONHOME`, `PYTHONPATH`, `PYTHONDONTWRITEBYTECODE`, `PYTHONPYCACHEPREFIX`, `XDG_CACHE_HOME`). The bridge conforms to a `PipelineBridge` protocol so an XPC runner can replace it later without UI changes.
- **Configuration service (`ConfigurationStore`)** handles user preferences, API credentials (Keychain), security-scoped bookmarks (with staleness checks), workflow presets, frame-rate/template settings, and provider/voice mappings.
- **Output manager (`AssetExporter`)** prepares Resolve/Premiere exports inside sandbox directories, mirrors to user-selected project folders via bookmarks, records manifest metadata for resumable generation, and enforces UTF-8/48 kHz defaults.
- **Diagnostic manager** collects masked logs, manifests, and environment summaries into a user-triggered zip stored in the sandbox container; users must confirm contents before export.

## 2. Module Structure
```
DavinciAuto.app
└─ Contents
   ├─ MacOS/
   │   └─ DavinciAuto (SwiftUI binary)
   ├─ Frameworks/
   │   └─ Python.framework (signed, universal)
   └─ Resources/
      ├─ python/
      │   ├─ site-packages/ (vendored deps, bytecode disabled)
      │   └─ cli/davinciauto-run (Python entry)
      ├─ bin/ffmpeg (LGPL build, executable, signed)
      ├─ templates/
      │   ├─ resolve/
      │   └─ premiere/
      │       └─ README.md (conversion guidance, supported versions, limitations)
      ├─ config-schemas/
      │   └─ pipeline_config.json
      ├─ licenses/
      │   ├─ FFmpeg.LICENSE
      │   └─ ThirdPartyNotices.txt
      ├─ diagnostics/
      │   └─ masking_patterns.json
      └─ PrivacyInfo.xcprivacy
```
- `davinciauto_core` reorganized to expose `run_pipeline(config: dict)` plus modules for caching, manifest handling, voice resolution, and NLE-specific exporters.

## 3. Bootstrapping & Environment Control
```swift
func bootstrapPython() throws {
    guard let resPath = Bundle.main.resourceURL?.path,
          let fwRoot = Bundle.main.privateFrameworksPath?.appending("/Python.framework/Versions/3.11") else {
        throw BootstrapError.missingPythonBundle
    }
    let sitePackages = resPath + "/python/site-packages"
    let caches = FileManager.default.urls(for: .cachesDirectory, in: .userDomainMask).first!
    setenv("PYTHONHOME", fwRoot, 1)
    setenv("PYTHONPATH", sitePackages, 1)
    setenv("PYTHONDONTWRITEBYTECODE", "1", 1)
    setenv("PYTHONPYCACHEPREFIX", caches.appendingPathComponent("pyc").path, 1)
    setenv("XDG_CACHE_HOME", caches.appendingPathComponent("xdg").path, 1)
    PythonLibrary.useLibrary(fwRoot + "/Python")
}
```
- Prevents `.pyc` creation inside Resources.
- Python libraries direct caches to sandbox container.
- Bootstrap executes before any Python import, avoiding accidental linkage to system Python.

## 4. Data & Configuration Flow
1. **Onboarding** collects BYOK API keys, stored via Keychain (`KeychainCredentialStore`) with delete/refresh controls; help text clarifies third-party billing.
2. User selects project/export folder; `BookmarkManager` captures security-scoped bookmark, resolves it with staleness detection (`bookmarkDataIsStale`), and triggers re-selection if needed.
3. Voice casting presets stored as JSON under sandbox `Application Support/com.davinciauto/appconfig/voices.json`, using abstract voice names resolved per provider; warn when mapping missing.
4. Workflow selection toggles Resolve vs Premiere output via `PipelineConfig` (contains `target_nle`, `frame_rate`, `template_version`).
5. Runtime caches/logs/manifest data stored under sandbox `Application Support/com.davinciauto/runtime/` and `Caches/com.davinciauto/`; `.app` bundle remains read-only post-signing.
6. Templates/README remain immutable resources.

## 5. Voice & Provider Abstraction
```json
{
  "voice": "NarratorA",
  "providers": {
    "elevenlabs": "Mv8AjrYZCBkdsmDHNwcB",
    "azure": "ja-JP-NanamiNeural"
  },
  "fallback": "elevenlabs"
}
```
- Provider adapters resolve abstract voices; if selected provider lacks mapping, UI prompts for assignment before run.
- Caching keys incorporate `provider`, `voice`, and text hash to prevent double billing.

## 6. Pipeline Execution & Resumability
- Swift builds `PipelineJob` JSON including hashed segments, provider config, voice mapping, NLE target, frame rate, and retry strategy (with backoff).
- `PipelineRunner` resolves bookmarks, stages inputs in sandbox temp, and invokes Python entry (`davinciauto_core.run_pipeline`) via PythonKit.
- Python runner consults per-job `manifest.json` (stored under `Application Support/com.davinciauto/cache/<project>/manifest.json`) to skip already-generated segments and update entries after each successful generation.
- Outputs created under sandbox staging directories (`runtime/<job-id>/audio`, `.../subtitles`) with 48 kHz WAV and UTF-8 SRT; once complete, they copy to bookmark destination using `FileCoordinator` to maintain sandbox rules; manifest writes final status.
- Progress events emitted as JSON lines (`state`, `segment_id`, `percent_complete`, `retry_after`, `remaining_requests`, `message`); Swift stream parser updates UI and communicates rate-limit wait times.
- On failure, Python emits `error` event with classification; Swift logs masked details and stops provider billing by ensuring no partial segment re-generation without manifest update.

## 7. Diagnostics & Masking
- Diagnostics package includes: `logs/*.log`, `pipeline.stdout.jsonl`, `manifest.json`, `environment.json` (macOS version, app version, entitlements). Input scripts are excluded unless user opts in per export dialog.
- `MaskingEngine` reads `diagnostics/masking_patterns.json` defining regexes for API keys, Bearer tokens, Azure keys, etc.; all log lines pass through before packaging.
- UI displays summary (files, total size, included categories) and warns about content before generating zip.

## 8. Security & Compliance
- Privacy manifest lists BYOK usage, no data collection, and third-party SDK declarations; maintained via CI schema validation.
- Required Reason API audit keeps restricted APIs out; CI grep ensures no unwanted frameworks (e.g., `NSAppleScript`).
- ATS stays default (HTTPS/TLS). Proxy/IPv6 failures present human-readable instructions and allow retry.
- No dynamic plugin/script ingestion; only bundled Python executed.
- App size target ≤400 MB enforced by CI check that sums bundle resources.

## 9. Build & Signing Pipeline
1. Package `davinciauto_core` as universal wheel (arm64/x86_64) using `delocate`/`auditwheel`-equivalent; remove unused compiled modules where possible.
2. Build FFmpeg (LGPL options) for both architectures, unify via `lipo`, place under `Resources/bin/ffmpeg`, ensure `chmod +x` and codesign with TeamID.
3. Run `otool -L` on all `.dylib`, `.so`, `ffmpeg` to confirm `@rpath` -> `@executable_path/../Frameworks` or similar sanctioned paths.
4. Codesign Python.framework, site-packages binaries, ffmpeg, and main app with hardened runtime; CI runs `codesign --verify --strict --deep -v`.
5. Xcode build script copies resources, privacy manifest, templates, README, diagnostics patterns.
6. CI ensures `PrivacyInfo.xcprivacy` valid, ATS untouched, environment bootstrap present, and manifest/regression tests pass.
7. Archive via `xcodebuild`, export, notarize with notarytool, staple ticket; maintain checklist for App Store submission metadata (BYOK messaging, support instructions, demo credentials if required).

## 10. Extensibility Plan
- `PipelineBridge` protocol abstracts execution location; implement `PythonKitBridge` now, `PipelineXPCBridge` later without modifying UI.
- Provider adapters implement `ProviderConfig` protocol enabling new TTS providers.
- Voice presets stored in JSON schema allow import/export; future community sharing possible.
- Template metadata supports new NLE outputs (`template_version` keys) with compatibility matrix.

## 11. Task Breakdown (initial sprints)
- **T1**: Implement Python bootstrap/environment setup.
- **T2**: Build BookmarkManager with staleness detection and reauthorization flow.
- **T3**: Implement segment caching & `manifest.json` handling for resumable generation.
- **T4**: Define template/version metadata and enforce Resolve/Premiere export differences.
- **T5**: Diagnostics zip + MaskingEngine + export UI.
- **T6**: Extend CI to run `otool`, `codesign --verify`, privacy manifest schema checks, bundle size guard.

## 12. Acceptance Criteria Summary
- **FR-1**: Keychain-backed provider setup with add/edit/delete, connection test, BYOK messaging.
- **FR-2**: Voice presets editable via UI/JSON, provider switch respects abstract voice mapping.
- **FR-3**: Resolve/Premiere workflows produce distinct output layouts and FCPXML/Premiere templates validated in respective NLEs.
- **FR-4**: Full pipeline executes without local HTTP server; all IPC in-process.
- **FR-5**: Outputs include 48 kHz WAV, UTF-8 SRT (ms precision), timeline XML; imports succeed in target NLE using provided README guidance.
- **PKG-1/2**: `.app` self-contained; experiments/unneeded assets excluded; size ≤400 MB.
- **PKG-3**: Operates with `network.client` + `files.user-selected.read-write` entitlements only; writes confined to container or bookmarked folders.
- **PKG-4**: CI produces signed universal build, verifies codesign/otool, optional notarization dry run.
- **CX-1/2/3/4**: Help covers Keychain management, permissions, BYOK billing; network errors show retries/remaining quota; Premiere README packaged; Privacy manifest populated.

