# Requirements: mac-app-store-readiness

## Background
- Current repo `davinciauto` bundles Python pipelines, FastAPI backend, HTML/Tk GUI steps, experiments, and tooling around DaVinci Resolve.
- Goal is to rework the distribution so it can ship as a Mac App Store product with a streamlined package and user-selectable workflow options.

## Known Pitfalls & Mitigations
1. **Local HTTP servers trigger `network.server` entitlement requests** – avoid FastAPI localhost listeners in production builds; prefer in-process calls or XPC/CLI bridges.
2. **Dynamic dependency downloads violate App Store 2.5.2** – all Python deps, runtimes, and media tools must ship inside the bundle; no runtime `pip install` or updater.
3. **Sandbox file access limitations** – rely on `files.user-selected.read-write` plus security-scoped bookmarks for output destinations; prompt user via open/save panels.
4. **Premiere export mismatch** – deliver either (a) dedicated Premiere-compatible templates or (b) clear guidance/tooling that converts Resolve/FCPXML output for Premiere users.
5. **Automation entitlements escalate review risk** – initial release should avoid Apple Events automation; focus on file-based handoff instead of controlling Resolve/Premiere directly.
6. **Bundled binaries must be signed and license-compliant** – ship LGPL-friendly `ffmpeg`, sign Python/FFmpeg with the app’s TeamID, and include license notices.
7. **Credential storage must be secure** – store API keys in Keychain, never plain text.
8. **Privacy assets are mandatory even with no data collection** – provide a `PrivacyInfo.xcprivacy` manifest describing BYOK-only usage and confirm third-party SDK declarations.
9. **Required Reason APIs can slip in unintentionally** – audit the codebase to avoid restricted API usage; if unavoidable, document rationale in the privacy manifest before submission.
10. **App Transport Security exceptions invite rejection** – keep ATS at the secure default (HTTPS/TLS only) and avoid custom exceptions.
11. **User-supplied scripts can be flagged as dynamic code** – disable arbitrary plugin/script ingestion for the initial MAS build.

## Objectives
1. Produce a macOS-friendly application bundle structure suitable for App Store submission.
2. Allow end users to configure preferred AI providers (e.g. ElevenLabs vs Azure vs future providers).
3. Allow user-level control over voice assignment strategy and editing target (DaVinci Resolve vs Adobe Premiere) without editing code.
4. Reduce the shipped payload to the minimum necessary for primary workflows while keeping development/experiment assets out of the distributable bundle.
5. Preserve existing pipeline capabilities (script → audio → subtitles → timeline export) within the curated package.

## Functional Requirements
- **FR-1**: Provide a configuration surface (UI and/or guided setup) where users can choose the default AI/TTS provider, supply credentials, and switch providers later; reflect BYOK (user-supplied API keys) messaging throughout onboarding/help.
- **FR-2**: Provide a configuration mechanism for voice casting policies (e.g. mapping NA/dialogue roles to voices, rotation rules, or preset selection) editable without touching Python files.
- **FR-3**: Provide a workflow chooser covering at least DaVinci Resolve and Adobe Premiere export variants; the selection must affect output folder structure and generated assets, including any required conversion guidance for Premiere.
- **FR-4**: Deliver a GUI entry point (macOS-native or embedded WebView) that wraps the pipeline and presents the customization options above without relying on a localhost HTTP server.
- **FR-5**: Ensure pipeline execution still produces audio, subtitles, and project assets compatible with the chosen NLE target while running inside the sandbox (no forbidden network-server entitlement), while exposing network retry/proxy-friendly UX and rate-limit status where possible.
- **FR-6**: Provide an opt-in diagnostic export (masked logs/config) that users can share with support; sensitive tokens must be redacted automatically.

## Packaging & Infrastructure Requirements
- **PKG-1**: Define which components are bundled with the Mac App Store build (Python runtime, dependencies, assets) and which are excluded (experiments, unused scripts, raw datasets); ensure the bundle works offline except for external API calls and meets the ≤400 MB size target.
- **PKG-2**: Establish an internal module layout that isolates the distributable core from optional tooling and facilitates code signing/notarization.
- **PKG-3**: Provide an in-process or XPC-based launch flow for Python execution that keeps all IPC within sandbox-allowed mechanisms and documents required entitlements (`network.client`, `files.user-selected.read-write`). Plan for eventual migration between same-process and XPC execution without large-scale refactors.
- **PKG-4**: Document and, if possible, automate the build pipeline from source checkout to signed universal (`arm64` + `x86_64`) `.app` ready for App Store submission, including third-party binary signing, hardened runtime, and license packaging.
- **PKG-5**: Ensure all runtime caches, temp files, and generated assets live under the sandbox container (`~/Library/Containers/.../Data/{Library,Caches,Application Support}`); never write into the `.app` bundle post-signing.

## Compliance / UX Requirements
- **CX-1**: Offer clear credential storage guidance consistent with macOS security (Keychain usage) and expose controls to delete stored keys; document BYOK payments (no in-app purchase, billing handled by providers).
- **CX-2**: Ensure the app discloses required permissions (network, file access) and handles failure cases gracefully, including retry timing, remaining quota messaging when available, and IPv6/proxy-aware diagnostics.
- **CX-3**: Provide user-facing documentation/help accessible from the app describing configuration steps, supported providers, export destinations, Premiere conversion instructions (with README in `Resources/templates/premiere/`), and contact/support options.
- **CX-4**: Maintain a populated Privacy Manifest covering data collection statements and Required Reason API answers even when data collection is none; keep metadata aligned with BYOK usage.

## Out of Scope (for this spec)
- Refactoring experimental tools unrelated to the core audio/subtitle pipeline unless they interfere with packaging.
- Implementing new AI provider integrations beyond those already available; focus is on configuration plumbing.
- Creating Windows/Linux installers.

