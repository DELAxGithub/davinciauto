# SPEC-030: 起動時 Self-check

## チェック項目 (MUST)
1. **Qt プラグイン**: PySide6 で最小ウィジェットを生成できること。
2. **ffmpeg/ffprobe**: 実行権限があり、`-version` が成功すること。
3. **Azure Speech SDK**: `import azure.cognitiveservices.speech` が成功すること。
4. **書き込み権限**: 設定ディレクトリにアトミック書き込みが可能なこと。

## UI
- バッジ表示: 緑 = OK, 黄 = 任意項目失敗, 赤 = 致命。
- 詳細ドロワーに失敗理由と対応手順を表示する。
- Self-check は起動時に自動実行し、ボタンで再実行できる。

## 実装ノート
- Self-check は `QThread` または `QFuture` で非同期実行する。
- ネットワーク依存チェックは「任意項目」として黄バッジで扱う。
- 結果はキャッシュし、最新実行時刻を表示する。
