# DaVinci Resolve 自動分割 運用ガイド

**実際の編集作業での使用方法とベストプラクティス**

## 🎬 日常的な使用フロー

### 1. 編集点データ準備

#### A. Excel/Google Sheetsで準備
```
1. CSVテンプレートをダウンロード（またはサンプルをコピー）
2. 編集点のタイムコードを入力（HH:MM:SS:FF形式）
3. シーン名・ラベルを追加
4. CSVファイルとして保存（UTF-8エンコーディング）
```

#### B. タイムコード入力のコツ
```
✅ 正しい形式: 01:23:45:12
❌ 間違い例: 1:23:45:12, 01:23:45,12, 1.23.45.12

💡 時短テクニック:
- Excelの時刻形式を使用して入力後、文字列形式に変換
- フレーム番号は手動で追加
- コピー&ペースト時は形式をテキストで貼り付け
```

### 2. EDL生成実行

#### シンプル実行
```bash
# 最も簡単な実行方法
python davinci_auto_split.py 編集点データ.csv
```

#### 実際の作業例
```bash
# プロジェクトディレクトリに移動
cd /path/to/your/project

# データ準備確認
ls -la data/
# → data/episode_01_cuts.csv があることを確認

# EDL生成実行
python /path/to/davinciauto/davinci_auto_split.py data/episode_01_cuts.csv

# 成功時の出力例
🎉 実行完了 - EDLモード
📁 output/davinci_cuts_20250903_145612.edl
```

### 3. DaVinci Resolveでの取り込み

#### Step-by-Step手順
```
1. DaVinci Resolveを起動
2. プロジェクトを開く（または新規作成）
3. Media Pool タブを開く
4. 空白部分で右クリック
5. "Import Media..." を選択
6. 生成されたEDLファイル（.edl）を選択
7. "Open" をクリック
```

#### 自動生成されるもの
```
✅ 新しいタイムライン
   - 名前: "Auto Generated Edit Points" (またはカスタム名)
   - 各編集点が独立したクリップとして配置
   
✅ クリップ命名
   - CSV の Name/Label カラムがクリップ名になる
   
✅ 正確なタイムコード
   - フレーム単位での正確な配置
```

### 4. 編集作業開始

#### 取り込み後の確認事項
```
□ タイムラインが正しく生成されているか
□ 編集点の数が期待通りか（CSVの行数と一致）
□ クリップ名が適切に設定されているか
□ タイムコードが正確か（抜き打ち数箇所確認）
```

#### 一般的な後続作業
```
1. 不要な編集点の削除
2. クリップの並び替え
3. トランジション効果の追加
4. 色調補正・音量調整
5. 字幕・テロップ追加
```

## ⚡ 時短テクニック集

### 1. CSVテンプレート活用

#### マスターテンプレート作成
```csv
In,Out,Name,Note
01:00:00:00,,オープニング,冒頭5秒
01:00:05:00,,メインコンテンツ開始,
01:10:00:00,,CM明け,
01:20:00:00,,エンディング,最後30秒
```

#### プロジェクト別コピー
```bash
# テンプレートをコピーして使用
cp template/cuts_template.csv projects/episode_01/cuts.csv
# エディタで編集
code projects/episode_01/cuts.csv
```

### 2. バッチ処理活用

#### 複数エピソード一括処理
```bash
#!/bin/bash
# 複数CSVファイルを一括処理

for csv_file in data/episode_*.csv; do
    echo "Processing: $csv_file"
    python davinci_auto_split.py "$csv_file"
done
```

#### フォルダ構造例
```
project/
├── data/
│   ├── episode_01_cuts.csv
│   ├── episode_02_cuts.csv
│   └── episode_03_cuts.csv
├── output/
│   ├── episode_01.edl
│   ├── episode_02.edl
│   └── episode_03.edl
└── scripts/
    └── batch_process.sh
```

### 3. 品質チェック自動化

#### チェックスクリプト例
```bash
#!/bin/bash
# 生成されたEDLファイルの簡易チェック

edl_file="$1"
if [ ! -f "$edl_file" ]; then
    echo "❌ EDLファイルが見つかりません: $edl_file"
    exit 1
fi

line_count=$(grep -c "^[0-9][0-9][0-9].*V.*C" "$edl_file")
echo "✅ 編集点数: $line_count"

if [ $line_count -eq 0 ]; then
    echo "⚠️  編集点が見つかりません"
    exit 1
fi

echo "✅ EDLファイル正常"
```

## 🔧 高度な運用パターン

### 1. プロジェクト統合

#### Makefileを使用した自動化
```makefile
# Makefile
PYTHON = python
SCRIPT = /path/to/davinciauto/davinci_auto_split.py

all: episode_01 episode_02 episode_03

episode_01:
	$(PYTHON) $(SCRIPT) data/episode_01_cuts.csv
	mv output/davinci_cuts_*.edl output/episode_01.edl

episode_02:
	$(PYTHON) $(SCRIPT) data/episode_02_cuts.csv
	mv output/davinci_cuts_*.edl output/episode_02.edl

clean:
	rm -f output/*.edl

.PHONY: all clean episode_01 episode_02 episode_03
```

#### 実行
```bash
make all          # 全エピソード処理
make episode_01   # 単一エピソード処理
make clean        # 生成物削除
```

### 2. 品質管理体制

#### 3段階チェック体制
```
□ Level 1: 自動検証
  - CSVフォーマット確認
  - タイムコード妥当性チェック
  - EDL生成成功確認

□ Level 2: 半自動検証  
  - DaVinciでのインポート確認
  - 編集点数の照合
  - サンプルタイムコード抜き打ち確認

□ Level 3: 手動確認
  - 実際の映像との照合
  - 編集意図との整合性確認
  - 最終品質承認
```

#### チェックリスト
```
□ CSVファイル
  - UTF-8エンコーディング
  - 必須カラム存在（In）
  - タイムコード形式（HH:MM:SS:FF）
  - 重複タイムコード無し

□ EDL生成
  - エラーメッセージ無し
  - 期待される編集点数
  - ファイルサイズ妥当性

□ DaVinciインポート
  - タイムライン生成成功
  - クリップ名正確
  - タイムコード精度
```

### 3. トラブルシュート手順

#### 一般的な問題対応フロー
```
1. エラーメッセージの確認
   ↓
2. CSVファイルの妥当性チェック
   ↓
3. サンプルデータでのテスト実行
   ↓
4. フォールバックモードの試行
   ↓
5. 手動マーカー配置での回避
```

#### 緊急時対応
```bash
# 最小限のテストケース作成
echo "In,Name" > emergency_test.csv
echo "01:00:00:00,Test" >> emergency_test.csv

# テスト実行
python davinci_auto_split.py emergency_test.csv

# 成功時 → 元データの問題
# 失敗時 → システムの問題
```

## 📊 運用メトリクス

### パフォーマンス指標

#### 効率性測定
- **手動作業時間**: 編集点1個あたり 30-60秒
- **自動処理時間**: 編集点1個あたり 0.1秒未満
- **時間短縮率**: 95%以上

#### 品質指標
- **タイムコード精度**: フレーム単位（±0フレーム）
- **成功率**: 95%以上（正常なCSVデータの場合）
- **エラー復旧率**: 100%（フォールバックモード含む）

### 定期監視項目

#### 月次レビュー
```
□ 処理したプロジェクト数
□ 総編集点数
□ エラー発生率
□ ユーザーフィードバック
□ システム改善点
```

## 🎯 ベストプラクティス

### 1. データ管理

#### フォルダ構造の標準化
```
project_name/
├── source/                  # 元映像ファイル
├── data/
│   ├── raw/                # 生のタイムコードデータ
│   └── processed/          # 処理済みCSVファイル
├── output/
│   ├── edl/               # EDLファイル
│   └── projects/          # DaVinciプロジェクトファイル
└── docs/
    ├── notes.md           # 編集ノート
    └── changelog.md       # 変更履歴
```

#### 命名規則
```
CSV: {project}_{episode}_{version}_cuts.csv
EDL: {project}_{episode}_{date}.edl
例: drama_s01e01_v2_cuts.csv → drama_s01e01_20250903.edl
```

### 2. チーム運用

#### 役割分担
```
□ データ作成者
  - CSVファイルの正確な入力
  - タイムコード検証
  
□ システム運用者  
  - EDL生成実行
  - エラー対応・トラブルシュート
  
□ 編集者
  - DaVinciでの最終取り込み
  - 品質確認・承認
```

#### コミュニケーション
```
□ 開始前
  - データ形式の確認
  - 特殊要件のヒアリング
  
□ 実行中
  - 進捗状況の共有
  - エラー発生時の即座な報告
  
□ 完了後
  - 成果物の確認
  - 品質チェック結果の共有
```

### 3. セキュリティ・バックアップ

#### データ保護
```
□ 定期バックアップ
  - CSVファイル: 日次
  - EDLファイル: 生成時即座
  - プロジェクトファイル: 作業完了時

□ バージョン管理
  - Git等でCSVファイル管理
  - 変更履歴の追跡
  - 差分確認機能活用
```

---

**このガイドは実際の編集現場での効率的な運用を想定して作成されています。プロジェクトの特性に応じて適切にカスタマイズしてご使用ください。**