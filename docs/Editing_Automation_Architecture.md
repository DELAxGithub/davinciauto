# Editing Automation Architecture

更新日: 2026-07-08

## Decision

`davinciauto` is the shared editing automation engine.

Program and client repositories should call it through explicit project
profiles instead of copying pipeline code. Platto, JAL, Orion, and future
projects can keep their own source documents and editorial rules while sharing
the same IR, planning, Resolve application, and verification layers.

## Repository Roles

| Layer | Owner | Examples |
|---|---|---|
| Shared engine | `~/src/20_tools/davinciauto` | IR generation, duration reports, Resolve apply scripts, readback reports |
| Program operations | Program repo | Platto episode metadata, Google Doc IDs, guest/report/BGM business state |
| Project profile | Program repo or `projects/<client>/<id>/` | Resolve project name, timeline names, fps, track layout, input script paths |
| Generated artifacts | ignored output folders or Dropbox reports | renders, WAV/MP3, extracted PDFs, screenshot sets |

## Contract

The engine should not consume an entire free-form editing script directly.
Instead it consumes a small contract:

```text
source document
  -> explicit table / CSV / profile
  -> EditScript IR
  -> Timeline Plan IR
  -> Resolve apply
  -> readback verification
```

The table/profile contract should include:

- source in/out timecode or generated narration timing
- speaker or role
- transcript or narration text
- edit action such as `KEEP`, `CUT`, `RESTORE`, or `NOTE`
- optional priority and move hints
- project profile with fps, Resolve project, timeline, track mapping, and bins

## Why IR First

The IR is the boundary that keeps this from becoming a pile of one-off scripts.

- Editorial documents can change without touching Resolve.
- Duration can be checked before changing a timeline.
- Platto and JAL can share planning/reporting logic.
- Resolve application can stay conservative: dry-run first, new timeline only,
  readback after apply.

## Resolve Control Boundary

Use both Resolve MCP and Resolve Python, but give them different jobs.

| Job | Preferred Tool |
|---|---|
| Project/timeline inspection | Resolve MCP or Resolve CLI |
| Markers and light metadata | Resolve MCP or Resolve CLI |
| Frame-precise batch placement | Resolve Python script via Resolve CLI/Console |
| Verification after apply | Resolve MCP or Resolve CLI |

This matches the current practical limit: MCP is excellent for readback and
small operations, while precise `AppendToTimeline` placement is still safer in
Resolve Python.

## Current Profiles

### Platto

Platto should keep operational state in `~/src/70_プラッと/platto-automation`.
Reusable code lives here.

Known reusable pieces:

- `scripts/doc_to_davinci_ir.py`
- `scripts/doc_ir_duration_report.py`
- `scripts/platto_contract_to_block_ir.py`
- `scripts/apply_platto_block_na_timeline.py`
- `scripts/platto_edited_audio_to_doc_csv.py`

Episode-specific runbooks remain useful as evidence, but new episodes should
move toward a profile/config entry rather than another dedicated apply script.

### JAL

The JAL pilot already uses a project profile:

- `projects/jal/kumojo-shosai-pilot/project.yaml`
- `video_pipeline.workflows.run_narrated_vtr`
- `scripts/apply_jal_kumojo_timeline.py`

The next cleanup step is to make the JAL apply path use the same generic
Timeline Plan IR shape as Platto where possible.

## Migration Plan

1. Keep existing episode scripts as compatibility wrappers.
2. Extract shared parsing, timecode, IR validation, and report writing into
   package modules.
3. Replace `platto_*` and `jal_*` hard-coded values with project profiles.
4. Add one command that accepts `--config <project.yaml>` and phase names.
5. Keep generated outputs ignored unless the file is a curated source input,
   manifest, or runbook.

## Commit Boundary

For now, commit:

- docs and runbooks that identify the active route
- reusable scripts and profile-safe inputs
- lightweight project manifests

Do not commit:

- generated audio/video
- temporary PDF/image extraction files
- Resolve render outputs
- secrets or API tokens
