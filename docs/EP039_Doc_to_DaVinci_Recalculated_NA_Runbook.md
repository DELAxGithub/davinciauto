# EP039 Doc to DaVinci Recalculated NA Runbook

更新日: 2026-06-21

## 目的

EP039で成功した「カット済み会話 + ナレーションWAV」を、次回以降も同じ手順でDaVinci Resolve上に再生成するための実行手順。

このランブックで作るのは、元TCへ戻す非詰め版ではなく、完成タイムライン上のTCを再計算した版。

```text
KEEP尺 + NA尺 + KEEP尺 + NA尺 ...
```

を上から足し算し、A1/A2に会話、A3にNAを配置する。

## 正本

- Resolve project: `プラっと編集0518`
- 元タイムライン: `039編集_0619`
- 既知の成功カット範囲: `039編集_0619 自動カット済み`
- 出力タイムライン例: `039編集_0619_NA込み再計算`
- IR: `output/ep039_auto_cut_2/desired_timeline_ir_24fps.json`
- NA WAV: `output/ep039_auto_cut_2/na_wav/NA1.wav` ... `NA13.wav`
- 実行スクリプト: `scripts/apply_ep039_recalculated_na_timeline.py`
- 簡易入口: `scripts/run_ep039_recalculated_na_pipeline.py`

重要: `039編集_0619 自動カット済み` のA1を、206個の残し範囲の正本として読む。新しい321配置IRは使わない。

## 期待値

2026-06-21時点の成功値:

- keep ranges: `206`
- keep frames: `50996`
- NA items: `13`
- total plan items: `219`
- final duration frames: `56833`
- final duration: 約 `39分28秒`
- final end TC: `01:39:28:01`
- A1 clip count: `206`
- A2 clip count: `206`
- A3 clip count: `13`

生成済み成果物:

- `output/ep039_recalculated_na/apply_report.json`
- `output/ep039_recalculated_na/tc_mapping.csv`

## 事前確認

台本がまだ固まっていない段階では、DaVinciを触らず、先に尺レポートを回す。

```bash
python3 scripts/doc_ir_duration_report.py \
  output/ep039_auto_cut_2/desired_timeline_ir_24fps.json \
  --na-dir output/ep039_auto_cut_2/na_wav \
  --target-minutes 45 \
  --out-json output/ep039_script_duration_loop/duration_report.json \
  --out-report output/ep039_script_duration_loop/duration_report.md \
  --out-csv output/ep039_script_duration_loop/duration_events.csv
```

この段階で短すぎる/長すぎる場合は、ResolveタイムラインではなくDoc/CSVの `KEEP` / `RESTORE` / `CUT_IF_OVER` / `PRIORITY` を直す。

色分け台本/PDFがある場合は、細かいカットへ進む前にブロック色計画を作る。

```bash
python3 scripts/platto_script_to_block_color_plan.py \
  '/Users/delaxpro/Downloads/プラっと#39.pdf' \
  --fps 24 \
  --out-json output/ep039_block_color/block_color_plan.json \
  --out-csv output/ep039_block_color/block_color_plan.csv \
  --out-report output/ep039_block_color/block_color_plan.md
```

EP039 PDFでは19ブロックを抽出済み。これはフィラーまで厳密に切る前の、SEG単位の荒編/色分け確認に使う。

DaVinci Resolveを起動し、project `プラっと編集0518` を開く。

```bash
cd /Users/delaxpro/src/20_tools/davinciauto

python3 /Users/delaxpro/src/claude-config/skills/davinci-resolve/scripts/resolve_cli.py status

python3 /Users/delaxpro/src/claude-config/skills/davinci-resolve/scripts/resolve_cli.py timeline-info \
  --timeline '039編集_0619'

python3 /Users/delaxpro/src/claude-config/skills/davinci-resolve/scripts/resolve_cli.py timeline-info \
  --timeline '039編集_0619 自動カット済み'
```

期待:

- `039編集_0619`: fps `24`, start frame `86400`, end frame `208176`
- `039編集_0619 自動カット済み`: fps `24`, start frame `86400`, end frame `137396`

## NA WAV生成

NA WAVがまだ無い場合だけ実行する。すでに存在するWAVは再生成せず、manifestに `existing` として記録される。

```bash
python3 scripts/platto39_generate_na_audio.py \
  output/ep039_auto_cut_2/desired_timeline_ir_24fps.json \
  --out-dir output/ep039_auto_cut_2/na_wav \
  --prefer auto
```

期待:

- `output/ep039_auto_cut_2/na_wav/NA1.wav` ... `NA13.wav`
- `output/ep039_auto_cut_2/na_wav/na_audio_manifest.json`

## Dry Run

既存の同名タイムラインがある場合は失敗する。再実行時は `OUTPUT_TIMELINE` を変える。

通常はこちらを使う。

```bash
python3 scripts/run_ep039_recalculated_na_pipeline.py \
  --output-timeline '039編集_0619_NA込み再計算_test'
```

内部で実行される詳細コマンド:

```bash
python3 /Users/delaxpro/src/claude-config/skills/davinci-resolve/scripts/resolve_cli.py run-script \
  --script /Users/delaxpro/src/20_tools/davinciauto/scripts/apply_ep039_recalculated_na_timeline.py \
  --globals-json '{"SOURCE_TIMELINE":"039編集_0619","REFERENCE_TIMELINE":"039編集_0619 自動カット済み","OUTPUT_TIMELINE":"039編集_0619_NA込み再計算_test","IR_JSON":"/Users/delaxpro/src/20_tools/davinciauto/output/ep039_auto_cut_2/desired_timeline_ir_24fps.json","NA_DIR":"/Users/delaxpro/src/20_tools/davinciauto/output/ep039_auto_cut_2/na_wav","APPLY":false}' \
  --apply
```

dry-runではResolveにタイムラインを作らない。`final_duration_frames`, `final_end_tc`, `first_plan_items`, `last_plan_items` を確認する。

## Apply

`OUTPUT_TIMELINE` は既存名と重複させない。重複した場合、スクリプトは上書きせず停止する。

通常はこちらを使う。

```bash
python3 scripts/run_ep039_recalculated_na_pipeline.py \
  --apply \
  --output-timeline '039編集_0619_NA込み再計算_test'
```

内部で実行される詳細コマンド:

```bash
mkdir -p output/ep039_recalculated_na

python3 /Users/delaxpro/src/claude-config/skills/davinci-resolve/scripts/resolve_cli.py run-script \
  --script /Users/delaxpro/src/20_tools/davinciauto/scripts/apply_ep039_recalculated_na_timeline.py \
  --globals-json '{"SOURCE_TIMELINE":"039編集_0619","REFERENCE_TIMELINE":"039編集_0619 自動カット済み","OUTPUT_TIMELINE":"039編集_0619_NA込み再計算_test","IR_JSON":"/Users/delaxpro/src/20_tools/davinciauto/output/ep039_auto_cut_2/desired_timeline_ir_24fps.json","NA_DIR":"/Users/delaxpro/src/20_tools/davinciauto/output/ep039_auto_cut_2/na_wav","REPORT_JSON":"/Users/delaxpro/src/20_tools/davinciauto/output/ep039_recalculated_na/apply_report.json","MAPPING_CSV":"/Users/delaxpro/src/20_tools/davinciauto/output/ep039_recalculated_na/tc_mapping.csv","APPLY":true}' \
  --apply
```

## 検証

```bash
python3 /Users/delaxpro/src/claude-config/skills/davinci-resolve/scripts/resolve_cli.py timeline-info \
  --timeline '039編集_0619_NA込み再計算_test'
```

Resolve MCPで確認する場合:

- timeline info: A1 `206`, A2 `206`, A3 `13`
- end frame: `143233` 付近
- start TC: `01:00:00:00`

`tc_mapping.csv` で、各KEEP/NAの完成タイムライン上の位置を確認できる。

## 既存実験タイムライン

- `039編集_0619_自動カット２回目`: 321配置 + NA後付けで失敗寄り。比較用。
- `039編集_0619_自動カット２回目_cutonly`: 既知成功版の複製。A1/A2のみ206。
- `039編集_0619_非詰めNA実験`: 元TC位置へKEEP/NAを置いた診断版。NAが隙間から溢れる箇所を確認するためのもの。
- `039編集_0619_NA込み再計算`: 現時点の本命。KEEP/NAを足し算して完成TCを再計算。

## 失敗時に見る場所

- `output timeline already exists`: `OUTPUT_TIMELINE` を新しい名前にする。
- `NA clip not found`: `NA_DIR` に `NA1.wav` ... `NA13.wav` があるか確認する。
- `source WAV clips not found`: Resolve Media Pool内に `260605_001_Tr1.WAV` と `260605_001_Tr2.WAV` があるか確認する。
- `keep_ranges` が206でない: `REFERENCE_TIMELINE` が `039編集_0619 自動カット済み` になっているか確認する。
- final durationが大きく違う: NA WAVの再生成で読み上げ尺が変わっていないか、`na_audio_manifest.json` を確認する。

## EP40へ持ち越す設計

このEP039実験で採用する方針:

- `source TC`: 元素材のどこを使うか。
- `record TC`: 完成タイムライン上のどこに置くか。
- record TCは、KEEP/RESTORE/NAを並べたdesired-state IRから機械的に足し算する。
- Resolveでは既存タイムラインを直接直さず、必ず別タイムラインを生成する。
- 生成後に `apply_report.json` と `tc_mapping.csv` を残す。
