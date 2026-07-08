# Platto Split Audio Whisper Workflow

プラっと収録で途中から録音ファイルが分かれた場合でも、通常回と同じ「文字起こしCSV→色選択→台本/荒編」ワークフローに載せるための手順。

## 目的

- 分割されたWAVを、シート上では1本の連続収録として扱う。
- 各話者のラベリアマイクを話者名に固定する。
- Google SheetsへアップロードするCSVは、既存の荒編形式5列に揃える。

## 標準CSV

アップロード用CSVは以下の5列だけを正本にする。

| 列 | 用途 |
| --- | --- |
| Speaker Name | 話者名 |
| イン点 | 連続タイムライン上の開始TC |
| アウト点 | 連続タイムライン上の終了TC |
| 文字起こし | Whisper文字起こし |
| 色選択 | 使い所チェック用。初期値は空欄 |

分割元ファイル、パート番号、Whisper JSONなどの検証情報は `*_with_source.csv` と `split_audio_manifest.resolved.json` に残し、シートには持ち込まない。

## シート投入用の発話ブロック化

Whisperの生セグメントは細かく切れすぎるため、使い所チェック用のGoogle Sheetsには、同じ話者の一連の発話をまとめた `*_whisper_review_blocks.csv` を投入する。

- raw: `XXX_whisper_merged.csv`
  - Whisper由来の細かいTCを残す検証用。
- review blocks: `XXX_whisper_review_blocks.csv`
  - ディレクターが読む・色を付けるための正本。
  - 同じ話者、短い間、長すぎない範囲を1ブロックにまとめる。
  - 細かいカット編集に進む時はraw CSVへ戻れる。

実行例:

```bash
python3 scripts/platto_merge_whisper_blocks.py \
  output/ep041_whisper/041_whisper_merged.csv \
  --out output/ep041_whisper/041_whisper_review_blocks.csv \
  --fps 24 \
  --max-gap 1.0 \
  --max-duration 18 \
  --max-chars 160
```

初期値は「1秒以内の間」「最大18秒」「最大160文字」。番組によって発話が長い場合は `--max-duration` と `--max-chars` を広げる。

## 分割ファイルの考え方

1. パートごとに、全トラックのWAV尺を確認する。
2. 次パートの開始位置は、前パートの最長尺を足した位置にする。
3. 各Whisperセグメントのローカル時刻にパート開始位置を足して、全体TCへ変換する。
4. 対話収録では、2本のマイクを別々にWhisperしない。相手の声が別マイクにも入るため、同じ発話が2回起こされやすい。
5. 標準は `transcription_mode: mixed_dialogue`。
   - Tr1/Tr2をパートごとに1本へミックスする。
   - ミックス音声を1回だけWhisperする。
   - 各セグメントのTr1/Tr2音量を比較して、話者ラベルを付ける。
   - これにより、同一発話が平田/石田の両方に出る構造を避ける。

例:

- `001_Tr1.WAV` / `001_Tr2.WAV`: 00:00:00:00 から開始
- `002_Tr1.WAV` / `002_Tr2.WAV`: `001` の尺だけ後ろから開始

これにより、Resolveの元タイムラインが連続配置されていれば、シート上のTCもそのまま参照できる。

## 実行手順

1. `output/epXXX_whisper/split_audio_manifest.json` を作る。
2. `speaker`, `track`, `part`, `path` を収録実態に合わせて記入する。
3. Whisperを実行する。

```bash
uv run --with mlx-whisper --with numpy python scripts/platto_split_whisper.py \
  --manifest output/ep040_whisper/split_audio_manifest.json \
  --out-dir output/ep040_whisper
```

4. 生成された `XXX_whisper_merged.csv` から `XXX_whisper_review_blocks.csv` を作る。
5. `XXX_whisper_review_blocks.csv` を「プラッと粗編」Google Sheetへ投入する。

```bash
PYTHONUNBUFFERED=1 /Users/delaxpro/src/70_プラッと/platto-automation/venv/bin/python \
  /Users/delaxpro/src/70_プラッと/platto-automation/tools/push_csv_to_sheet.py \
  --csv /Users/delaxpro/src/20_tools/davinciauto/output/ep041_whisper/041_whisper_review_blocks.csv \
  --tab 041_whisper_blocks_0702
```

初回やスコープ更新時はGoogle OAuthの許可画面が出る。許可後はタブ作成とCSV投入が自動で進む。

## EP040 実績

- 素材フォルダ: `/Users/delaxpro/Dropbox/プラッと/01_プラッと素材/040平田石田`
- Resolve元タイムライン: `040_オリジナル`
- Tr1: 平田
- Tr2: 石田
- 文字起こし方式: `mixed_dialogue`
- part `001`: 約17分45秒
- part `002`: 約74分37秒
- アップロード先: [プラッと粗編 / 040_whisper_0624](https://docs.google.com/spreadsheets/d/1xR3ieULVDruivI_Flq2I3FRx4ZtgknPT6bjO5PHYzbg/edit#gid=1543052822)
- 初回行数: 3152行
- マイク別Whisper重複除去後: 2272行
- ミックス対話Whisper版: 1998行

## 注意点

- Whisperは長い無音末尾で「ご視聴ありがとうございました」などの定型文を誤生成することがある。`scripts/platto_split_whisper.py` では、定型アウトロと長い同一音反復を除外している。
- 2本のマイクに相手の声が漏れる場合、マイク別Whisperは重複が多くなる。EP040以降は、原則としてミックス対話Whisperを使う。
- 話者ラベルは各セグメント内のTr1/Tr2音量比較で付けるため、短い相槌やかぶりでは誤ることがある。使い所チェックでは、重複の少なさを優先する。
- 番組テーマ、場所、出演者、固有名詞は、Whisper後の用語補正辞書として使う。Whisper本体に無理に期待するより、`*_with_source.csv` または `*_whisper_review_blocks.csv` 作成後に機械補正する方が安全。
- Resolve側で録音パート間に実際の空白や欠落がある場合は、manifestだけでは吸収できない。その場合はパート開始位置を手で補正する拡張が必要。
