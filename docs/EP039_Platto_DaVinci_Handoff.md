# EP039 プラっと DaVinci 自動編集 引き継ぎ

更新日: 2026-06-20  
対象リポジトリ: `/Users/delaxpro/src/20_tools/davinciauto`  
注意: 直前まで誤って `/Users/delaxpro/src/10_apps/delax100daysworkout` を作業ディレクトリにしていたが、今回のDaVinci自動化の引き継ぎ先はこの `davinciauto` リポジトリ。

## 目的

EP039「ゴールの先に世界が見える＠高輪ゲートウェイ」の編集台本をもとに、DaVinci Resolve上で以下を自動化する。

- Google Doc / CSV / 台本から残し・カット範囲を解釈する
- Resolveタイムラインにマーカーを打つ
- A1/A2の2本のWAVを同じ範囲でカットする
- 必要に応じて隙間あり版・隙間詰め版を作る
- v3台本で「切りすぎた35分版」から約45分版へ戻す

## 現在の状況

### Google Doc

- 対象Doc: <https://docs.google.com/document/d/12xy1YRVMr39F1P7Pa8bH71gQZjOhfJDW9JE-E0YxWIw/edit?tab=t.0>
- タイトル: `プラっと#39`
- もともと450行・5列の編集指示テーブルが入っていた
  - `編集指示`
  - `Speaker Name`
  - `イン点`
  - `アウト点`
  - `文字起こし`
- Chrome経由でDoc先頭にv3編集台本を追加済み
- 既存の文字起こし・編集指示テーブルは削除せず、v3台本の下に残している
- Google Drive connectorの直接書き込みはスコープ不足で失敗したため、Chrome経由で貼り込んだ

### 添付されたv3台本

- 元ファイル:
  - `/Users/delaxpro/.codex/attachments/345ddc28-e370-40ae-b9fe-b40b1075b87b/pasted-text.txt`
- 見出し:
  - `EP039「ゴールの先に世界が見える＠高輪ゲートウェイ」編集台本 v3`
- v3の意図:
  - v2どおり切った結果、本編が約35分まで短くなった
  - 約10分を復活し、本編約45分へ戻す
  - ナレ込みでは約50分枠を想定
- 主な復活対象:
  - `#6` サウナ＆北欧の雑談: 3:30-4:00
  - `#5` 日系ブラジル人: 1:25
  - `#9` 国家プロジェクト実例: 1:20-1:40
  - `#14` ラクリス: 1:00
  - `#15` 制度の細部: 0:45-1:10
  - `#13` 地震に高い建物: 任意 0:12
- 構造変更:
  - NA8を「#11直後」から「地震・ラクリス後、改札/入管の直前」へ移動

## Resolve プロジェクト状態

### プロジェクト

- Resolve Project: `プラっと編集0518`
- 元タイムライン: `039編集_0619`
- 複製・作業タイムライン:
  - `039編集_0619 copy`
  - `039編集_0619 自動カット済み`

### 素材

- Timeline FPS: 24
- Start TC: `01:00:00:00`
- 元素材:
  - A1: `260605_001_Tr1.WAV`
  - A2: `260605_001_Tr2.WAV`
- 元範囲:
  - start frame `86400`
  - source total frames `121776`
  - original end frame `208176`

## ここまで実行済みの編集

### 1. Google Docテーブル由来のマーカー追加

Google Docの編集指示テーブルを解析し、Resolveタイムラインにマーカーを追加した。

- Red: カット/削除/落とし
- Yellow: 詰め
- Purple: 要編集判断
- Blue: 移動/ラストへ/締めcouplet
- `残し` だけの行は基本的にマーカー対象外

結果:

- action markers: 195件
- duplicate frame統合後の実マーカー: 193件
- 色別:
  - Red 172
  - Yellow 15
  - Purple 1
  - Blue 5
- customData prefix:
  - `platto39-script-v1-row-*`

### 2. Redマーカーだけを非リップル削除

`039編集_0619 copy` に対して、Redマーカー範囲を空白化した。

- 元のA1/A2フルクリップを削除
- Red範囲を除いたkeep rangesを、元のrecordFrame位置へ再配置
- タイムコードは保持
- 隙間は残す

結果:

- Red merged cut ranges: 154
- keep ranges: 155
- A1/A2: 各155クリップ
- original end frame: `208176` まで保持

### 3. CSVの色あり範囲だけを残す版

ユーザー指定CSV:

- `/Users/delaxpro/Downloads/プラッと粗編 - 039_Formatted_for_XML.csv`

CSV仕様:

- `色選択` が空でない行 = 残し範囲
- `色選択` が空の行 = 台本外/落とす候補

注意: これは過去のEP039実験で採用した仮ルール。未編集CSVをそのまま次回の正本として読む場合は、`色選択` だけでKEEP/CUTを決めない。未編集CSVはまず `SOURCE` 行として扱い、整理用テンプレートの `編集指示` 列へ `KEEP` / `CUT` / `RESTORE` を入れてからResolve配置案を作る。

2026-06-20のPalmier型検証:

- 未編集CSVを `SOURCE` としてIR化
- `039編集_0619_palmier実験` は既存の別タイムラインとして使用
- Resolveへ反映したのは黄色のSOURCEマーカー495個のみ
- クリップ配置、カット、隙間詰めは未実行
- 生成物:
  - `output/platto39_palmier_experiment/desired_timeline_ir.json`
  - `output/platto39_palmier_experiment/ep039_edit_instruction_template.csv`
  - `output/platto39_palmier_experiment/resolve_apply_plan.json`
  - `output/platto39_palmier_experiment/resolve_markers_after_apply.json`

処理:

- CSVの色あり行だけをkeep rangeとして扱う
- そこからRedマーカー範囲をさらに差し引く
- A1/A2へ非リップル再配置

結果:

- CSV rows: 495
- 色あり行: 426
- 色なし行: 69
- CSV merged keep ranges: 354
- Red cut ranges: 154
- final keep ranges: 206
- final keep frames: 50996
- final cut frames: 70780
- A1/A2: 各206クリップ
- 隙間あり版の最終end frame: `202386`
- 先頭クリップ:
  - 相対 `00:02:11:20`
  - タイムライン上 `01:02:11:20`

### 4. `自動カット済み` タイムラインで隙間詰め

ユーザーから「タイムライン名は自動カット済み」と指定があり、`039編集_0619 自動カット済み` に対して隙間を詰めた。

隙間ありの長さ:

- `01:20:32:18`

隙間詰め後:

- `00:35:24:20`

結果:

- Timeline: `039編集_0619 自動カット済み`
- Start frame: `86400`
- End frame: `137396`
- A1/A2: 各206クリップ
- A1/A2同期維持
- クリップは先頭から連続配置

## 重要な解釈

ユーザーが編集を変える理由:

- 自動カット結果が短すぎた
- 現在の35分版は切りすぎ
- v3は「短くなりすぎたので約10分戻す」ための台本

したがって、次にやるべきことは「さらに切る」ではなく、v3台本に明記された復活範囲を戻して45分前後へ伸ばすこと。

## 次回のコールドスタート手順

### 1. 作業場所

```bash
cd /Users/delaxpro/src/20_tools/davinciauto
git status --short
```

`delax100daysworkout` では作業しない。

### 2. Resolve状態確認

DaVinci Resolveが起動している前提で、Resolve MCPまたは以下のCLIを使う。

```bash
python3 /Users/delaxpro/src/claude-config/skills/davinci-resolve/scripts/resolve_cli.py status
python3 /Users/delaxpro/src/claude-config/skills/davinci-resolve/scripts/resolve_cli.py timelines
python3 /Users/delaxpro/src/claude-config/skills/davinci-resolve/scripts/resolve_cli.py timeline-info --timeline '039編集_0619 自動カット済み'
```

期待値:

- current project: `プラっと編集0518`
- target timeline exists: `039編集_0619 自動カット済み`
- fps: 24
- start TC: `01:00:00:00`
- duration after compact: `00:35:24:20`
- A1/A2 clip count: 206 each

### 3. v3復活範囲を追加する

目標は、`自動カット済み` の35分版から、v3で指定された以下の範囲を復活すること。

候補範囲:

- `#5` 日系ブラジル人
  - `00:13:01:07` → `00:14:27:23`
- `#6` サウナ＆北欧
  - `00:16:52:08` → `00:21:15:15`
  - 優先サブ範囲:
    - `00:16:52:08` → `00:17:33:15`
    - `00:17:37:20` → `00:18:02:08`
    - `00:18:04:18` → `00:18:35:03`
    - `00:18:44:03` → `00:19:24:03`
    - `00:19:28:12` → `00:20:09:00`
    - 任意: `00:20:18:15` → `00:21:15:15`
- `#9` 国家プロジェクト実例
  - `00:37:32:05` → `00:38:10:15`
  - `00:40:26:12` → `00:41:10:05`
  - 任意: `00:40:00:22` → `00:40:23:10`
- `#13` 地震
  - 任意: `00:50:05:20` → `00:50:15:10`
- `#14` ラクリス
  - `00:50:51:05` → `00:51:47:10`
- `#15` 制度の細部
  - `00:58:34:03` → `00:58:58:20`
  - `01:00:08:15` → `01:00:25:03`
  - `01:00:37:07` → `01:00:42:15`

注意:

- v3は「約10分復活」と言っているが、全範囲を機械的に戻すと繋がりが荒い可能性がある
- #15は断片的なので、繋がりが悪ければ#6サウナへ尺を振り替える
- NA8の位置移動も必要

### 4. 実装方針

現在の`自動カット済み`は隙間詰め済みなので、元タイムコード位置が失われている。

おすすめは次のどちらか。

#### 方針A: 新しい複製タイムラインを作り直す

1. `039編集_0619` または `039編集_0619 copy` を複製
2. CSV色あり + Red除外 + v3復活範囲を統合したkeep rangesを作る
3. A1/A2を元タイムコード位置へ非リップル配置
4. 確認後、隙間を詰めた版を生成

利点:

- 元TCベースでv3範囲を扱える
- 失敗時に戻しやすい

#### 方針B: 35分版に復活クリップを挿入する

1. v3復活範囲を元WAVから切り出す
2. 該当SEGの位置を探し、35分版に挿入
3. 必要なら後続クリップを押し出す

欠点:

- すでに詰め済みなので、元TCと現タイムライン位置の対応表が必要
- NA8移動も絡むため複雑

基本は方針A推奨。

## EP40設計への接続

EP039は、EP40以降のDoc→DaVinci自動反映設計の実例として扱う。

今回の重要な学びは、35分まで短くなった既存タイムラインを直接reconcileするより、元タイムコードを保ったDoc/CSVから編集状態を作り直し、別タイムラインとして生成する方が安全ということ。

EP40では以下をV0方針にする。

- Google Doc本文の自然文見出しではなく、Doc/CSV表を正本にする
- timecodeからframeへの変換はIR生成時に1回だけ行う
- `doc_row_id` や `customData` prefixで再実行可能性を確保する
- 既存Resolveタイムラインへの直接clear/placeはV1以降の検証対象にする
- V0では、CSV → desired-state IR → マーカー案/新規タイムライン案 → 限界レポートの順に進める

詳細は `docs/Doc_to_DaVinci_Automation_Design.md` を参照。

## 2026-06-21 NA込み再計算版

ナレーションをA3へ後付けする最初の試行では、元TC位置に置く非詰め版を作った。

- `039編集_0619_非詰めNA実験`
- A1/A2: 各206 clips
- A3: 13 clips

これは診断用として有益だったが、NAが抜いた隙間より長い箇所があり、完成形としては「元TC位置に置く」だけでは不足だと分かった。

その後、完成タイムライン上のTCを再計算する方式を採用した。

```text
KEEP尺 + NA尺 + KEEP尺 + NA尺 ...
```

この方式では、`source TC` と `record TC` を分ける。

- `source TC`: 元素材のどこを使うか
- `record TC`: 完成タイムライン上のどこに置くか

成功タイムライン:

- `039編集_0619_NA込み再計算`

成功値:

- A1/A2: 各206 clips
- A3: 13 clips
- total plan items: 219
- final duration frames: 56833
- final duration: 約39分28秒
- final end TC: `01:39:28:01`

生成物:

- `output/ep039_recalculated_na/apply_report.json`
- `output/ep039_recalculated_na/tc_mapping.csv`

実行スクリプト:

- `scripts/apply_ep039_recalculated_na_timeline.py`
- `scripts/apply_ep039_noncompact_na_experiment.py`
- `scripts/platto39_generate_na_audio.py`

次回以降の再実行手順:

- `docs/EP039_Doc_to_DaVinci_Recalculated_NA_Runbook.md`

現時点では、`039編集_0619_NA込み再計算` がDoc→DaVinci完成形生成の本命実験版。`039編集_0619_非詰めNA実験` は、NAを元TC上の空白に置いた場合の溢れを確認する診断版として残す。

## 2026-06-21 台本尺計算ループ

次回以降は、DaVinciを触る前に台本/CSV段階で想定尺を確認する。

基本ループ:

```text
Google Doc / CSV
→ desired_timeline_ir
→ duration_report
→ Doc / CSV修正
→ duration_report再実行
→ 台本が固まったらDaVinciへ生成
```

追加スクリプト:

- `scripts/doc_ir_duration_report.py`

EP039の現行IRでの確認例:

```bash
python3 scripts/doc_ir_duration_report.py \
  output/ep039_auto_cut_2/desired_timeline_ir_24fps.json \
  --na-dir output/ep039_auto_cut_2/na_wav \
  --target-minutes 45 \
  --out-json output/ep039_script_duration_loop/duration_report.json \
  --out-report output/ep039_script_duration_loop/duration_report.md \
  --out-csv output/ep039_script_duration_loop/duration_events.csv
```

出力:

- `output/ep039_script_duration_loop/duration_report.md`
- `output/ep039_script_duration_loop/duration_report.json`
- `output/ep039_script_duration_loop/duration_events.csv`

2026-06-21時点の現行IRによる想定尺:

- total: `00:46:39:19`
- target 45分に対して: `00:01:39:19` over
- KEEP: `00:34:37:04`
- RESTORE: `00:07:59:10`
- NA: `00:04:03:05`

注意: これはDoc/IRを正本にした台本尺。`039編集_0619_NA込み再計算` は既知成功カット範囲206個を正本にしたため約39分28秒。両者の差は、何を正本として採用するかの違い。今後はDaVinciへ出す前に、この差をDoc/CSV上で解消する。

## 2026-06-21 ブロック色分け工程

現行の自動編集は発話行ごとに厳密配置するため、フィラーや短い言い淀みまでチクチク切りすぎる。初稿荒編では、先にSEG/ブロック単位で色分けしたタイムラインを作り、構造を確認してから細かいカットへ進む方針にする。

参照PDF:

- `/Users/delaxpro/Downloads/プラっと#39.pdf`

追加スクリプト:

- `scripts/platto_script_to_block_color_plan.py`

実行例:

```bash
python3 scripts/platto_script_to_block_color_plan.py \
  '/Users/delaxpro/Downloads/プラっと#39.pdf' \
  --fps 24 \
  --out-json output/ep039_block_color/block_color_plan.json \
  --out-csv output/ep039_block_color/block_color_plan.csv \
  --out-report output/ep039_block_color/block_color_plan.md
```

出力:

- `output/ep039_block_color/block_color_plan.json`
- `output/ep039_block_color/block_color_plan.csv`
- `output/ep039_block_color/block_color_plan.md`

抽出結果:

- blocks: 19
- block total duration: `01:01:05:00`

この計画は、色分け台本のSEG範囲をDaVinci上で見える化するためのもの。既存のDaVinci Script `Colorize_Timeline_Clips.py` は順番にclip colorを付ける簡易版なので、今後は `block_color_plan` の `source_in/out` と `resolve_color` を使い、SEG単位のclipへ色を付ける処理へ拡張する。

今後の推奨順:

```text
台本/CSVで尺を確認
→ PDF/台本からblock_color_plan生成
→ ブロック単位の荒編/色分けタイムライン作成
→ 聴感確認
→ 必要箇所だけ発話行単位の細かいカット
```

注意: 単一の長いWAVクリップに対してclip colorだけを変えても、部分範囲だけ色分けすることはできない。色分けを有効にするには、先にSEG単位のclipへ分けるか、SEG範囲を別clipとして配置する必要がある。

## Palmier調査からの持ち帰り

Palmier Proから持ち込むのはコードではなく、以下の設計規律だけ。

- 操作前に現在状態を読む
- 内部時間はframeに統一する
- 自動化に渡す操作面を小さく厳密にする
- 再実行時に同じ範囲を二重配置しないよう安定IDを持つ
- 実行後に結果を読み返して検証する

Palmierは自前エディタなのでタイムライン状態を完全所有できる。一方、こちらはResolve外部制御なので、EP40 V0では既存タイムラインを直接書き換えるのではなく、新規タイムライン生成を基本にする。

## 一時スクリプト履歴

過去作業では `/tmp` に以下のスクリプトを作った。

- `/tmp/platto39_apply_nonripple_cuts.py`
  - Redマーカー範囲だけを除いて元TC位置へ再配置
- `/tmp/platto39_apply_csv_keep_and_red_cuts.py`
  - CSV色あり範囲からRed範囲を差し引いて元TC位置へ再配置
- `/tmp/platto39_compact_auto_cut.py`
  - keep rangesを先頭から連続配置し、隙間詰め版を生成
- `/tmp/platto39_verify_csv_keep.py`
  - A1/A2 clip countや先頭/末尾clip範囲を確認

次回はこれらを `scripts/` 配下へEP039用ツールとして整理するのがよい。

候補ファイル名:

- `scripts/platto39_build_keep_ranges.py`
- `scripts/platto39_apply_resolve_cuts.py`
- `scripts/platto39_compact_timeline.py`

2026-06-21時点で、NA込み再計算の本命経路は `scripts/` 配下へ保存済み。今後は上記候補名で一般化する前に、まず `scripts/apply_ep039_recalculated_na_timeline.py` とランブックを正本として扱う。

## 検証済み数値

### CSV色あり + Red除外

- `final_keep_ranges`: 206
- `final_keep_frames`: 50996
- 24fps換算: `00:35:24:20`

### `039編集_0619 自動カット済み`

- start frame: `86400`
- end frame: `137396`
- duration: `50996 frames`
- duration TC: `00:35:24:20`
- A1 first clip:
  - `86400` → `86553`
- A1 last clip:
  - `137138` → `137396`
- A2も同じ範囲

## 注意事項

- Resolveの実編集は必ず複製タイムラインで行う
- `039編集_0619` は元タイムラインとしてなるべく触らない
- `自動カット済み` は既に35分詰め版になっている
- v3反映は「復活」が主目的
- Google Docにはv3方針が既に入っているが、発話テーブル側の編集指示まではまだv3に更新していない
- `delax100daysworkout` repoには今回のDaVinci自動化コードを置かない

## 関連ファイル

- v3台本添付:
  - `/Users/delaxpro/.codex/attachments/345ddc28-e370-40ae-b9fe-b40b1075b87b/pasted-text.txt`
- CSV:
  - `/Users/delaxpro/Downloads/プラッと粗編 - 039_Formatted_for_XML.csv`
- Google Doc:
  - <https://docs.google.com/document/d/12xy1YRVMr39F1P7Pa8bH71gQZjOhfJDW9JE-E0YxWIw/edit?tab=t.0>
- Resolve helper CLI:
  - `/Users/delaxpro/src/claude-config/skills/davinci-resolve/scripts/resolve_cli.py`
- NA込み再計算ランブック:
  - `docs/EP039_Doc_to_DaVinci_Recalculated_NA_Runbook.md`

## 次にやること

1. Resolve上で `039編集_0619_NA込み再計算` を聴感確認する
2. `tc_mapping.csv` を見ながら、NAの入る位置が意図通りか確認する
3. v3台本から復活範囲を構造化データにする
4. 45分に足りない場合は、#6サウナ範囲などをkeep rangesへ追加する
5. NA8位置移動とラストcouplet位置を確認する
6. EP40向けに、Doc表へ `NA`, `KEEP`, `RESTORE`, `record order` を書ける形へマニュアルを更新する
