# Mini VTR Automation Pipeline

**8分間の教育動画自動生成パイプライン** - スクリプトからDaVinci Resolve用素材まで一貫制作

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python: 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)]()
[![DaVinci Resolve](https://img.shields.io/badge/DaVinci_Resolve-18+-red.svg)]()

## 🎯 概要

Mini VTR Automation Pipeline は、テキストスクリプトから高品質な教育動画素材を自動生成するPythonパイプラインです。ElevenLabs TTSを使用した多声優音声生成、日本語対応字幕システム、DaVinci Resolve連携により、効率的な動画制作ワークフローを実現します。

**主要機能:**
- 📝 役割別音声合成 (ナレーター・対話キャラクター)
- 🎵 音声タイムライン自動生成
- 📺 日本語2行字幕自動作成・時間同期
- 🎬 DaVinci Resolve直接インポート
- 🔧 プロフェッショナル制作ワークフロー対応

## 🚀 クイックスタート

### 1. インストール

```bash
git clone https://github.com/yourusername/davinciauto.git
cd davinciauto/minivt_pipeline
pip install -r requirements.txt
```

### 2. 環境設定

`.env` ファイルを作成:

```bash
# ElevenLabs TTS（必須）
ELEVENLABS_API_KEY=your_elevenlabs_api_key
ELEVENLABS_VOICE_ID_NARRATION=voice_id_for_narration
ELEVENLABS_VOICE_ID_DIALOGUE=voice_id_for_dialogue

# パフォーマンス調整（オプション）
HTTP_TIMEOUT=30
RATE_LIMIT_SLEEP=0.35
```

### 3. スクリプト作成

`data/` フォルダにスクリプトファイルを作成:

```
NA: 今日は人工知能について学習しましょう。
セリフ: AIって本当にすごいですね！
NA: そうです。特に機械学習の分野では著しい進歩があります。
セリフ: 具体的にはどのような用途があるのでしょうか？
```

### 4. パイプライン実行

```bash
# 完全実行
python src/pipeline.py --script data/your_script.txt

# テスト実行（音声生成なし）
python src/pipeline.py --script data/your_script.txt --fake-tts

# 再生速度調整
python src/pipeline.py --script data/your_script.txt --rate 1.2
```

### 5. DaVinci Resolve連携

1. `src/resolve_import.py` をDaVinci ResolveのScriptsフォルダにコピー
2. DaVinci Resolve で **Workspace → Scripts → Edit → resolve_import** を実行
3. 生成された `output/subtitles/script.srt` を選択してインポート

## 📁 プロジェクト構造

```
minivt_pipeline/
├── src/
│   ├── pipeline.py           # メインパイプライン
│   ├── resolve_import.py     # DaVinci Resolve連携
│   ├── clients/
│   │   ├── tts_elevenlabs.py # ElevenLabs TTS
│   │   └── gpt_client.py     # GPT連携（今後）
│   └── utils/
│       ├── srt.py            # 字幕生成
│       └── wrap.py           # 日本語テキスト整形
├── data/                     # スクリプトファイル
├── output/
│   ├── audio/                # 生成音声
│   └── subtitles/           # 字幕ファイル
├── docs/                     # 詳細ドキュメント
└── requirements.txt
```

## 🎨 特徴的機能

### 多声優音声システム
- **NA:** ナレーション専用音声
- **セリフ:** 対話キャラクター音声
- 役割自動認識・音声切り替え

### 日本語対応字幕
- 自動2行改行（句読点ベース）
- 音声同期タイムコード生成
- DaVinci Resolve標準SRT形式

### プロ制作ワークフロー
- ElevenLabs高品質TTS
- レート制限・エラー回復
- バッチ処理対応

## 📚 詳細ドキュメント

- **[ユーザーガイド](docs/USER_GUIDE.md)** - 完全な使用方法、トラブルシューティング
- **[API仕様](docs/API.md)** - 関数リファレンス、パラメータ詳細  
- **[DaVinci導入チェック表](DaVinci_導入チェック表.md)** - Resolve連携トラブル解決

## 🛠️ システム要件

- **Python**: 3.11以上
- **DaVinci Resolve**: 18以上（Scripts API有効）
- **ElevenLabs API**: 有効なAPIキー
- **OS**: Windows, macOS, Linux

## 🔧 開発・カスタマイズ

### テスト実行
```bash
# 最小限テスト
python src/pipeline.py --script data/short_test.txt --fake-tts

# デバッグモード
python debug_split.py
```

### 主要設定ファイル
- `requirements.txt` - Python依存関係
- `.env` - 環境変数設定
- `src/clients/tts_elevenlabs.py` - TTS設定
- `src/utils/wrap.py` - 日本語改行ルール

## 🚨 トラブルシューティング

### よくある問題
1. **ElevenLabs API制限** → レート制限設定確認
2. **DaVinci Resolve接続失敗** → Developer設定有効化
3. **日本語字幕文字化け** → UTF-8エンコーディング確認
4. **音声生成失敗** → APIキー・音声ID確認

詳細は [DaVinci導入チェック表](DaVinci_導入チェック表.md) を参照してください。

## 📈 パフォーマンス

- **TTS生成**: ~2-3秒/行（シーケンシャル処理）
- **字幕生成**: ~0.1秒（即座）
- **DaVinci連携**: ~1-2秒（自動インポート）
- **最適化可能性**: 70%高速化（並列TTS処理）

## 🤝 コントリビューション

1. このリポジトリをフォーク
2. フィーチャーブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. ブランチをプッシュ (`git push origin feature/amazing-feature`)  
5. プルリクエストを作成

## 📄 ライセンス

このプロジェクトは MIT License の下でライセンスされています - 詳細は [LICENSE](LICENSE) ファイルを参照してください。

## 🙏 謝辞

- [ElevenLabs](https://elevenlabs.io/) - 高品質TTS API
- [DaVinci Resolve](https://www.blackmagicdesign.com/products/davinciresolve) - プロフェッショナル動画編集
- Python コミュニティ - 優秀なライブラリ群

---

**作成者**: [Your Name](https://github.com/yourusername)  
**プロジェクト**: Mini VTR Automation Pipeline  
**更新日**: 2025年1月