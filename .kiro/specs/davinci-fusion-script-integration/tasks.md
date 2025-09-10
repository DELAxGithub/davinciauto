# Tasks Backlog

## Implementation

1. Entry/Bootstrap
- スクリプト雛形作成（`main()`/ログユーティリティ）
- Resolve API import/接続ユーティリティ

2. Path Handling
- 既定SRT探索ロジック実装（相対・ワークスペース）
- ファイル選択ダイアログ（`tkinter`フォールバック実装）

3. Subtitle Import
- タイムライン検証（Project/Timeline必須）
- メソッド順次試行＋例外処理
- 失敗時メディアプールへのフォールバック

4. Render Settings
- プリセット適用の試行
- カスタム設定（mp4/H.264/Timeline準拠/AAC）
- 出力先パス決定とディレクトリ作成

5. Render Queue
- `AddRenderJob()` でキュー追加
- オプション：`StartRendering()` 自動開始（デフォルトOFF）

6. Save & Finalize
- `Project.Save()` 呼び出しと検証
- 最終ログ整備

## Testing

- ローカル（Resolveなし）でのユニットレベル: パス解析・設定構築の関数分離とテスト
- Resolve環境での手動結合テスト: 字幕インポート/レンダー設定/キュー追加/保存
- フォールバック網羅テスト: 各APIメソッド失敗パス確認

## Documentation

- ユーザー手順: Scriptsメニューからの起動、既定パス、フォールバック説明
- トラブルシューティング: API未検出、Project/Timeline未設定、権限/パス失敗

## Acceptance Mapping

- AC-1〜AC-7に対応するテスト観点と検証手順を記載し、完了条件をチェックリスト化

