# Progress Log

_Last updated: 2025-09-18_

## OrionEp2 Workstream
- ✅ Azure TTS narration flow confirmed from timeline CSV → FCPXML (`scripts/build_timeline_orionep2.py`, `scripts/csv_to_fcpx7_from_timeline.py`).
- ✅ Documentation refreshed for Azure Speech Service (README + PROJECT_INDEX).
- ⚠️ BGM/SE generation still depends on ElevenLabs (`scripts/generate_bgm_se_from_plan.py`, `scripts/master_bgm_from_plan.py`). Keep API key active until alternate provider is ready.
- ✅ Follow-up SRT workflow validated (`scripts/make_srt_from_xml_and_csv.py` with `OrionEp2_timeline_v1.*`).
- 🔄 Repository cleanup ongoing: only restore components needed for Ep2 delivery; leave archived extras untouched for now.

## OrionEp1 Automation
- ✅ Azureナレーション → タイムラインCSV → BGM/SE → FCPXML の完全パイプラインを再構築。
- ✅ `scripts/fit_bgm_plan_to_timeline.py` でタイムラインCSVから `bgm_se_plan.json` の時刻/行番号を自動同期。
- ✅ ElevenLabs BGM/SE を追加生成（長尺SEは30秒上限で自動トリム）し、`build_fcpx_with_bgm_se.py` で A1/A2/A3 XML を更新。
- ✅ 字幕更新ワークフローを整理：`make_srt_from_xml_and_csv.py` で新規字幕生成、`retime_srt_with_timeline.py` 改修で既存SRTを実尺に合わせて再タイミング。
- ✅ `.env.example` を追加し、ElevenLabsキーを含む環境変数テンプレートを整備。
- ✅ 入力/出力のディレクトリ運用を整理（`inputs/`=供給データ、`exports/`=生成結果）。

## Resolve Smart Tagging Toolkit
- ✅ `tools/resolve_auto_tagging/run_auto_tagging.py` に `--project`, `--limit`, `--batch`, `--merge-policy`, `--dry-run`, `--thumbnails`, `--log` を実装。Gemini 2.5 Pro ドライラン済み（20本バッチ）。
- ✅ `tools/resolve_auto_tagging/import_metadata.py` で `/Orion/data/tags_sanitized.csv` を upsert（append/replace/dry-run対応）。
- ✅ EP01–EP12 の image-cut seed CSV を整備（5–7タグ／行、Notesで台本出典）。
- ⚠️ Resolve 20.2 環境は Smart Bin API 非公開のため自動生成不可。マニュアル構築手順と intention/foundation CSV をテンプレート `.drp` 化して対応。
- ✅ `scripts/add_markers_from_csv.py` を追加し、タイムラインCSV + LLM出力CSVから Guide マーカー（コメント/タグ/メモとデュレーション付与）をFCPXMLへ自動挿入。

## Immediate Next Steps
1. Re-run BGM/SE generation for any new `bgm_se_plan.json` tweaks; master outputs with `scripts/master_bgm_from_plan.py`.
2. Package the refreshed narration + SRT + mastered audio into the Resolve project template and confirm import on Resolve 18+.
3. 手動で基礎/意図スマートビンをテンプレ `.drp` に組み込み、Power Bin 化。`import_metadata.py` + `run_auto_tagging.py` の運用手順を編集部へ引き継ぎ。
4. Decide on long-term replacement for ElevenLabs music/SFX (Azure Audio Content Creation or local library) before future episodes.

## Parking Lot
- Migrate `generate_bgm_se_from_plan.py` to optionally call Azure or local assets once a new provider is chosen.
- Add automated validation to compare narration CSV timings against generated SRT for drift detection.
- Update GUI tooling once core CLI scripts stabilize after the Azure switch.
