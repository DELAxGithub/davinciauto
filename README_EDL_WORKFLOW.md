# DaVinci Resolve EDL経由自動分割システム

> **親方の格付け**: ①EDL経由(本命) ②マーカー半自動(次善) ③PyAutoGUI(論外)

業界標準のEDL（Edit Decision List）経由でDaVinci Resolveの自動分割を実現するシステム。確実性と安定性を重視した実装。

## 🎯 システム概要

### Core Concept
- **確実性重視**: PyAutoGUI等の不安定な手法を完全排除
- **業界標準準拠**: EDLフォーマットによるネイティブな連携
- **ワークフロー分離**: Python=EDL生成、DaVinci=インポート処理
- **フォールバック完備**: EDL失敗時の自動マーカーモード切り替え

### アーキテクチャ
```
CSV編集点データ
    ↓
Python EDLジェネレーター
    ↓
標準EDLファイル (.edl)
    ↓
DaVinci Resolve EDLインポート
    ↓
自動タイムライン生成（編集点付き）
```

## 🚀 クイックスタート

### 1. 基本的な使用方法
```bash
# EDL経由で自動分割（推奨）
python davinci_auto_split.py davinci_autocut/data/markers.csv

# マーカー半自動フォールバック
python davinci_auto_split.py --mode marker davinci_autocut/data/markers.csv
```

### 2. DaVinci Resolveでの取り込み
1. **Media Pool** → 右クリック → **Import Media**
2. 生成された **EDLファイル** を選択
3. **新しいタイムライン** が編集点付きで自動作成
4. **編集開始**！

### 3. 実行結果の例
```
🎬 DaVinci Resolve 自動分割システム
✅ EDL生成成功: 4個の編集点
📁 output/davinci_cuts_20250903_221827.edl

🚀 次の手順:
   1. DaVinci Resolveを開く
   2. Media Pool → 右クリック → Import Media
   3. 生成されたEDLファイルを選択
   4. 新しいタイムラインが編集点付きで作成されます
```

## 📁 ファイル構成

```
davinciauto/
├── davinci_auto_split.py          # 統合メインスクリプト
├── generate_edl.py                # EDLジェネレーター
├── davinci_autocut/
│   ├── data/markers.csv           # サンプル編集点データ
│   └── lib/resolve_utils.py       # タイムコード計算ユーティリティ
├── output/                        # EDLファイル出力先
├── gas_edl_generator.js           # 既存JavaScript実装（参考）
├── EDL_IMPORT_GUIDE.md           # DaVinciインポート手順書
└── README_EDL_WORKFLOW.md        # このファイル
```

## 📊 CSV入力フォーマット

### 基本形式
```csv
In,Out,Name
01:01:23:12,01:02:10:00,シーン1
01:03:05:00,01:03:20:10,シーン2
01:05:15:05,01:06:30:20,シーン3
01:08:00:00,,シーン4
```

### サポートするカラム名（大文字小文字・空白を自動正規化）
- **必須**: `In` / `Start Time` / `Start_Time`
- **オプション**: `Out` / `End Time` / `End_Time`（省略時は1フレーム自動追加）
- **オプション**: `Name` / `Label`（省略時は自動生成）

### タイムコード形式
- **標準**: `HH:MM:SS:FF` (例: `01:23:45:12`)
- **自動変換**: `H:MM:SS:FF` → `01:23:45:12`
- **バリデーション**: 無効フォーマットは警告付きでスキップ

## 🛠️ 高度な使用方法

### 1. コマンドラインオプション

```bash
# 基本実行
python davinci_auto_split.py data.csv

# フレームレート指定
python davinci_auto_split.py --fps 24 data.csv

# 出力ファイル指定
python davinci_auto_split.py --output custom.edl data.csv

# EDLタイトル指定
python davinci_auto_split.py --title "My Project Cuts" data.csv

# 強制フォールバックモード
python davinci_auto_split.py --force-fallback data.csv

# ヘルプ表示
python davinci_auto_split.py --help
```

### 2. EDL単独生成

```bash
# シンプルEDL生成
python generate_edl.py davinci_autocut/data/markers.csv

# カスタム設定
python generate_edl.py --fps 30 --output custom.edl --title "My Cuts" data.csv
```

### 3. プログラムでの利用

```python
from generate_edl import EDLGenerator

# EDLジェネレーター作成
generator = EDLGenerator(frame_rate=25)

# CSV読み込み
edit_points = generator.load_csv("data/markers.csv")

# EDL生成
edl_content = generator.generate_edl(edit_points, title="My Project")

# ファイル保存
generator.save_edl(edl_content, "output/my_cuts.edl")
```

## 🔧 技術仕様

### EDLフォーマット仕様
```
TITLE: Auto Generated Edit Points
FCM: NON-DROP FRAME

001  V     C        01:01:23:12 01:02:10:00 00:00:00:00 00:00:00:01
* FROM CLIP NAME: シーン1

002  V     C        01:03:05:00 01:03:20:10 00:00:00:01 00:00:00:02
* FROM CLIP NAME: シーン2
```

### エラーハンドリング
- **タイムコード検証**: 無効形式の自動検出と警告
- **CSV構造チェック**: 必須フィールドの存在確認
- **自動フォールバック**: EDL失敗時のマーカーモード切り替え
- **詳細エラー報告**: 行番号付きエラーメッセージ

### パフォーマンス
- **処理速度**: < 5秒（数百編集点まで）
- **メモリ効率**: CSVストリーミング読み込み
- **ファイルサイズ**: EDL = CSV行数 × 約100bytes

## 🎯 動作確認・品質保証

### テストケース実行
```bash
# 正常ケース
python davinci_auto_split.py davinci_autocut/data/markers.csv

# エラーハンドリング
echo "In,Name" > test_error.csv
echo "invalid,Test" >> test_error.csv
python davinci_auto_split.py test_error.csv
```

### 期待される出力
- ✅ EDLファイル生成完了メッセージ
- ✅ 編集点数の正確なカウント
- ✅ DaVinciでのインポート手順表示
- ⚠️ エラー時の詳細メッセージとフォールバック

### DaVinciでの検証
1. **Media Pool Import**: EDLファイルの正常読み込み
2. **Timeline Generation**: 編集点付きタイムライン作成
3. **Timecode Accuracy**: フレーム単位での正確性
4. **Clip Naming**: ラベル情報の正確な反映

## 🚨 トラブルシューティング

### よくある問題と解決策

#### 1. CSVエラー
```
❌ CSVファイル読み込みエラー: 'utf-8' codec can't decode
解決: CSVファイルをUTF-8で保存し直す
```

#### 2. タイムコードエラー
```
⚠️  行2: 無効なタイムコード形式: 1:23:45:12
解決: HH:MM:SS:FF形式（01:23:45:12）に修正
```

#### 3. DaVinciインポートエラー
```
エラー: "Invalid EDL format"
解決: 
- EDLファイルのフォーマットを確認
- プロジェクトフレームレートを統一
- ローカルファイルパスを確認
```

#### 4. フォールバック発動
```
🔄 EDLモード失敗 → フォールバックモードに切り替え
対応: マーカー手動配置の指示に従う
```

### デバッグ情報収集
```bash
# 詳細分析実行
python -c "
from generate_edl import EDLGenerator
gen = EDLGenerator()
result = gen.load_csv('your_file.csv')
print(f'Loaded: {len(result)} points')
for p in result[:3]: print(p)
"
```

## 📈 パフォーマンス最適化

### 大量データ対応
- **バッチ処理**: 数千編集点まで対応
- **メモリ効率**: ストリーミング処理で低メモリ消費
- **処理速度**: 多スレッド対応（将来実装）

### 品質監視
- **エラー率監視**: 無効データの比率追跡
- **処理時間測定**: パフォーマンス回帰検出
- **成功率追跡**: DaVinciインポート成功率

## 🔮 今後の拡張予定

### Phase 1: 機能強化
- [ ] 複数トラック対応EDL生成
- [ ] カラー情報のEDL埋め込み
- [ ] XMLマーカー形式の並行サポート

### Phase 2: 統合強化
- [ ] DaVinci Resolve API直接連携
- [ ] リアルタイム同期機能
- [ ] 複数フレームレート自動対応

### Phase 3: UX向上
- [ ] GUI版ツール
- [ ] ドラッグ&ドロップ対応
- [ ] プレビュー機能

## 📞 サポート・フィードバック

### 問題報告
問題や改善要望は以下の情報と共に報告してください：

```bash
# システム情報収集
python --version
python davinci_auto_split.py --help
```

### 成功事例共有
- 処理した編集点数
- 実際の時間短縮効果
- DaVinciでの使用感

---

## 🏆 親方の格付け総括

| 手法 | 確実性 | 効率性 | 保守性 | 評価 |
|------|--------|--------|--------|------|
| **EDL経由** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 🏆 本命 |
| マーカー半自動 | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | 🥈 次善 |
| PyAutoGUI等 | ⭐ | ⭐⭐ | ⭐ | 🚫 論外 |

**結論**: EDL経由は業界標準で最も確実。親方の指導通り、この手法を採用することで安定したワークフローが実現されました。