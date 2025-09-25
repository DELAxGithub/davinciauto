# OrionEp1 Automation Handoff

_Last updated: 2025-09-17_

## Scope
- Azure Speech narration synthesis from dialogue Markdown/CSV
- Timeline CSV + FCP7 XML generation and sync
- ElevenLabs BGM/SE batch rendering and timeline integration
- Subtitle refresh and retiming aligned with narration
- Environment/configuration updates required to operate the pipeline

## Prerequisites
- Python 3.11 with project dependencies installed (`pip install -r requirements.txt`)
- `.env` populated from `.env.example` (ensure `ELEVENLABS_API_KEY`, Azure Speech keys, LLM keys as needed)
- Resolve 18+ available for final verification (manual step)

## Core Pipeline (codified CLI)
1. **Narration generation**
   ```bash
   python scripts/process_orionep2_short.py <script.txt> \
     --timeline-name OrionEp1_timeline \
     --prefix OrionEp1
   ```
   Outputs:
   - `projects/OrionEp1/サウンド類/Narration/*.mp3`
   - `projects/OrionEp1/exports/timelines/OrionEp1_timeline.csv`
   - `projects/OrionEp1/exports/timelines/OrionEp1_timeline.xml`

2. **Plan sync (timeline → BGM/SE plan)**
   ```bash
   python scripts/fit_bgm_plan_to_timeline.py \
     projects/OrionEp1/exports/timelines/OrionEp1_timeline.csv \
     projects/OrionEp1/inputs/bgm_se_plan.json \
     --out projects/OrionEp1/inputs/bgm_se_plan_synced.json
   ```
   - Injects `start_line/end_line`, `time_tc`, `offset_sec`, caps durations >30s.

3. **ElevenLabs BGM/SE rendering**
   ```bash
   PYTHONPATH=. python scripts/generate_bgm_se_from_plan.py \
     projects/OrionEp1/inputs/bgm_se_plan_synced.json
   ```
   - Re-run with `--only bgm` / `--only se` for partial refresh.
   - Outputs to `projects/OrionEp1/サウンド類/BGM` and `.../SE`.

4. **Timeline assembly (NA+BGM+SE)**
   ```bash
   PYTHONPATH=. python scripts/build_fcpx_with_bgm_se.py \
     projects/OrionEp1/exports/timelines/OrionEp1_timeline.csv \
     projects/OrionEp1/inputs/bgm_se_plan_synced.json \
     projects/OrionEp1/exports/timelines/OrionEp1_timeline_with_bgm.xml
   ```

5. **Subtitles**
   - Generate new SRT from CSV text:
     ```bash
     python scripts/make_srt_from_xml_and_csv.py \
       projects/OrionEp1/exports/timelines/OrionEp1_timeline_with_bgm.xml \
       projects/OrionEp1/exports/timelines/OrionEp1_timeline.csv
     ```
   - Retiming original subtitles to new audio:
     ```bash
     python scripts/retime_srt_with_timeline.py \
       projects/OrionEp1/exports/timelines/OrionEp1_timeline_with_bgm.xml \
       projects/OrionEp1/inputs/OrionEp1.srt \
       projects/OrionEp1/exports/subtitles/OrionEp1_retimed.srt
     ```

## Script Changes (Sept 2025)
- Added `scripts/fit_bgm_plan_to_timeline.py` to auto-sync plan JSON with timeline.
- Hardened `scripts/retime_srt_with_timeline.py`:
  - Filters to narration clips via `pathurl` check.
  - Proportional cue allocation without min-duration clipping.
- Introduced `.env.example` including ElevenLabs key placeholder.
- Standardised directory usage (`inputs/` for user-provided, `exports/` for generated).

## Generated Assets (current state)
- Timeline with mixes: `projects/OrionEp1/exports/timelines/OrionEp1_timeline_with_bgm.xml`
- BGM/SE stems: `projects/OrionEp1/サウンド類/BGM|SE`
- Subtitles:
  - Fresh auto-cut: `projects/OrionEp1/テロップ類/SRT/OrionEp1_Sub_follow.srt`
  - Retimed legacy: `projects/OrionEp1/exports/subtitles/OrionEp1_retimed.srt`

## Verification Checklist
1. Import `OrionEp1_timeline_with_bgm.xml` into Resolve → confirm track assignments (A1=NA, A2=BGM, A3=SE).
2. Spot-check ElevenLabs renders (long ambience cues are capped to 30s).
3. Review `OrionEp1_retimed.srt` in Resolve overlay.
4. Ensure `.env` contains valid keys before regenerating BGM/SE.

## Open Items / Next Steps
- Consider pipeline for video asset automation (scene placeholder creation, still imports).
- Evaluate replacing ElevenLabs with Azure Audio Content Creation for cost control.
- Add regression tests comparing SRT cue count vs narration clips to catch drift automatically.
- Package the above commands into a single orchestrator script or Makefile target for one-shot rebuilds.

## References
- `progress.md` — running changelog (updated 2025-09-17)
- `docs/ELEVENLABS_MCP_SETUP.md` — extended ElevenLabs integration notes
- `docs/CLI_SETUP_JA.md` — Japanese quickstart for CLI environment
