# Pipeline Scripts

This directory collects reusable automation scripts. Key entries:

- `orion_ep7_pipeline.py`: end-to-end TTS/timeline/SRT generator for Orion Episode 7 assets.
- `doc_to_davinci_ir.py`: shared Doc/CSV -> frame-based EditScript IR builder. This is the preferred entry for reusable editing automation.
- `apply_ep039_recalculated_na_timeline.py`: EP039 Doc-to-DaVinci experiment that rebuilds a final timeline by recalculating record TC from kept interview ranges plus NA WAV durations. See `docs/EP039_Doc_to_DaVinci_Recalculated_NA_Runbook.md`.
- `doc_ir_duration_report.py`: estimates script duration from IR before touching Resolve; use this for the Doc/CSV -> IR -> duration loop while the script is still changing.
- `platto_contract_to_block_ir.py`: converts a Platto contract CSV into block-level timeline IR. Consecutive `KEEP` rows become listening/editing blocks, and NA WAV durations are inserted into the same event sequence.
- `platto_contract_to_google_doc_table.py`: converts a Platto DaVinci contract CSV back into the 4-column Google Doc review table (`カット候補`, `Speaker Name`, `素材イン点&ナレーション`, `文字起こし`). Use `--na-position after-next-color-block` for the EP040 Doc-style order.
- `apply_platto_block_na_timeline.py`: DaVinci Resolve apply script for the block/NA IR. It duplicates the source timeline, replaces A1/A2 with talk blocks, places temporary NA on A3, applies clip colors, and adds markers. Run through `resolve_cli.py run-script`; start with `APPLY=false`.
- `platto_script_to_block_color_plan.py`: extracts SEG/source ranges and script color labels from Platto PDFs/text, producing a block-level color plan before fine cuts.
- `run_ep039_recalculated_na_pipeline.py`: short command wrapper for dry-run/apply of the EP039 recalculated-NA pipeline.
- `apply_ep039_noncompact_na_experiment.py`: EP039 diagnostic timeline that keeps source TC positions and places NA on A3 without compacting.
- `platto39_generate_na_audio.py`: generates or reuses Platto NA WAV files from `desired_timeline_ir`; `--prefer mac` uses local macOS speech for free provisional narration.
- `apply_jal_kumojo_timeline.py`: JAL pilot Resolve apply script. Keep JAL-specific names in `projects/jal/kumojo-shosai-pilot/project.yaml` and move reusable logic into shared modules as it stabilizes.

Architecture note: `davinciauto` is the shared engine. Program repositories
should keep business state and call these scripts through explicit profiles. See
`docs/Editing_Automation_Architecture.md`.

Call the Orion pipeline from the repo root:

```bash
python scripts/orion_ep7_pipeline.py
```

Remember to export `GOOGLE_APPLICATION_CREDENTIALS` and any voice override environment variables before running.
