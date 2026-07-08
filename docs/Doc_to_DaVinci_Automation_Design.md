# Doc to DaVinci Automation Design

更新日: 2026-06-28

## 目的

EP40以降のプラっと編集で、Google Doc / CSVの編集指示をDaVinci Resolveへできるだけ自動反映するための設計メモ。

主題はDaVinci AI CommanderのUIではなく、`davinciauto`側の制作パイプラインとして、Doc/CSVからResolve向けの編集状態を生成すること。

## 基本方針

- V0では既存Resolveタイムラインへの直接reconcileはしない。
- V0の正入力は、Google Docからエクスポートまたは取得済みのCSVとする。
- Google Doc本文の自然文見出しは機械読み取り対象にしない。
- Doc/CSVの表だけを自動反映の契約にする。
- timecodeからframeへの変換はIR生成時に1回だけ行う。
- Resolveへ反映する場合は必ず別タイムラインまたは別生成物を作る。
- 実行後は、できたこと/できないことを限界レポートとして残す。
- 番組尺の目標は、トーク部分だけでなくNAを含めた完成尺で管理する。EP40時点では50分を基準にする。
- `KEEP` 行をそのまま1行1クリップとして切らない。連続する `KEEP` 行は、色・TC連続性・NA挿入位置を見てブロック化し、まず聴きやすい荒編を作る。

## Doc / CSV 契約

EP39形式のGoogle Doc表を基本契約にする。

Google Docを書く側の詳しい運用ルールは `docs/Platto_Google_Doc_Authoring_Guide.md` を参照する。この設計書は、書かれたDoc/CSVをどうIR化してResolveへ渡すかに焦点を置く。

必須列:

- `編集指示`
- `Speaker Name`
- `イン点`
- `アウト点`
- `文字起こし`

CSVに存在する場合だけ追加ヒントとして扱う列:

- `色選択`

`色選択` は、色あり行を残し候補、色なし行を台本外または落とす候補として扱うための補助情報であり、Google Doc本体の必須列にはしない。

ただし、未編集CSVでは `色選択` を編集判断として使わない。編集指示が空の行は `SOURCE` として扱い、素材台帳/確認マーカーだけを生成する。過去のEP39実験を再現する場合だけ、明示的に `--color-policy keep` を指定して、色あり行を `KEEP`、色なし行を `CUT` として読む。

## 編集指示タグ

既存の日本語指示を正規化しつつ、将来は `編集指示` 列に以下の機械タグを許可する。

- `KEEP`: 残す
- `CUT`: 落とす
- `RESTORE`: 復活候補
- `MOVE_AFTER:<section_or_timecode>`: 指定位置の後ろへ移動
- `PRIORITY:A|B|C`: 残し/復活の優先度
- `NOTE:`: 人間向け補足。配置ロジックには使わない

自然文だけの見出しや段落は、人間向けメモとして残してよいが、自動反映の入力契約には含めない。

## desired_timeline_ir

Doc/CSVから直接Resolveを操作せず、まず `desired_timeline_ir` を生成する。

概念フィールド:

- `doc_row_id`: Doc/CSV行に由来する安定ID
- `action`: `SOURCE`, `KEEP`, `CUT`, `RESTORE`, `MOVE`, `NOTE` などの正規化済み操作
- `automation_classification`: `自動反映可能`, `半自動`, `手作業必須`
- `priority`: `A`, `B`, `C` または未指定
- `source_in_frame`: 元素材上の開始frame
- `source_out_frame`: 元素材上の終了frame
- `record_start_frame`: 生成先タイムライン上の開始frame
- `duration_frames`: 配置尺
- `tracks`: 対象トラック。例: `A1`, `A2`
- `speaker`: `Speaker Name`
- `transcript`: `文字起こし`
- `notes`: 人間向け補足
- `issues`: 行単位の警告

IRではframeを唯一の内部時間単位にする。秒やtimecodeは入力/表示用に留める。

V0のJSONには、全行の `entries` に加えて `placement_plan` と `marker_plan` を含める。`placement_plan` は自動配置可能な `KEEP` / `RESTORE` 行だけを含み、`marker_plan` はsource frameを持つ行をResolveマーカー候補として含める。`SOURCE` は配置しない。未編集CSVをResolveに反映する場合は、黄色マーカーで素材行を見える化するところまでに止める。

### block_timeline_ir

EP40以降の荒編では、行単位IRをそのままResolveへ置く前に `block_timeline_ir` を作る。

目的:

- フィラーや短い相づちまで細かく切らず、会話の流れを保ったまま使い所を確認する。
- CSVの `色選択` を、ブロック色分けとしてタイムライン上で見える化する。
- NAを後付けではなく同じイベント列へ入れ、`KEEP_BLOCK + NA + KEEP_BLOCK ...` の足し算でrecord TCを再計算する。
- 台本修正中は、DaVinciを触る前に尺の増減を把握できるようにする。

概念フィールド:

- `event_id`: `B001`, `NA1` などの安定ID
- `event_type`: `KEEP_BLOCK` または `NA`
- `source_in_frame` / `source_out_frame`: 元素材上の範囲。NAでは空。
- `record_start_frame`: 生成先タイムライン上の開始frame
- `duration_frames`: 配置尺
- `source_rows`: ブロックに含めたDoc/CSV行ID
- `color_hint` / `resolve_color`: CSV色とResolve用の近似クリップ色
- `speaker` / `transcript_preview`: 人間が確認するための要約
- `na_audio_path`: 仮NA WAVのパス

ブロック化の基本ルール:

- 連続する `KEEP` 行は同じブロックにまとめる。
- `CUT`, `NOTE`, `NA` が来たらブロックを閉じる。
- `色選択` が変わった場合は、見える化しやすいように別ブロックにする。
- イン/アウトTCが不連続な場合は、別ブロックにする。
- NAの仮音声は無料・ローカルのmacOS `say` で作ってよい。目的は品質ではなく、尺と挿入位置の確認。

## Palmierから採用する設計原則

Palmier Proのコードや実装細部は持ち込まない。採用するのは以下の設計原則のみ。

- 操作前に現在状態を読む。
- 内部時間をframeに統一する。
- AIや自動化に渡す操作面を小さく、厳密にする。
- 再実行時に同じ範囲を二重配置しないよう、安定IDやprefixを持つ。
- 実行結果を読み返して検証する。

Palmierは自前エディタなのでタイムライン状態を完全所有できる。一方でResolveは外部API越しに操作するため、V0では既存タイムラインへの直接clear/placeや差分reconcileを前提にしない。

詳細な棚卸しは `docs/Palmier_MCP_Capability_Audit.md` を参照。EP40 V0へ反映するのは、read-before-write、frame契約、安定IR、batch placement前提の新規タイムライン生成、限界レポートに限定する。

## EP40 V0 実験フロー

EP40素材が来たら、最初の実験フローを以下に固定する。

1. Google Doc表をCSV化する。
2. `scripts/doc_to_davinci_ir.py` でCSVから `desired_timeline_ir` を生成する。
3. IR生成時にtimecodeをframeへ変換する。
4. `scripts/doc_ir_duration_report.py` で、DaVinciに触る前に想定尺を出す。目標はNA込み50分を基準にする。
5. 想定尺が目標から外れている場合は、Google Doc/CSVへ戻って `RESTORE` / `CUT_IF_OVER` / `PRIORITY` を直す。
6. 尺が近づくまで、Doc/CSV → IR → 尺レポートをループする。
7. 色分け台本/PDFがある場合は、`scripts/platto_script_to_block_color_plan.py` でSEG単位の `block_color_plan` を作る。
8. 台本が固まってきたら、`scripts/platto_contract_to_block_ir.py` で `KEEP` 行をブロック化し、NA込みのrecord TCを再計算する。
9. `scripts/apply_platto_block_na_timeline.py` をResolve経由で実行し、まずブロック単位の荒編/色分けタイムラインを作る。
10. ブロック構成を聴いて確認してから、必要箇所だけ行単位の細かいカットへ進む。
11. Resolveへ反映する場合は、必ず別タイムライン名で作る。
12. 実行後に限界レポートを残す。

限界レポートでは各項目を以下に分類する。

- `自動反映可能`
- `半自動`
- `手作業必須`

実行例:

```bash
python3 scripts/doc_to_davinci_ir.py \
  /path/to/ep40_export.csv \
  --fps 24 \
  --out-json output/ep40/desired_timeline_ir.json \
  --out-report output/ep40/doc_to_davinci_report.md \
  --out-edit-template output/ep40/edit_instruction_template.csv
```

未編集の文字起こしCSVから始める場合、この時点では `SOURCE` 行だけが出る。`edit_instruction_template.csv` の `編集指示` 列へ `KEEP` / `CUT` / `RESTORE` などを入れてから、あらためてIRを生成する。

台本が固まる前は、Resolveではなく尺レポートを回す。

```bash
python3 scripts/doc_ir_duration_report.py \
  output/ep40/desired_timeline_ir.json \
  --na-dir output/ep40/na_wav \
  --target-minutes 50 \
  --out-json output/ep40/duration_report.json \
  --out-report output/ep40/duration_report.md \
  --out-csv output/ep40/duration_events.csv
```

NA WAVがまだ無い場合は `--na-dir` を省略できる。その場合、NAは文字数から仮尺を見積もる。

尺レポートで見るもの:

- `KEEP` / `RESTORE` / `NA` の合計尺
- targetに対して短いか長いか
- 復活候補の優先度別尺
- オーバー時に落とせる `CUT_IF_OVER` / 低優先度候補

この段階ではDaVinciを触らない。DaVinciは、台本尺が成立した後の聴感確認と微調整に使う。

色分け台本/PDFがある場合は、行単位の精密カットへ進む前にブロック色計画を作る。

```bash
python3 scripts/platto_script_to_block_color_plan.py \
  /path/to/platto_script.pdf \
  --fps 24 \
  --out-json output/ep40/block_color_plan.json \
  --out-csv output/ep40/block_color_plan.csv \
  --out-report output/ep40/block_color_plan.md
```

この `block_color_plan` は、SEG単位の荒編とタイムライン色分けに使う。目的は、フィラーや言い淀みまでチクチク切る前に、番組の構造、復活範囲、色分け台本との対応を見える化すること。

V0の推奨順:

1. 台本尺計算
2. SEG/ブロック色分け
3. ブロック単位の荒編
4. 聴感確認
5. 必要な箇所だけ細かいカット

既存のResolveスクリプト `Colorize_Timeline_Clips.py` はクリップを順番に色付けする簡易ツール。今後は `block_color_plan` の `source_in/out` と `resolve_color` を使い、SEG単位で作られたクリップへ色を付ける方向に拡張する。

EP40で採用したブロック荒編の実行例:

```bash
python3 scripts/platto39_generate_na_audio.py \
  output/ep40/desired_timeline_ir.json \
  --out-dir output/ep40/na_wav \
  --prefer mac

python3 scripts/platto_contract_to_block_ir.py \
  /path/to/EP040_davinci_contract.csv \
  --fps 24 \
  --na-dir output/ep40/na_wav \
  --out-json output/ep40/block_timeline_ir.json \
  --out-report output/ep40/block_timeline_ir.md
```

Resolve反映は `resolve_cli.py run-script` 経由で行う。必ず `SOURCE_TIMELINE` と別の `OUTPUT_TIMELINE` を指定し、最初は `APPLY=false` でdry-runする。

```bash
python3 /Users/delaxpro/src/claude-config/skills/davinci-resolve/scripts/resolve_cli.py run-script \
  --script /Users/delaxpro/src/20_tools/davinciauto/scripts/apply_platto_block_na_timeline.py \
  --globals-json '{"SOURCE_TIMELINE":"040_オリジナル","OUTPUT_TIMELINE":"040_自動編集_ブロックNA_0628","BLOCK_IR_JSON":"output/ep40/block_timeline_ir.json","NA_DIR":"output/ep40/na_wav","APPLY":false}' \
  --apply
```

この荒編はA1/A2にトークブロック、A3に仮NA、各ブロックにクリップ色とマーカーを置く。映像の精密な切り直しはV1以降で、まずは音声・尺・構成確認を優先する。

Resolveを触る直前には、IRからdry-run apply planを作る。

```bash
python3 scripts/doc_ir_to_resolve_plan.py \
  output/ep40/desired_timeline_ir.json \
  --source-timeline "EP40 original" \
  --output-timeline "EP40 doc auto v0" \
  --out-json output/ep40/resolve_apply_plan.json \
  --out-report output/ep40/resolve_apply_plan.md
```

`resolve_apply_plan.json` はResolveを変更しない。次のapply実装へ渡す、複製タイムライン名、マーカー候補、配置候補、安全フラグを持つ最終レビュー用成果物。

すでに別の実験タイムラインを作ってある場合は、`--mode target-existing` を使う。このモードは元タイムラインを複製せず、指定済みの別タイムラインにマーカーだけを置く検証に使う。

```bash
python3 scripts/doc_ir_to_resolve_plan.py \
  output/ep40/desired_timeline_ir.json \
  --source-timeline "EP40 original" \
  --output-timeline "EP40 doc marker experiment" \
  --mode target-existing \
  --out-json output/ep40/resolve_apply_plan.json \
  --out-report output/ep40/resolve_apply_plan.md
```

さらに際まで進める場合は、guarded apply入口でdry-run確認する。

```bash
python3 scripts/apply_doc_resolve_plan.py \
  output/ep40/resolve_apply_plan.json
```

このコマンドもResolveを変更しない。現時点では `place_source_range` と generated namespace clear は未実装として検出し、`apply_ready: false` を返す。

実Resolveへ接続する場合は、DaVinci Resolve起動、対象project/timeline確認後に、`resolve_cli.py run-script` 経由で `APPLY=true` を渡す。ただし、source range配置の実装が入るまではmarker-only検証に限定する。

```bash
python3 /Users/delaxpro/src/claude-config/skills/davinci-resolve/scripts/resolve_cli.py run-script \
  --script /Users/delaxpro/src/20_tools/davinciauto/scripts/apply_doc_resolve_plan.py \
  --globals-json '{"PLAN_JSON":"output/ep40/resolve_apply_plan.json","APPLY":false}'
```

## V1以降の検証対象

以下はV0では実装前提にしない。

- 既存Resolveタイムラインへの差分reconcile
- 任意trackの正確なclear region
- linked A1/A2の完全同期カット
- ripple / 非ripple編集のAPI差吸収
- 既存編集済みタイムラインへの安全な再適用
- テキスト、字幕、ナレ移動の完全自動化
- transcript-driven cut
- Resolveからのvisual inspection
- PDF/Docの色分け台本から、Resolve上の既存単一クリップを自動分割してSEGごとに着色する処理
- ブロック荒編に合わせた映像クリップの安全な再配置

## EP39からの学び

EP39では、Doc由来マーカー、Red範囲の非リップル削除、CSV色あり範囲の残し、隙間詰めまで実施した。

その結果、35分版を直接直すより、元タイムコードを保った入力からIRを作り直し、別タイムラインとして再生成する方が安全だと分かった。EP40ではこの方針を初期設計にする。

2026-06-20の追加検証では、未編集CSVを `SOURCE` として読み、`039編集_0619_palmier実験` に495個の黄色マーカーだけを反映した。カット/配置は行わず、Doc整理前の見える化としては安全に成立した。

2026-06-21の追加検証では、ナレーションを後付けで元TC位置に置く方式ではなく、`source TC` と `record TC` を明示的に分ける方式が有効だと分かった。

- `source TC`: 元素材のどこを使うか。
- `record TC`: 完成タイムライン上のどこに置くか。

成功した流れは、既知の成功カット範囲206個を正本にし、NA WAV 13本を同じイベント列へ入れ、`KEEP尺 + NA尺 + KEEP尺 ...` を上から足し算してrecord TCを再計算する方法。

検証タイムライン:

- `039編集_0619_NA込み再計算`

成功値:

- A1/A2: 各206 clips
- A3: 13 clips
- total plan items: 219
- final duration: 56833 frames, 約39分28秒
- final end TC: `01:39:28:01`

EP40 V0では、NA/字幕/補足音声も「後付けレイヤー」ではなく、desired-state IRのイベント列へ入れてからrecord TCを再計算する方針を採用する。

再実行手順は `docs/EP039_Doc_to_DaVinci_Recalculated_NA_Runbook.md` を参照。

## EP40実行結果

2026-06-28に、EP40の自動編集用CSVからブロック荒編を生成した。

入力:

- CSV: `EP040_davinci_contract - EP040_davinci_contract.csv.csv`
- Source timeline: `040_オリジナル`
- Output timeline: `040_自動編集_ブロックNA_0628`
- NA: macOS `say` 生成の仮WAV

結果:

- CSV行数: 1395
- `KEEP` 行: 1222
- `CUT` 行: 158
- `NOTE` 行: 15
- `KEEP` ブロック: 33
- NA: 15
- markers: 48
- A1/A2配置: 各33 blocks
- A3配置: 15 NA clips
- clip colors: 81 clips
- IR予定尺: `01:07:04:08`
- Resolve読戻し尺: last audio `01:06:52:02`, timeline end `01:06:53:17`

50分尺に対しては約17分長い。次の台本ループでは、DaVinci上で細かく切る前にCSV/Docへ戻り、復活候補や削除候補を調整してから再生成する。

IR予定尺とResolve読戻し尺には約12秒の差が出た。仮NAのメディア長、Append時の端数、Resolve APIの読み返し差分が絡むため、今後は `apply_platto_block_na_timeline.py` 実行後に `inspect_resolve_timeline_audio.py` で読戻し、予定尺との差をレポートに残す。
