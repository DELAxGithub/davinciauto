# Orion Production Pipeline

オリオンシリーズ制作のための完全自動化パイプライン（DaVinci Resolve統合）

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python: 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)]()
[![DaVinci Resolve](https://img.shields.io/badge/DaVinci_Resolve-18+-red.svg)]()

## 🚀 クイックスタート

```bash
# EP13を作成（フルオート）
cd orion
python generate_tts.py --episode 13 --delay 3.0
PYTHONPATH=pipeline python pipeline/core.py --project OrionEp13
```

生成された `projects/OrionEp13/output/OrionEp13_timeline.xml` をDaVinci Resolveにインポート

## 📁 ディレクトリ構成

```
davinciauto/
├── orion/                      # メインパイプライン ⭐
│   ├── generate_tts.py         # TTS生成スクリプト
│   ├── pipeline/               # パイプラインコア
│   │   ├── core.py             # メイン処理
│   │   ├── writers/            # 出力生成（SRT, CSV, XML）
│   │   └── utils/              # ユーティリティ
│   ├── projects/               # エピソードデータ
│   │   └── OrionEp12/          # リファレンス実装
│   ├── WORKFLOW.md             # 完全マニュアル
│   └── README.md               # パイプライン詳細
│
├── projects/                   # プロジェクトデータ（全エピソード）
│   ├── OrionEp12/              # EP12（ゴールデンリファレンス）
│   ├── OrionEp13/
│   └── ...
│
├── scripts/                    # ユーティリティスクリプト
│
└── archive/                    # 旧バージョン（参照用のみ）
    ├── minivt_pipeline/
    ├── experiments/
    ├── prototype-legacy/
    └── README.md
```

## 🎯 主な機能

### ✅ 実装済み
- **Gemini TTS統合**: Google Gemini APIでナレーション音声生成（SSML対応）
- **タイムライン自動生成**: FCP7 XML形式でDaVinci Resolve互換出力
- **セクションギャップ自動挿入**: 脚本の時間マーカーから3秒ギャップ挿入
- **字幕タイムコード生成**: SRTファイルとナレーション原稿のテキストマッチング
- **CSV検証出力**: タイムライン詳細の確認用CSV
- **SSML対応**: 読み仮名、ブレーク（間）の自動処理

### 🔧 開発中
- SRT自動生成機能（ナレーション原稿から字幕を自動生成）
- 統合CLIツール（`orion` コマンド）
- 包括的な検証レポート

## 📖 ドキュメント

- **[WORKFLOW.md](orion/WORKFLOW.md)** - 完全な制作マニュアル（Phase 1-5）
- **[DESIGN.md](orion/DESIGN.md)** - アーキテクチャ設計
- **[STATUS.md](orion/STATUS.md)** - 開発ステータス

## 🛠️ セットアップ

### 必要要件
- Python 3.11+
- Google Gemini API Key
- DaVinci Resolve 18+（オプション）

### 環境変数

```bash
export GEMINI_API_KEY="your-api-key"
```

## 📝 エピソード制作ワークフロー

### Phase 1: プロジェクト準備
```bash
mkdir -p projects/OrionEp13/inputs
mkdir -p projects/OrionEp13/output/audio
mkdir -p projects/OrionEp13/exports
```

### Phase 2: 入力ファイル作成

以下の4つのファイルを `projects/OrionEp13/inputs/` に配置：

- `ep13nare.yaml` - TTS設定（Gemini voice、style prompt、SSML）
- `ep13nare.md` - ナレーション原稿（1行 = 1音声ファイル）
- `ep13.srt` - 字幕ファイル（視聴者用字幕）
- `orinonep13.md` - 元の脚本（セクションマーカー含む）

### Phase 3: TTS生成

```bash
cd orion
python generate_tts.py --episode 13 --delay 3.0
```

**実行内容**:
- `ep13nare.yaml` から81セグメント読み込み
- Gemini APIで音声生成（MP3出力）
- `projects/OrionEp13/output/audio/` に保存
- 約15-20分で完了（セグメント数による）

### Phase 4: パイプライン実行

```bash
cd orion
PYTHONPATH=pipeline python pipeline/core.py --project OrionEp13
```

**実行内容**:
1. 入力ファイル検証
2. SRTパース（ep13.srt）
3. 音声セグメント読み込み
4. タイムライン計算（セクションギャップ挿入）
5. 出力生成：
   - `OrionEp13_timecode.srt` - タイムコード付き字幕
   - `OrionEp13_timeline.csv` - タイムライン詳細（検証用）
   - `OrionEp13_timeline.xml` - DaVinci Resolve用XML

### Phase 5: DaVinci Resolve インポート

1. DaVinci Resolveで新規タイムライン作成
2. **File → Import → Timeline → FCP 7 XML**
3. `projects/OrionEp13/output/OrionEp13_timeline.xml` を選択
4. タイムラインに全音声クリップが配置される

## 🔍 トラブルシューティング

### 字幕のギャップ問題
**症状**: 生成されたSRTに数秒のギャップがある

**原因**: `ep{N}.srt` とナレーション原稿のテキスト不一致

**解決策**:
1. パイプライン出力の警告を確認：`⚠️ X subtitles could not be matched`
2. `ep{N}.srt` のエントリをナレーション原稿と1対1対応させる
3. 句読点・改行を統一（テキストマッチング精度向上）

### TTS生成エラー
**症状**: Gemini API エラー

**原因**: API rate limit または無効なSSML

**解決策**:
- `--delay` パラメータを増やす（デフォルト: 3.0秒 → 5.0秒）
- SSML構文を確認（`<sub alias>`, `<break time>` の閉じタグ）

### タイムコード不整合
**症状**: DaVinci Resolveで音声位置がずれる

**確認**:
1. `OrionEp{N}_timeline.csv` でタイムコード確認
2. セクションギャップが正しく3秒挿入されているか確認
3. `is_scene_start=YES` の行を確認

## 🚦 開発ステータス

- ✅ **EP12完成**（リファレンス実装）
- ✅ **コアパイプライン安定版**（v2.0）
- ✅ **SSML対応テキストマッチング**
- 🔧 **SRT自動生成機能**（Phase 2実装予定）
- 🔧 **統合CLIツール**（設計段階）
- 📋 **EP13以降の制作準備完了**

## 📊 パフォーマンス

- **TTS生成**: ~10-15秒/セグメント（Gemini API）
- **パイプライン実行**: ~2-5秒（81セグメント）
- **合計所要時間**: 約15-20分（EP12実績）

## 🧪 参考: 旧バージョン（Archive）

旧実装は `archive/` に保存されています：

- `archive/minivt_pipeline/` - ElevenLabs TTS版（初期バージョン）
- `archive/experiments/` - 各種実験コード
- `archive/prototype-legacy/` - その他プロトタイプ

**新規開発には `orion/` を使用してください。**

## 📜 ライセンス

MIT License - 詳細は [LICENSE](LICENSE) ファイルを参照

## 🤝 貢献

バグ報告や機能リクエストはIssueでお願いします。

## 🙏 謝辞

- [Google Gemini API](https://ai.google.dev/) - 高品質TTS
- [DaVinci Resolve](https://www.blackmagicdesign.com/products/davinciresolve) - プロフェッショナル動画編集
- Python コミュニティ - 優秀なライブラリ群

---

**作成者**: Hiroshi Kodera
**プロジェクト**: Orion Production Pipeline
**最終更新**: 2024年10月
