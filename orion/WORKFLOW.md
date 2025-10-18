# Orion Pipeline v2 - Complete Workflow Guide

完全な自動化ワークフロー：スクリプトから完成XMLまで

## 概要

このガイドでは、Orionシリーズ（EP12以降）の動画制作パイプラインの完全な手順を説明します。

## 前提条件

### 必要な環境
- Python 3.11+
- ffmpeg（音声ファイル解析用）
- Gemini API Key（TTS生成用）
- Google Cloud認証（オプション：Google TTS fallback用）

### 環境変数
`.env`ファイルに以下を設定：
```bash
GEMINI_API_KEY=your_gemini_api_key_here
GOOGLE_APPLICATION_CREDENTIALS=/path/to/google-credentials.json  # オプション
```

## ワークフロー全体像

```
1. プロジェクト準備
   ↓
2. 入力ファイル作成（スクリプト・字幕・TTS設定）
   ↓
3. TTS音声生成（Gemini）
   ↓
4. パイプライン実行（タイムライン計算・出力生成）
   ↓
5. DaVinci Resolve インポート
```

---

## Phase 1: プロジェクト準備

### 1.1 ディレクトリ構造の作成

新しいエピソード用のディレクトリを作成します：

```bash
cd /path/to/davinciauto/prototype/orion-v2
mkdir -p projects/OrionEp{N}/{inputs,output/audio,exports}
```

**例（EP12の場合）**:
```bash
mkdir -p projects/OrionEp12/{inputs,output/audio,exports}
```

**ディレクトリ構造**:
```
projects/OrionEp12/
├── inputs/           # 入力ファイル
│   ├── ep12.srt           # 字幕（LLM生成）
│   ├── ep12nare.md        # ナレーション原稿
│   ├── ep12nare.yaml      # TTS設定（Gemini）
│   └── orinonep12.md      # オリジナル脚本（見出し付き）
├── output/           # パイプライン出力
│   └── audio/             # TTS生成音声ファイル
└── exports/          # 最終出力
```

---

## Phase 2: 入力ファイル作成

### 2.1 オリジナル脚本（`orinonep{N}.md`）

**目的**: 見出しマーカーで章立てを定義し、3秒ギャップを挿入する基準となる

**フォーマット**:
```markdown
【HH:MM-HH:MM】セクション名
本文テキスト...

【HH:MM-HH:MM】次のセクション
本文テキスト...
```

**例**:
```markdown
【00:00-00:30】アバン
今日の瞑想スコア85点という通知に、違和感を感じたことはありませんか？
この数値化は、進歩の証なのか、それとも本質からの逸脱なのか？

【00:30-01:30】日常への没入
月曜日の朝、全社ミーティング。
人事部長が誇らしげに語ります...
```

**重要**: 見出し行は `【HH:MM-HH:MM】` 形式で、パイプラインが自動検出します。

---

### 2.2 ナレーション原稿（`ep{N}nare.md`）

**目的**: TTS生成の元となるテキスト（1行 = 1音声ファイル）

**フォーマット**:
- 各行が1つの音声セグメントに対応
- 句読点や読み方を調整
- SSML タグは **使用しない**（YAML側で指定）

**例**:
```
今日の瞑想スコア85点という通知に、違和感を感じたことはありませんか？
この数値化は、進歩の証なのか、それとも本質からの逸脱なのか？
ようこそ、オリオンの会議室へ。今夜のテーマは「瞑想アプリの違和感」。
```

**行数 = 音声ファイル数**: EP12の場合、80行 = 80音声ファイル

---

### 2.3 TTS設定（`ep{N}nare.yaml`）

**目的**: Gemini TTS の音声・スタイル・SSML設定

**フォーマット**:
```yaml
gemini_tts:
  segments:
    - speaker: ナレーター
      voice: kore  # Gemini音声ID
      text: "今日の瞑想スコア85点という通知に、違和感を感じたことはありませんか？"
      style_prompt: "Speak with intellectual depth and documentary-style narration, calm and authoritative."

    - speaker: ナレーター
      voice: kore
      text: "この数値化は、進歩の証なのか、それとも本質からの逸脱なのか？"
      style_prompt: "Speak with intellectual depth and documentary-style narration, calm and authoritative."
```

**フィールド説明**:
- `speaker`: 話者名（ログ表示用）
- `voice`: Gemini音声ID（`kore`, `aoede`, `charon`, `fenrir`, `kore`, `puck`, `coral`, など）
- `text`: 発話テキスト（SSML タグ使用可能）
- `style_prompt`: 音声スタイル指示（英語で記述）
- `scene`: シーン名（オプション、ログ用）

**SSML タグ例**:
```yaml
text: "ようこそ、<sub alias='おりおん'>オリオン</sub>の会議室へ。<break time='600ms'/>今夜のテーマは..."
```

**重要**: YAMLのセグメント数は `ep{N}nare.md` の行数と一致させる

---

### 2.4 字幕（`ep{N}.srt`）

**目的**: 最終的にタイムラインに配置される字幕テキスト

**フォーマット**: 標準SRT形式
```
1
00:00:00,000 --> 00:00:05,000
今日の瞑想スコア85点！という通知に
違和感を感じたことはありませんか？

2
00:00:05,000 --> 00:00:10,000
この数値化は 進歩の証なのか
それとも本質からの逸脱なのか？
```

**注意点**:
- タイムコードは仮のもので構いません（パイプラインで上書きされます）
- テキストは複数行に分割可能（DaVinci Resolveで表示する形式）
- 字幕数 > 音声数 が一般的（1音声に複数字幕を配置）

**例**: EP12の場合、99字幕エントリ → 80音声セグメント

---

## Phase 3: TTS音声生成

### 3.1 汎用TTS生成スクリプト

**スクリプト**: `generate_tts.py`

**使い方**:
```bash
python generate_tts.py --episode {N} [--limit {M}] [--delay {SEC}]
```

**引数**:
- `--episode`: エピソード番号（必須）
- `--limit`: 生成セグメント数の上限（テスト用、オプション）
- `--delay`: リクエスト間隔（秒、デフォルト: 3.0）

**例**:
```bash
# テスト（最初の3セグメントのみ）
python generate_tts.py --episode 12 --limit 3 --delay 2.0

# 全セグメント生成
python generate_tts.py --episode 12 --delay 3.0
```

### 3.2 生成プロセス

1. `ep{N}nare.yaml` を読み込み
2. Gemini TTS APIに順次リクエスト
3. `projects/OrionEp{N}/output/audio/` に保存
4. ファイル名: `OrionEp{N}_001.mp3`, `OrionEp{N}_002.mp3`, ...

**推定時間**: 3-4秒/セグメント × セグメント数
- EP12（80セグメント）: 約4-6分

### 3.3 生成確認

```bash
ls -lh projects/OrionEp12/output/audio/
```

**出力例**:
```
-rw-r--r--  27K  OrionEp12_001.mp3
-rw-r--r--  29K  OrionEp12_002.mp3
-rw-r--r--  26K  OrionEp12_003.mp3
...
```

---

## Phase 4: パイプライン実行

### 4.1 パイプライン概要

**スクリプト**: `pipeline/core.py`

**処理フロー**:
1. **入力検証**: 必要なファイルの存在確認
2. **SRT解析**: 字幕エントリをパース
3. **TTS確認**: 音声ファイルの存在・時間長を取得
4. **タイムライン計算**:
   - 音声ファイルを連続配置
   - 見出しマーカーで3秒ギャップ挿入
   - タイムコード計算（29.97fps）
5. **出力生成**:
   - タイムコード付きSRT
   - タイムラインCSV
   - FCP7 XML（DaVinci Resolve用）
   - マージ済みSRT

### 4.2 実行方法

```bash
cd prototype/orion-v2
PYTHONPATH=pipeline python pipeline/core.py --project OrionEp{N}
```

**例（EP12）**:
```bash
PYTHONPATH=pipeline python pipeline/core.py --project OrionEp12
```

### 4.3 出力ファイル

**`output/` ディレクトリ**:
- `OrionEp12_timecode.srt` - タイムコード付き字幕
- `OrionEp12_timeline.csv` - タイムライン詳細（デバッグ用）
- `OrionEp12_timeline.xml` - DaVinci Resolve インポート用XML

**`exports/` ディレクトリ**:
- `orionep12_merged.srt` - マージ済み字幕（互換性用）

### 4.4 パイプライン出力例

```
[Phase 1] Input Validation
✅ Input validation passed

[Phase 2] Parse Source SRT
✅ Parsed 99 subtitle entries from ep12.srt

[Phase 3] TTS Generation
✅ Processed 80 audio segments
  → Total audio duration: 456.23s (7.6min)

[Phase 4] Timeline Calculation
  → Detected 6 section markers from orinonep12.md
  → Scene lead-in: 3.0s at sections
✅ Calculated timeline for 80 audio segments
  Total duration: 474.23s (7.9min)
  Scene transitions: 6
  Final timecode: 00:07:54:06

[Phase 5] Output Writing
  → Loaded 80 Nare lines from ep12nare.md
  → Mapped 99 subtitles to 80 segments
  ✅ OrionEp12_timecode.srt
  ✅ OrionEp12_timeline.csv
  ✅ OrionEp12_timeline.xml
  ✅ orionep12_merged.srt

✅ All output files written successfully
```

---

## Phase 5: DaVinci Resolve インポート

### 5.1 XMLインポート

1. DaVinci Resolveを開く
2. **File → Import → Timeline → FCP7 XML...**
3. `output/OrionEp12_timeline.xml` を選択
4. タイムラインが自動生成される

### 5.2 タイムライン構造

- **Video Track 1**: （空）
- **Audio Track 1**: 音声ファイル（`OrionEp12_001.mp3` ～ `OrionEp12_080.mp3`）
- 見出しマーカー位置に3秒ギャップ

### 5.3 字幕追加

1. `output/OrionEp12_timecode.srt` を手動インポート
2. タイムラインに配置
3. タイミング確認

---

## トラブルシューティング

### TTS生成エラー

**問題**: `ModuleNotFoundError: No module named 'tts_config_loader'`

**解決**:
```bash
PYTHONPATH=/path/to/experiments:/path/to/scripts python generate_tts.py ...
```

---

### パイプラインエラー

**問題**: `No such file or directory: ep{N}nare.md`

**解決**: ファイル名を確認
- `ep12nare.md` (正)
- `ep12nare` (誤)

---

### 字幕ズレ

**問題**: SRTタイムコードと音声がズレる

**原因**: Nare原稿と字幕のマッピングミス

**解決**:
1. `ep{N}nare.md` の行数を確認
2. `ep{N}nare.yaml` のセグメント数が一致するか確認
3. パイプライン再実行

---

## よくある質問

### Q1: エピソード番号は何番まで使えますか？

A: 制限なし。`--episode 13`, `--episode 100` など任意の番号が使用可能です。

### Q2: Gemini TTS以外のTTSエンジンは使えますか？

A: はい。`orion_tts_generator.py` がGoogle Cloud TTSにフォールバックします。

### Q3: 見出しマーカーなしでパイプライン実行できますか？

A: はい。見出しマーカーがない場合、音声ファイルは連続配置されます（ギャップなし）。

### Q4: 字幕数と音声数が異なる場合、どうなりますか？

A: パイプラインが自動的に比例配分します。音声1つに複数字幕を割り当てることが可能です。

---

## まとめ

このワークフローにより、スクリプト作成からDaVinci Resolve用XMLまで、完全自動化された制作パイプラインが実現されます。

**次のエピソード作成時**は、Phase 1からこのガイドに従って進めてください。

---

**作成日**: 2025-10-17
**対象バージョン**: Orion Pipeline v2
**対象エピソード**: EP12以降
