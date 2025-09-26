# Mini VTR Automation Pipeline

**8分間の教育動画自動生成パイプライン** - スクリプトからDaVinci Resolve用素材まで一貫制作

> **New in 2025**: macOS ネイティブな SwiftUI GUI を廃止し、Python (PySide6) + PyInstaller で
> ワンクリック GUI を提供します。旧 Swift プロジェクトは 2024 年までのコミットに
> アーカイブされており、必要であれば Git の履歴から参照してください。下記の
> Quick Start を参照して PyInstaller ビルドをご利用ください。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python: 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)]()
[![DaVinci Resolve](https://img.shields.io/badge/DaVinci_Resolve-18+-red.svg)]()

## 🎯 概要

Mini VTR Automation Pipeline は、テキストスクリプトから高品質な教育動画素材を自動生成するPythonパイプラインです。Azure Speech Service (Azure TTS) を使用した多声優音声生成、日本語対応字幕システム、DaVinci Resolve連携により、効率的な動画制作ワークフローを実現します。

**主要機能:**
- 📝 役割別音声合成 (ナレーター・対話キャラクター)
- 🎵 音声タイムライン自動生成
- 📺 日本語2行字幕自動作成・時間同期
- 🎬 DaVinci Resolve直接インポート
- 🔧 プロフェッショナル制作ワークフロー対応

## 🚀 クイックスタート

### PyInstaller GUI

```bash
# 仮想環境と依存をインストール
make setup            # .venv が作成され、[cli,dev] 依存が入ります

# GUI を開いてパイプラインを実行
.venv/bin/python -m gui_app.main

# PyInstaller で OneDir バンドルを作成
pyinstaller/build_gui.sh
open "dist/DaVinciAuto GUI.app"
```

> **配布バンドルについて**
> - `pyinstaller/build_gui.sh` 実行後、`dist/DaVinciAuto GUI.app` と `dist/DaVinciAuto_GUI.dmg` が生成されます。
>   編集担当者へは DMG を配布し、「ダブルクリック → `DaVinciAuto GUI.app` を Applications にドラッグ」だけで導入完了です。
> - Azure Speech / ElevenLabs (TTS) / Stable Audio 依存、ffmpeg/ffprobe がバンドル済みなので追加の `pip install` は不要です。
> - 初回起動時はセットアップダイアログで API キーを入力するだけでナレーション/音声／BGMワークフローを利用できます。
>   ElevenLabs を使わない運用では GUI セットアップ画面の「ナレーション生成をスキップ」で音声ステップを抑止できます。

*Self-check* や Azure/ELEVEN API キーの登録、ウィザードによる入力保管、進捗ログの
閲覧などは GUI から操作できます。旧 Swift GUI は `archive/` 以下にアーカイブされており、
今後の開発は Python GUI に一本化します。

### CLI パイプライン

### 1. インストール

```bash
git clone https://github.com/yourusername/davinciauto.git
cd davinciauto/minivt_pipeline
pip install -r requirements.txt
```

### 2. 環境設定

`.env` ファイルを作成:

```bash
# Azure Speech Service（必須）
AZURE_SPEECH_KEY=your_azure_speech_key
AZURE_SPEECH_REGION=your_region
AZURE_SPEECH_VOICE_NARRATION=voice_name_for_narration
AZURE_SPEECH_VOICE_DIALOGUE=voice_name_for_dialogue

# Stable Audio（BGM/SE 自動生成）
STABILITY_API_KEY=your_stability_api_key

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
│   │   ├── tts_azure.py        # Azure TTS
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
- Azure高品質TTS
- レート制限・エラー回復
- バッチ処理対応

## 📚 詳細ドキュメント

- **[ユーザーガイド](docs/USER_GUIDE.md)** - 完全な使用方法、トラブルシューティング
- **[API仕様](docs/API.md)** - 関数リファレンス、パラメータ詳細
- **[編集者向け1枚もの](docs/EDITOR_ONE_PAGER.md)** - どこを自動化し、何を用意すれば良いか

## 🛠️ システム要件

- **Python**: 3.11以上
- **DaVinci Resolve**: 18以上（Scripts API有効）
- **Azure Speech Service**: APIキー・リージョン設定
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
- `src/clients/tts_azure.py` - TTS設定
- `src/utils/wrap.py` - 日本語改行ルール

## 🧪 実験・持ち込み素材

外部から持ち込むファイルや試行コードは `experiments/` に集約します。

```
experiments/
├── inbox/
│   ├── davinci/   # XML, DRP など
│   └── llm/       # LLM出力（json, md, txt）
└── scratch/       # 試行コード/一時出力
```

## 🚨 トラブルシューティング

### よくある問題
1. **Azure TTS制限** → レート制限設定確認
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

- [Azure Speech Service](https://azure.microsoft.com/products/cognitive-services/text-to-speech/) - 高品質TTS API
- [DaVinci Resolve](https://www.blackmagicdesign.com/products/davinciresolve) - プロフェッショナル動画編集
- Python コミュニティ - 優秀なライブラリ群

---

## 🎧 Project Audio Workflow (Resolve-ready)

以下は本リポ内のプロジェクト型ワークフロー（OrionEp2 の実装例）です。コマンドはプロジェクト名を入れ替えれば流用できます。

1) 音声生成（Azure TTS / Neural voices）

```bash
# 1–27行 / 28–63行（プロジェクト固有の台本を内包）
python scripts/generate_orionep2_lines_1_27.py
python scripts/generate_orionep2_lines_28_63.py
```

2) タイムラインCSV（秒ベース + 30fps）

```bash
python scripts/build_timeline_orionep2.py
# out: projects/OrionEp2/exports/timelines/OrionEp2_timeline_v1.csv
```

3) Resolveインポート用XML（FCP7互換）

```bash
python scripts/csv_to_fcpx7_from_timeline.py \
  projects/OrionEp2/exports/timelines/OrionEp2_timeline_v1.csv
# out: projects/OrionEp2/exports/timelines/OrionEp2_timeline_v1.xml
```

4) BGM/SE 生成（セクション設計 → 自動作曲/効果音）

```bash
# セクション設計
projects/OrionEp2/inputs/bgm_se_plan.json

# BGM + SFX 生成（自動ツール）
python scripts/generate_bgm_se_from_plan.py projects/OrionEp2/inputs/bgm_se_plan.json           # 両方
python scripts/generate_bgm_se_from_plan.py projects/OrionEp2/inputs/bgm_se_plan.json --only sfx # SFXのみ再実行
```

5) BGM 自動整音（LUFS/TP/LRA + フェード）

```bash
# -15 LUFS / -1 dBTP / LRA 11, FadeIn 1.0s / FadeOut 1.5s
python scripts/master_bgm_from_plan.py projects/OrionEp2/inputs/bgm_se_plan.json
```

6) ナレーション + BGM + SE を1本のXMLへ統合

```bash
python scripts/build_fcpx_with_bgm_se.py \
  projects/OrionEp2/exports/timelines/OrionEp2_timeline_v1.csv \
  projects/OrionEp2/inputs/bgm_se_plan.json \
  projects/OrionEp2/exports/timelines/OrionEp2_timeline_with_bgm_se_mastered.xml
```

7) Resolve でダッキング（テンプレート方式）
- テンプレートDRP内で A1=VO, A2=MUSIC, A3=SE を定義し、Fairlight のコンプレッサを MUSIC に挿入、サイドチェイン入力=VO。
- 推奨値: Ratio 4:1 / Attack 120ms / Release 250ms / 目標GR ≈ -7dB（スピーカ/楽曲に応じ調整）。


**作成者**: [Your Name](https://github.com/yourusername)  
**プロジェクト**: Mini VTR Automation Pipeline  
**更新日**: 2025年1月

## Codex hooks: 承認時にmacOS通知

- 追加スクリプト: `scripts/notify_mac.sh`, `scripts/codex_hook_approval_required.sh`
- 目的: Codex の承認/確認が必要になったタイミングで macOS のシステム通知を出す
- 仕組み: AppleScript (`osascript`) で通知を送信。追加の依存関係は不要。

使い方（Codex の hooks 機構に合わせて設定してください）:

- 承認・確認イベント（例: `approval_required`）で以下を実行するようにフック設定:

  `bash scripts/codex_hook_approval_required.sh "<理由や状況>" "<詳細(任意)>"`

例（擬似的な hooks 設定イメージ）:

```yaml
# codex.yaml 等に hooks がある場合のイメージ
hooks:
  approval_required:
    - ["bash", "scripts/codex_hook_approval_required.sh", "ファイル書き込みが必要", "対象: 作業ディレクトリ"]
  confirmation_required:
    - ["bash", "scripts/codex_hook_approval_required.sh", "確認が必要", "ネットワークアクセス"]
```

直接呼び出しテスト:

```bash
bash scripts/codex_hook_approval_required.sh "承認が必要です" "ネットワークアクセス"
```

補足:

- 通知音は `Submarine` を使用。`scripts/notify_mac.sh` 第4引数で変更可。
- Terminal や iTerm2 で通知が表示されない場合は、システム設定 > 通知 で許可を確認。
- Codex 側の hooks の具体的な設定ファイルやキー名はバージョン/ディストリによって異なるため、ご利用環境のドキュメントに従って上記コマンドを紐付けてください。
