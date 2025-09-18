# Progress Log

_Last updated: 2025-09-16_

## OrionEp2 Workstream
- ✅ Azure TTS narration flow confirmed from timeline CSV → FCPXML (`scripts/build_timeline_orionep2.py`, `scripts/csv_to_fcpx7_from_timeline.py`).
- ✅ Documentation refreshed for Azure Speech Service (README + PROJECT_INDEX).
- ⚠️ BGM/SE generation still depends on ElevenLabs (`scripts/generate_bgm_se_from_plan.py`, `scripts/master_bgm_from_plan.py`). Keep API key active until alternate provider is ready.
- ✅ Follow-up SRT workflow validated (`scripts/make_srt_from_xml_and_csv.py` with `OrionEp2_timeline_v1.*`).
- 🔄 Repository cleanup ongoing: only restore components needed for Ep2 delivery; leave archived extras untouched for now.

## Immediate Next Steps
1. Re-run BGM/SE generation for any new `bgm_se_plan.json` tweaks; master outputs with `scripts/master_bgm_from_plan.py`.
2. Package the refreshed narration + SRT + mastered audio into the Resolve project template and confirm import on Resolve 18+.
3. Decide on long-term replacement for ElevenLabs music/SFX (Azure Audio Content Creation or local library) before future episodes.

## Parking Lot
- Migrate `generate_bgm_se_from_plan.py` to optionally call Azure or local assets once a new provider is chosen.
- Add automated validation to compare narration CSV timings against generated SRT for drift detection.
- Update GUI tooling once core CLI scripts stabilize after the Azure switch.

