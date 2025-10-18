# Orion Pipeline v2

完全自動化された動画制作パイプライン for Orionシリーズ

## 概要

Orion Pipeline v2 は、スクリプトから DaVinci Resolve 用XMLまでを自動生成する動画制作パイプラインです。

**主な機能**:
- ✅ Gemini TTS による高品質音声生成
- ✅ 見出しマーカーによる自動ギャップ挿入
- ✅ 字幕とナレーションの自動マッピング
- ✅ FCP7 XML形式でのタイムライン出力
- ✅ エピソード番号指定による汎用化

## クイックスタート

### 1. 新しいエピソードの作成

```bash
# プロジェクトディレクトリ作成
mkdir -p projects/OrionEp13/{inputs,output/audio,exports}

# 必要なファイルを配置
# - inputs/ep13.srt
# - inputs/ep13nare.md
# - inputs/ep13nare.yaml
# - inputs/orinonep13.md
```

### 2. TTS音声生成

```bash
python generate_tts.py --episode 13 --delay 3.0
```

### 3. パイプライン実行

```bash
PYTHONPATH=pipeline python pipeline/core.py --project OrionEp13
```

### 4. DaVinci Resolve インポート

**File → Import → Timeline → FCP7 XML** から `output/OrionEp13_timeline.xml` をインポート

---

## ディレクトリ構造

```
prototype/orion-v2/
├── README.md              # このファイル
├── WORKFLOW.md            # 完全ワークフローガイド
├── generate_tts.py        # 汎用TTS生成スクリプト
├── pipeline/              # パイプラインコア
│   ├── core.py
│   ├── engines/
│   ├── parsers/
│   └── writers/
└── projects/              # エピソードごとのプロジェクト
    ├── OrionEp11/
    ├── OrionEp12/
    └── OrionEp13/
        ├── inputs/
        │   ├── ep13.srt
        │   ├── ep13nare.md
        │   ├── ep13nare.yaml
        │   └── orinonep13.md
        ├── output/
        │   ├── audio/
        │   ├── OrionEp13_timecode.srt
        │   ├── OrionEp13_timeline.csv
        │   └── OrionEp13_timeline.xml
        └── exports/
            └── orionep13_merged.srt
```

---

## 入力ファイル

### `ep{N}.srt` - 字幕
標準SRT形式の字幕ファイル。複数行に分割可能。

### `ep{N}nare.md` - ナレーション原稿
1行 = 1音声ファイル。TTS生成の元テキスト。

### `ep{N}nare.yaml` - TTS設定
Gemini TTS の音声・スタイル・SSML設定。

```yaml
gemini_tts:
  segments:
    - speaker: ナレーター
      voice: kore
      text: "テキスト..."
      style_prompt: "スタイル指示..."
```

### `orinonep{N}.md` - オリジナル脚本
見出しマーカー（`【HH:MM-HH:MM】セクション名`）で章立てを定義。

---

## 出力ファイル

### `OrionEp{N}_timecode.srt`
タイムコード付き字幕（音声タイミングに完全一致）

### `OrionEp{N}_timeline.csv`
タイムライン詳細（デバッグ用）

| index | audio_filename | duration_sec | start_timecode | end_timecode | is_scene_start | scene_lead_in_sec |
|-------|----------------|--------------|----------------|--------------|----------------|-------------------|
| 1     | OrionEp12_001.mp3 | 4.12 | 00:00:00:00 | 00:00:04:03 | NO | 0.00 |
| 11    | OrionEp12_011.mp3 | 6.81 | 00:01:04:03 | 00:01:11:04 | YES | 3.00 |

### `OrionEp{N}_timeline.xml`
DaVinci Resolve インポート用 FCP7 XML

---

## 主要機能

### 1. 見出しマーカーによる自動ギャップ

`orinonep{N}.md` の見出し（`【HH:MM-HH:MM】`）を自動検出し、該当位置に3秒ギャップを挿入。

**例**:
```markdown
【00:00-00:30】アバン
...

【00:30-01:30】日常への没入  ← ここで3秒ギャップ
...
```

### 2. 字幕とナレーションの自動マッピング

ナレーション原稿（`ep{N}nare.md`）と字幕（`ep{N}.srt`）をテキストマッチングで自動マッピング。

- 99字幕 → 80音声 のような不一致も自動処理
- 1音声に複数字幕を割り当て可能

### 3. Gemini TTS 統合

Google の Gemini TTS API を使用した高品質音声生成。

**対応音声**:
- `kore`, `aoede`, `charon`, `fenrir`, `puck`, `coral` など

**SSML対応**:
- `<sub alias='読み方'>表記</sub>` - 読み方指定
- `<break time='600ms'/>` - ポーズ挿入

---

## トラブルシューティング

### TTS生成が失敗する

**原因**: Gemini API Key未設定

**解決**:
```bash
# .env に追加
GEMINI_API_KEY=your_api_key_here
```

### 字幕タイミングがズレる

**原因**: Nare原稿と字幕のマッピングミス

**解決**:
1. `ep{N}nare.md` の行数を確認
2. `ep{N}nare.yaml` のセグメント数が一致するか確認
3. パイプライン再実行

### XMLインポートエラー

**原因**: 音声ファイルパスが不正

**解決**: パイプライン実行時に `output/audio/` に音声ファイルが存在することを確認

---

## 開発者向け

### パイプラインアーキテクチャ

```
core.py
├── parsers/      # 入力ファイル解析
│   ├── srt.py
│   └── markdown.py
├── engines/      # コア処理
│   ├── tts.py
│   └── timeline.py
└── writers/      # 出力ファイル生成
    ├── srt.py
    ├── csv.py
    └── xml.py
```

### 拡張方法

**新しいTTSエンジン追加**:
1. `engines/tts.py` に新しいエンジンクラスを追加
2. `generate_tts.py` で切り替えロジックを実装

**新しい出力形式追加**:
1. `writers/` に新しいライターを追加
2. `core.py` の Phase 5 で呼び出し

---

## ライセンス

内部プロジェクト用

---

## 関連ドキュメント

- [WORKFLOW.md](WORKFLOW.md) - 完全ワークフローガイド
- [引き継ぎ.md](../../引き継ぎ.md) - プロジェクト全体の引き継ぎ資料

---

**最終更新**: 2025-10-17
