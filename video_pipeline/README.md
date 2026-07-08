# Delax Video Pipeline

Reusable video-production workflows shared across Orion, Platto, JAL, and
future VTR projects.

The first workflow is `narrated_vtr`: a conservative script-to-review-artifacts
path for narrated videos.

Use the thin phase runner for normal projects. It deliberately runs one phase at
a time, because client VTR work usually has review gates between script, TTS,
Resolve, picture edit, and render.

```bash
python3 -m video_pipeline.workflows.run_narrated_vtr \
  --config projects/jal/kumojo-shosai-pilot/project.yaml \
  script-review
```

Available phases:

- `script-review`
- `build-artifacts`
- `pronunciation-review`
- `tts`
- `recalc`
- `resolve-dry-run`
- `resolve-apply`
- `qc`
- `render-job-dry-run`
- `render-job`

There is intentionally no `all` phase.

```bash
python3 -m video_pipeline.workflows.narrated_vtr \
  --script projects/jal/kumojo-shosai-pilot/inputs/script.md \
  --project-dir projects/jal/kumojo-shosai-pilot \
  --project-id jal-kumojo-shosai-pilot \
  --title "雲上書斎｜パイロット版"
```

It writes:

- script review report
- common IR
- narration text
- Gemini TTS YAML
- draft SRT
- reviewable BGM cue plan
- non-mutating Resolve apply-plan stub

Resolve mutation and BGM placement are intentionally separate approval steps.

## Script Review Gate

Run this whenever the narration script changes:

```bash
python3 -m video_pipeline.workflows.run_narrated_vtr \
  --config projects/jal/kumojo-shosai-pilot/project.yaml \
  script-review
```

It writes `outputs/script_review/script_review.md`, plus section and long-line
CSVs. This is intentionally lightweight: it catches structure, length, fixed
phrases, and long TTS segments, but leaves editorial judgment to the script
review.

## Generate Narration

Run the pronunciation review before sending text to Gemini TTS:

```bash
python3 -m video_pipeline.workflows.review_tts_pronunciation \
  --yaml projects/jal/kumojo-shosai-pilot/outputs/tts/gemini_tts.yaml \
  --rules-csv projects/jal/kumojo-shosai-pilot/inputs/pronunciation_rules.csv
```

It writes `outputs/tts/gemini_tts.reviewed.yaml` and
`outputs/tts/pronunciation_review.csv`. Use the reviewed YAML for synthesis.

```bash
python3 -m video_pipeline.workflows.generate_gemini_tts \
  --yaml projects/jal/kumojo-shosai-pilot/outputs/tts/gemini_tts.reviewed.yaml \
  --out-dir projects/jal/kumojo-shosai-pilot/outputs/audio/narration \
  --project-id jal-kumojo-shosai-pilot
```

To regenerate only corrected lines:

```bash
python3 -m video_pipeline.workflows.generate_gemini_tts \
  --yaml projects/jal/kumojo-shosai-pilot/outputs/tts/gemini_tts.reviewed.yaml \
  --out-dir projects/jal/kumojo-shosai-pilot/outputs/audio/narration \
  --project-id jal-kumojo-shosai-pilot \
  --only-indices 1,15,26,31,33,34,42 \
  --force
```

Then recalculate real timing from generated audio:

```bash
python3 -m video_pipeline.workflows.recalculate_from_audio \
  --project-dir projects/jal/kumojo-shosai-pilot \
  --project-id jal-kumojo-shosai-pilot \
  --audio-dir projects/jal/kumojo-shosai-pilot/outputs/audio/narration
```

## Create Resolve Timeline

Use the generic Resolve applier through the guarded Resolve CLI. It creates
organized bins, imports generated narration/BGM/review docs, creates a new
timeline, places narration on A1, temp BGM on A4, names tracks, and adds
section markers aligned to actual narration timing.

Dry-run first:

```bash
python3 /Users/delaxpro/src/claude-config/skills/davinci-resolve/scripts/resolve_cli.py run-script \
  --script scripts/apply_narrated_vtr_timeline.py \
  --globals-json '{"PROJECT_DIR":"projects/jal/kumojo-shosai-pilot","EXPECTED_PROJECT":"JAL","TIMELINE_NAME":"JAL_雲上書斎_Pilot_v002","BIN_NAME":"JAL_雲上書斎_Pilot","APPLY":false}' \
  --apply
```

Apply after the dry-run is clean:

```bash
python3 /Users/delaxpro/src/claude-config/skills/davinci-resolve/scripts/resolve_cli.py run-script \
  --script scripts/apply_narrated_vtr_timeline.py \
  --globals-json '{"PROJECT_DIR":"projects/jal/kumojo-shosai-pilot","EXPECTED_PROJECT":"JAL","TIMELINE_NAME":"JAL_雲上書斎_Pilot_v002","BIN_NAME":"JAL_雲上書斎_Pilot","APPLY":true}' \
  --apply
```

Known manual gate: SRT files are generated and imported as review documents
when Resolve accepts them, but direct SRT-to-subtitle-track import failed in
the current Resolve scripting path. Import `outputs/subtitles/timecoded.srt`
manually until a reliable subtitle applier is added.

## After Manual Picture Edit

Once footage has been selected and placed by hand, generate a QC pack from the
open Resolve timeline:

```bash
python3 /Users/delaxpro/src/claude-config/skills/davinci-resolve/scripts/resolve_cli.py run-script \
  --script scripts/report_narrated_vtr_timeline.py \
  --globals-json '{"PROJECT_DIR":"projects/jal/kumojo-shosai-pilot","TIMELINE_NAME":"JAL_雲上書斎_Pilot_v001"}' \
  --apply
```

This writes:

- `outputs/qc/qc_report.md`
- `outputs/qc/qc_report.json`
- `outputs/qc/timeline_items.csv`
- `outputs/qc/resolve_asset_log.csv`
- `assets/asset_log.csv`

Prepare a review render queue job without starting the render:

```bash
python3 /Users/delaxpro/src/claude-config/skills/davinci-resolve/scripts/resolve_cli.py run-script \
  --script scripts/prepare_narrated_vtr_review_render.py \
  --globals-json '{"PROJECT_DIR":"projects/jal/kumojo-shosai-pilot","EXPECTED_PROJECT":"JAL","TIMELINE_NAME":"JAL_雲上書斎_Pilot_v001","CUSTOM_NAME":"JAL_雲上書斎_Pilot_v001_review","ADD_JOB":true}' \
  --apply
```

Rendering remains a manual approval gate.
