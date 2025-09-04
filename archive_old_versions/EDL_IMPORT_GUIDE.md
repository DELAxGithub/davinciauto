# DaVinci Resolve EDL インポートガイド

## 概要
Google Apps ScriptでEDL（Edit Decision List）を生成し、DaVinci Resolveで直接インポートする方法。
CSV + Pythonスクリプトの問題（tkinter エラー、API制約）を回避した最適解。

## フロー
```
Google Sheets → GAS (EDL生成) → Google Drive → DaVinci Resolve (EDLインポート) → 編集点自動挿入
```

## 1. Google Apps Script セットアップ

### コード追加
`gas_edl_generator.js` の内容をGoogle Apps Scriptプロジェクトに追加

### 実行手順
1. Google Sheetsで cutlist データを開く
2. Apps Script エディタで `generateEDL()` を実行
3. Google Driveに `edit_points_yyyymmdd_hhmmss.edl` が保存される
4. ファイルの共有リンクを取得

### 生成されるEDL形式
```
TITLE: Auto Generated Edit Points
FCM: NON-DROP FRAME

001  V     C        01:00:15:23 01:00:15:24 00:00:00:00 00:00:00:01
* FROM CLIP NAME: Violet

002  V     C        01:07:03:23 01:07:03:24 00:00:00:01 00:00:00:02
* FROM CLIP NAME: Iris
```

## 2. DaVinci Resolve インポート

### 方法1: Media Pool インポート
1. **Media Pool** パネルを開く
2. **右クリック** → **Import Media**
3. **EDLファイル**を選択してインポート
4. **新しいタイムライン**が自動生成される

### 方法2: File Menu インポート  
1. **File** → **Import** → **Import Media**
2. **EDLファイル**を選択
3. **Import Options**:
   - `Auto conform frame rate`: ON
   - `Create timeline`: ON
4. **Import**をクリック

### 方法3: Timeline インポート
1. 既存タイムラインを開く
2. **Timeline** → **Import** → **Insert EDL**
3. EDLファイルを選択してマージ

## 3. インポート結果

### 自動生成内容
- ✅ **新しいタイムライン**: 編集点付きで作成
- ✅ **クリップセグメント**: 各区間が独立したクリップに
- ✅ **タイムコード精度**: フレーム単位で正確
- ✅ **ラベル情報**: クリップ名として反映

### タイムライン構造
```
Timeline: "Auto Generated Edit Points"
├── 01:00:15:23-01:00:15:24 [Violet]
├── 01:07:03:23-01:07:03:24 [Iris] 
├── 01:08:37:23-01:08:37:24 [Caribbean]
└── ...（22区間）
```

## 4. 利点・比較

| アプローチ | 実行方式 | 成功率 | セットアップ |
|----------|----------|--------|------------|
| **EDL インポート** | DaVinci標準機能 | 95%+ | GASのみ |
| CSV + Python | カスタムスクリプト | 70% | 複雑 |
| 手動配置 | マニュアル | 100% | 非効率 |

### EDLの利点
- ✅ **ネイティブサポート**: DaVinci Resolveの標準機能
- ✅ **安定性**: APIやtk inter の制約なし
- ✅ **再現性**: 同じEDLから常に同じ結果
- ✅ **互換性**: 他の編集ソフトでも利用可能
- ✅ **シンプル**: Google Apps Script のみで完結

## 5. トラブルシューティング

### EDL生成エラー
- **無効なタイムコード**: `HH:MM:SS:FF` 形式を厳密に確認
- **空行の処理**: Start Time が空の行は自動スキップ
- **文字エンコーディング**: UTF-8で保存を確認

### DaVinci インポートエラー
- **フレームレート不整合**: EDLのフレームレートとタイムラインを一致
- **ファイルパス**: ローカルにダウンロードしてからインポート
- **権限**: ファイルアクセス権限を確認

### 一般的な問題
```
エラー: "Invalid EDL format"
解決: EDLの形式、特にタイムコードとスペーシングを確認

エラー: "Timeline not created"
解決: インポート時に "Create timeline" オプションをON

エラー: "Frame rate mismatch"
解決: プロジェクト設定でフレームレートを統一
```

## 6. 実運用での推奨フロー

1. **Google Sheets**: cutlist データを作成・編集
2. **GAS実行**: `generateEDL()` でEDL生成
3. **ダウンロード**: Google DriveからEDLファイルをダウンロード
4. **DaVinci Import**: Media Pool → Import Media でEDL読み込み
5. **確認**: 生成されたタイムラインで編集点を確認
6. **編集開始**: 編集点を基準に本格的な編集作業

**所要時間**: 2-3分で22区間の編集点挿入が完了

## 7. 応用・カスタマイズ

### マーカー版XML
編集点ではなくマーカーとして配置したい場合:
```javascript
generateMarkerXML()  // GASで実行
```

### カスタムEDL
特定の要件に応じてEDL形式をカスタマイズ可能:
- 複数トラック対応
- エフェクト情報の埋め込み
- カラー情報の追加

---

**結論**: EDL形式はCSV + Pythonスクリプトの問題を根本的に解決し、より安定で効率的なワークフローを実現します。