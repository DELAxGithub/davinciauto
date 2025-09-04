# 🎬 DaVinci Resolve CSVマーカーシステム

Google Apps ScriptとDaVinci Resolveを連携した、ラジオ番組編集用の自動マーカー生成システム。アウト点対応版。

## 🎯 システム概要

**同一色の連続区間を単一のデュレーションマーカーに変換**
- Google Sheets で色分け選択
- 連続する同色区間 → 1つのデュレーションマーカー  
- DaVinciのScriptsメニューから直接実行

## 📋 ワークフロー

### 1. Google Sheets 処理

**必要なファイル**: `gas_final_complete.js`

1. **データ準備**: 元の文字起こしデータをGoogle Sheetsに貼り付け
2. **Step 1**: `executeStep1()` - タイムコードと文字起こしをペア化
3. **Step 2**: `executeStep2()` - 色選択（使う=色付け、使わない=空白）
4. **Step 3**: `executeStep3()` - 同一色区間のデュレーションマーカー生成

### 2. CSV出力

- 「DaVinciMarkers」シートが自動生成される
- ファイル → ダウンロード → CSV で保存
- 推奨ファイル名: `ダビンチマーカー - DaVinciMarkers.csv`

### 3. DaVinci Resolve インポート

**🎬 DaVinciで実行 (メニュー方式 - 推奨！)**

```
ワークスペース → スクリプト → Edit → DaVinci_CSV_Marker_Import
```

**自動機能**:
- ✅ 最新CSVファイルの自動検出（ダウンロードフォルダ）
- ✅ アウト点情報の自動計算・表示
- ✅ プロジェクト/タイムライン自動認識
- ✅ 新旧CSV形式両対応
- ✅ エラーハンドリング
- ✅ 処理結果の詳細レポート

## 🔧 技術仕様

### データ形式

**Input**: Google Sheetsの文字起こしデータ
```
[01:30:05-01:31:00] 重要な発言内容...
[01:31:01-01:33:15] さらに続く内容...
```

**Output**: CSV マーカーデータ（新形式 - アウト点対応）
```csv
timecode_in,timecode_out,marker_name,color,note,duration_frames,keywords
00:01:30:05,00:01:45:10,001_rose_区間,rose,重要な発言です...,375,重要,発言
```

**マーカーnote形式**:
```
元のnote | アウト点: 00:01:45:10 | キーワード: 重要,発言
```

### 色マッピング

| Google Apps Script | DaVinci Resolve | 用途例 |
|-------------------|-----------------|--------|
| `rose` | Red | 重要内容 |
| `mint` | Green | 料理・園芸 |
| `lemon` | Yellow | コマーシャル |
| `cyan` | Cyan | オープニング |
| `lavender` | Purple | 対談・討論 |
| `sky` | Cyan | まとめ・終了 |

### フレーム計算

- **25fps固定**
- タイムライン開始フレーム自動調整
- デュレーションマーカーの正確な時間計算

## 📁 ファイル構成

```
davinciauto/
├── gas_final_complete.js                    # Google Apps Script (完全版)
├── DaVinci_CSV_Marker_Import.py            # DaVinciメニュー用（推奨）
├── davinci_console_marker.py               # DaVinciコンソール用
├── test_duration_markers.csv               # テスト用サンプルデータ
├── FINAL_INSTRUCTIONS.md                   # 最終版使用手順
├── README_CSV_MARKER_SYSTEM.md             # このファイル
└── archive_old_versions/                   # 旧バージョンファイル
```

## 🚀 セットアップ

### Google Apps Script

1. Google Sheetsを開く
2. 拡張機能 → Apps Script
3. `gas_final_complete.js` の内容をコピペ
4. 保存して、スプレッドシートを再読み込み
5. メニューに「🎬 DaVinci マーカー生成」が表示される

### DaVinci Resolve

**手動インストール手順**:
1. `DaVinci_CSV_Marker_Import.py` をコピー
2. DaVinci Resolveスクリプトフォルダに配置:
   ```
   /Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Resources/
   Fusion/Scripts/Edit/DaVinci_CSV_Marker_Import.py
   ```
3. DaVinci Resolve再起動

**使用方法**:
```
ワークスペース → スクリプト → Edit → DaVinci_CSV_Marker_Import
```

## 💡 使用のポイント

### Google Sheets側

- **空白 = 使わない**: 色を選択しない行はマーカー生成されない
- **同一色連続 = 1つのマーカー**: 連続する同色区間が1つのデュレーションマーカーになる
- **プルダウン選択**: D列で色を選択、背景色が自動で変わる

### DaVinci側

- **自動検出**: Downloadsフォルダから最新CSVを自動検出
- **手動選択**: 必要に応じてファイル選択ダイアログも使用可能
- **エラー処理**: 接続エラー、ファイルエラーを適切にハンドリング

## 🎯 修正されたポイント

**以前の問題**: 各行に個別マーカーが作成されていた
**現在の実装**: 同一色の連続区間に単一のデュレーションマーカー

```
❌ 旧方式: 行1 → マーカー1, 行2 → マーカー2, 行3 → マーカー3
✅ 新方式: 行1-3(同色) → 1つのデュレーションマーカー
```

## 🔍 トラブルシューティング

### よくあるエラー

1. **"DaVinci Resolveに接続できません"**
   - DaVinciが起動しているか確認
   - プロジェクトが開いているか確認

2. **"タイムラインが選択されていません"**
   - Edit ページでタイムラインを選択
   - タイムラインが作成されているか確認

3. **"ファイルが見つかりません"**
   - CSVファイルがDownloadsフォルダにあるか確認
   - ファイル名が正しいか確認

### デバッグ

DaVinciのコンソール (Workspace → Console) でエラーメッセージを確認可能。

---

## 📞 サポート

システムに関する質問や改善提案は、このREADMEを参照してください。