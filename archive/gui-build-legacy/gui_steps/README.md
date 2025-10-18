# 🎬 DaVinci Auto Workflow - GUI版

8分動画制作自動化パイプライン GUI実装

## 📋 概要

スクリプト入力からDaVinci Resolve最終出力まで、動画制作ワークフローを4ステップでGUI化。

### ワークフロー
```
📝 Step 1: スクリプト編集    →    🎵 Step 2: TTS音声生成
       ↓                              ↓
🎬 Step 4: DaVinci出力     ←    ⏰ Step 3: 字幕タイミング
```

## 🚀 クイックスタート

### 1. 統合ランチャー（推奨）
```bash
cd gui_steps
python3 run_all_steps.py
```

### 2. 個別ステップ実行
```bash
# Step 1: スクリプト編集・配役設定
python3 step1_script_editor.py

# Step 2: TTS音声生成
python3 step2_tts_generation.py      # フル版
python3 step2_minimal_test.py        # テスト版（依存関係不要）

# Step 3: 字幕タイミング調整
python3 step3_subtitle_timing.py

# Step 4: DaVinci Resolve出力
python3 step4_davinci_export.py
```

## 📁 ファイル構成

```
gui_steps/
├── run_all_steps.py              # 🎯 統合ランチャー
├── step1_script_editor.py        # 📝 スクリプト編集GUI
├── step2_tts_generation.py       # 🎵 TTS生成GUI（フル版）
├── step2_minimal_test.py         # 🧪 TTS生成GUI（テスト版）
├── step3_subtitle_timing.py      # ⏰ 字幕調整GUI
├── step4_davinci_export.py       # 🎬 DaVinci出力GUI
├── common/
│   ├── gui_base.py               # 共通GUI基底クラス
│   └── data_models.py            # データ構造定義
└── README.md                     # このファイル
```

## 🎯 各ステップ詳細

### Step 1: スクリプト編集・配役設定
- **シンタックスハイライト**: NA:/セリフ:の色分け表示
- **キャラクター自動抽出**: スクリプトからキャラクター名を自動検出
- **音声指示解析**: （男声・疲れ切った声で）等の音声指示を解析
- **配役管理**: キャラクター別音声ID・性別設定
- **プロジェクト保存**: JSON形式での設定永続化

### Step 2: TTS音声生成
- **バッチTTS生成**: ElevenLabs APIを使用した一括音声生成
- **並列処理対応**: 同時実行数設定可能（実験的機能）
- **リアルタイム進捗**: 全体・現在行の2段階進捗表示
- **音声プレビュー**: 生成音声の即座再生（pygame使用）
- **再生成機能**: 問題のある行のみ個別再生成
- **コスト追跡**: リアルタイム見積もり・実績表示

### Step 3: 字幕タイミング調整
- **自動タイミング生成**: スクリプトまたは音声ファイルから自動生成
- **視覚的タイムライン**: 直感的な時間軸表示・編集
- **精密調整機能**: ±0.1秒・±1秒の微調整ボタン
- **リアルタイムプレビュー**: 字幕表示状態の即座確認
- **SRT出力**: 標準字幕形式でのエクスポート
- **統計機能**: 表示時間・文字数等の分析

### Step 4: DaVinci Resolve出力
- **API自動接続**: DaVinci Resolve Studioとの連携
- **SRT自動インポート**: 字幕ファイルの自動読み込み
- **レンダリングプリセット**: YouTube HD/4K等の最適化設定
- **Export Queue管理**: レンダリングキューの追加・監視
- **プロジェクト保存**: 作業内容の自動保存

## ⚙️ システム要件

### 基本要件
- **Python**: 3.8以上
- **OS**: macOS, Windows, Linux
- **メモリ**: 4GB以上推奨

### 依存パッケージ
```bash
# 基本GUI（全ステップ共通）
tkinter  # Python標準ライブラリ

# Step 2 フル版
requests            # ElevenLabs API通信
pygame             # 音声再生（fallback対応）
pydub              # 音声ファイル処理

# 既存パイプライン統合
../minivt_pipeline/requirements.txt  # 参照
```

### オプション要件
- **DaVinci Resolve Studio**: Step 4で必要（無料版はAPI制限あり）
- **ElevenLabs API Key**: Step 2のTTS生成で必要

## 🔧 設定

### 環境変数
```bash
export ELEVENLABS_API_KEY="your_api_key_here"
export ELEVENLABS_VOICE_ID="default_voice_id"
export ELEVENLABS_VOICE_ID_NARRATION="narration_voice_id"  
export ELEVENLABS_VOICE_ID_DIALOGUE="dialogue_voice_id"
```

### プロジェクト設定
- プロジェクトファイル（JSON）で設定を永続化
- ステップ間で自動的にデータ引き継ぎ
- 途中保存・再開可能

## 🎮 使用方法

### 基本ワークフロー
1. **統合ランチャー起動**: `python3 run_all_steps.py`
2. **サンプルプロジェクト作成**: クイックアクション → サンプルプロジェクト作成
3. **Step 1実行**: スクリプト編集・配役設定
4. **Step 2実行**: TTS音声生成（テスト版推奨）
5. **Step 3実行**: 字幕タイミング調整
6. **Step 4実行**: DaVinci Resolve出力

### プロジェクト管理
- **新規作成**: 各ステップで「新規プロジェクト」
- **保存**: 自動保存または手動保存
- **読み込み**: プロジェクトファイル（.json）から再開
- **ステップ間移動**: ナビゲーションボタンで瞬時移動

## 🎨 GUI機能

### 共通機能
- **ステップナビゲーション**: 4ステップ間の瞬時移動
- **現在ステップ表示**: アクティブステップのハイライト
- **プロジェクト管理**: 統一されたプロジェクト保存・読み込み
- **ステータス表示**: リアルタイム作業状況表示

### Step別特徴機能
- **Step 1**: シンタックスハイライト、キャラクター自動抽出
- **Step 2**: 並列処理、リアルタイム進捗、音声プレビュー
- **Step 3**: 視覚的タイムライン、精密時間調整
- **Step 4**: DaVinci API統合、レンダリング監視

## 🧪 テスト・デバッグ

### テスト版使用
```bash
# Step 2 テスト版（依存関係不要）
python3 step2_minimal_test.py
```

### デバッグ情報
- 各ステップにログ表示機能
- エラーメッセージの詳細表示
- 接続状態・進捗状況のリアルタイム更新

### トラブルシューティング
- **DaVinci接続エラー**: Studio版使用、アクティブプロジェクト確認
- **TTS生成エラー**: API Key設定、ネットワーク接続確認
- **依存関係エラー**: requirements.txt確認、仮想環境使用推奨

## 🔄 既存パイプラインとの関係

### 統合方針
- **既存コード活用**: `minivt_pipeline/src/` の機能を最大活用
- **GUI化**: コマンドライン機能をGUIでラップ
- **データ互換性**: 既存の出力形式・ファイル構造を維持
- **段階的移行**: CLI版とGUI版の並行利用可能

### ファイル連携
```
minivt_pipeline/
├── src/           # 既存ロジック（GUI版が呼び出し）
├── output/        # 共通出力フォルダ
└── data/          # 共通データフォルダ

gui_steps/         # GUI版（新規追加）
├── step*.py       # GUIフロントエンド
└── common/        # GUI共通機能
```

## 🎉 完了・次のステップ

### 完成機能
- ✅ 4ステップGUI完全実装
- ✅ プロジェクト管理システム
- ✅ ステップ間データ連携
- ✅ 既存パイプライン統合
- ✅ エラーハンドリング・フォールバック

### 今後の拡張予定
- [ ] プラグインシステム
- [ ] テンプレート機能
- [ ] クラウド連携
- [ ] 多言語対応

---

**🎬 Happy Video Production!**