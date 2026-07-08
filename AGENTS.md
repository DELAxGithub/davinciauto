# davinciauto Agents Guide

This repository is the shared video-editing automation engine for DaVinci
Resolve workflows. Keep client or program-specific business state in the
owning project repository, and keep reusable timeline/IR/Resolve automation
here.

## Recipe Table

| Task | Entry Point | Status | Last Verified |
|---|---|---:|---|
| Doc/CSV edit table to frame-based IR | `scripts/doc_to_davinci_ir.py` | active | 2026-06-28 |
| IR duration estimate before touching Resolve | `scripts/doc_ir_duration_report.py` | active | 2026-06-28 |
| Platto block + NA timeline generation | `scripts/platto_contract_to_block_ir.py` -> `scripts/apply_platto_block_na_timeline.py` | active | 2026-06-28 |
| EP039 recalculated NA reproduction | `scripts/run_ep039_recalculated_na_pipeline.py` | active, episode-specific | 2026-06-21 |
| JAL narrated VTR runner | `python3 -m video_pipeline.workflows.run_narrated_vtr` | active, project-profile based | 2026-07-08 |
| Legacy mini-VTR one-off pipeline | `minivt_pipeline/` / old docs | legacy | unknown |

## Canonical Routes

### Shared Doc to DaVinci Engine

Confidence: verified by recent Platto 39/40 and JAL pilot work.

Canonical flow:

```text
Google Doc / CSV / script table
  -> EditScript IR
  -> Timeline Plan IR
  -> Resolve apply script
  -> MCP or Resolve CLI readback report
```

Rules:

- Do not parse free-form headings as the machine contract. Tables and explicit
  tags are the contract.
- Convert timecode to frames once, at IR generation.
- Never overwrite an editor timeline. Generate a new timeline or a new plan.
- Use Resolve MCP/CLI for readback and verification. Use Resolve Python
  `AppendToTimeline` scripts for precise batch placement when MCP does not
  expose the needed operation.
- Always leave a report that separates `automatic`, `semi-automatic`, and
  `manual` work.

Evidence:

- `docs/Doc_to_DaVinci_Automation_Design.md`
- `docs/EP039_Doc_to_DaVinci_Recalculated_NA_Runbook.md`
- `docs/EP039_Platto_DaVinci_Handoff.md`
- `projects/jal/kumojo-shosai-pilot/project.yaml`

### Project Ownership Boundary

The engine belongs here. Project facts belong elsewhere.

- Platto episode state, guests, Google Docs, reports, BGM catalog decisions:
  `~/src/70_プラッと/platto-automation`
- JAL pilot inputs and per-project config:
  `projects/jal/kumojo-shosai-pilot/` until a dedicated JAL repository exists
- Generic reusable code:
  `scripts/`, `video_pipeline/`, and future `davinciauto` packages

When a workflow becomes reusable across two projects, move the reusable part
into this repository and leave only a profile/config in the project repo.

## Detailed Notes

### Preferred File Layout

```text
scripts/
  one-shot compatibility wrappers and Resolve apply entry points
video_pipeline/
  reusable narrated VTR workflow modules
projects/
  lightweight project profiles, inputs, and source-control-safe manifests
docs/
  runbooks, architecture, and verification notes
output/ and projects/*/*/outputs/
  generated artifacts; keep out of git unless explicitly curated
```

### Resolve Integration

Resolve MCP is valuable for inspection, validation, markers, and small
operations. Frame-precise bulk placement is still best handled by Resolve
Python scripts executed through the existing Resolve CLI or Resolve console.

Before applying:

1. Confirm the active Resolve project and target timeline.
2. Run dry-run mode when available.
3. Refuse to overwrite an existing generated timeline.
4. Apply into a new timeline.
5. Read back clip counts, track counts, start/end frames, and markers.

### Editing Contract

Use explicit table columns and tags:

- `KEEP`
- `CUT`
- `RESTORE`
- `MOVE_AFTER:<target>`
- `PRIORITY:A|B|C`
- `NOTE:`

Platto color-only interpretation is legacy and must be opt-in, for example
`--color-policy keep`. New CSVs should not silently treat color as KEEP/CUT.

## AI Involvement Levels

- Low: generate reports, inspect IR, summarize timeline state.
- Medium: build dry-run plans, duration estimates, review CSVs.
- High: create Resolve timelines only after dry-run and project/timeline checks.
- Manual required: editorial judgment, final picture edit, legal/factual review,
  final render start unless the project runbook says otherwise.

## Dormant or Legacy Areas

- Old mini-VTR docs still describe a narrow 8-minute educational video flow.
  Treat them as legacy unless the task explicitly references that workflow.
- `davinci-ai-commander` is a separate natural-language Resolve control product.
  Do not merge its product/UI concerns into this production engine.
- Generated media, renders, scratch PDFs, and temporary extraction files should
  stay ignored.

## Past Incidents

- EP039 initially happened from the wrong repository. The correct automation
  home for reusable DaVinci editing code is this repository.
- Platto-specific operational state should not be copied into generic scripts
  unless it is behind a named profile or explicit config.
- Directly mutating existing Resolve timelines makes recovery harder. Prefer new
  timelines and readback reports.
