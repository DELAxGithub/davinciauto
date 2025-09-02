# DaVinci Resolve スクリプト導入チェック表

## 🔍 基本環境チェック

### DaVinci Resolve 設定
- [ ] **DaVinci Resolve が起動している**
- [ ] **プロジェクトが開かれている** (空のプロジェクトでも可)
- [ ] **タイムラインが作成・選択されている**
- [ ] **Developer → Scripts** メニューが有効化されている

### Pythonスクリプト実行環境
- [ ] **Workspace → Scripts メニューが表示される**
- [ ] **Edit/Comp/Color ページでスクリプトメニューアクセス可能**
- [ ] **resolve_import.py がスクリプトフォルダに配置済み**

## 🛠️ スクリプト配置チェック

### ファイル配置確認
- [ ] **resolve_import.py の配置場所:**
  - Windows: `C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripts\Edit\`
  - macOS: `/Users/[username]/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripts/Edit/`
  - Linux: `/opt/resolve/Developer/Scripts/Edit/`

- [ ] **ファイル権限が実行可能に設定されている**
- [ ] **ファイル名に日本語・特殊文字が含まれていない**

## 📄 SRTファイル検証

### script.srt ファイル確認
- [ ] **SRTファイルが正しい場所に生成されている:**
  ```
  minivt_pipeline/output/subtitles/script.srt
  ```

- [ ] **SRTファイルの内容フォーマットが正しい:**
  ```
  1
  00:00:00,000 --> 00:00:03,000
  字幕テキスト行1
  字幕テキスト行2
  ```

- [ ] **ファイルサイズが 0 バイトでない**
- [ ] **文字エンコーディングがUTF-8**
- [ ] **改行コードが適切 (LF推奨)**

## 🔧 実行時トラブルシューティング

### スクリプト実行手順
1. [ ] **DaVinci Resolve で Workspace → Scripts → Edit → resolve_import を選択**
2. [ ] **ファイル選択ダイアログが表示される**
3. [ ] **SRTファイルを選択して開く**
4. [ ] **コンソールログで成功/エラーメッセージを確認**

### よくある問題と対処法

#### ❌ スクリプトメニューに表示されない
- **原因**: ファイル配置場所の間違い
- **対処**: 正しいScriptsフォルダに配置し直す
- **検証**: DaVinci Resolveを再起動してメニュー確認

#### ❌ "DaVinciResolveScript import failed"
- **原因**: DaVinci Resolve Developer機能が無効
- **対処**: Settings → General → Developer → External scripting using を有効化
- **検証**: DaVinci Resolveを再起動

#### ❌ "No active project/timeline"
- **原因**: プロジェクトまたはタイムラインが選択されていない
- **対処**: プロジェクトを開き、タイムラインを作成・選択
- **検証**: Edit ページでタイムライン表示を確認

#### ❌ "timeline.ImportSubtitles failed"
- **原因**: DaVinci ResolveバージョンによるAPI差異
- **対処**: 複数のインポート方法を自動試行（既に実装済み）
- **検証**: Media Poolに手動インポートで代替確認

#### ❌ SRTファイルが見つからない
- **原因**: パイプライン実行エラー、ファイル生成失敗
- **対処**: 
  ```bash
  cd minivt_pipeline
  python src/pipeline.py --script data/test_script.txt --fake-tts
  ls -la output/subtitles/
  ```

## 🧪 動作テスト手順

### 1. 最小限テスト
```bash
# テスト用SRTファイル生成
cd minivt_pipeline
python src/pipeline.py --script data/short_test.txt --fake-tts
```

### 2. DaVinci Resolve側テスト
- [ ] **Workspace → Scripts → Edit → resolve_import 実行**
- [ ] **output/subtitles/script.srt を選択**
- [ ] **成功メッセージ "[DONE] Subtitle imported" 確認**

### 3. インポート結果確認
- [ ] **タイムライン上に字幕トラックが追加される**
- [ ] **字幕の表示タイミングが適切**
- [ ] **日本語文字が正しく表示される**

## 📋 環境情報収集

問題が解決しない場合、以下の情報を収集:

### システム情報
- [ ] **OS**: (Windows/macOS/Linux + バージョン)
- [ ] **DaVinci Resolve バージョン**: 
- [ ] **Python バージョン**: `python --version`
- [ ] **スクリプト配置パス**: 

### ログ情報
- [ ] **パイプライン実行ログ**:
  ```bash
  python src/pipeline.py --script data/test_script.txt 2>&1 | tee pipeline.log
  ```
- [ ] **DaVinci Resolve コンソールログ** (スクリプト実行時の出力)
- [ ] **SRTファイル内容サンプル** (最初の数行)

## ✅ 成功確認チェックリスト

- [ ] **パイプライン実行完了**: audio/subtitles ファイル生成
- [ ] **DaVinci Resolve スクリプト実行成功**: エラーメッセージなし
- [ ] **タイムラインに字幕トラック表示**: 適切なタイミングで字幕表示
- [ ] **日本語文字化け無し**: テキストが正しく読める
- [ ] **音声と字幕の同期**: 音声タイミングと字幕表示が一致

---

**トラブル時のヘルプ**: 上記チェックリストを確認の上、具体的なエラーメッセージとシステム情報をお知らせください。