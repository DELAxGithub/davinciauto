# GUI ランチャーの使い方

## 概要
`DavinciAutoLauncher.command` をダブルクリックすることで、CLI を使わずに自己診断・Fake-TTS・本番実行ができます。実行後はログが `~/Library/Logs/davinciauto-cli/` に保存されます。

## ステップ
1. DMG を開き、`davinciauto-cli-<version>-<arch>` フォルダをローカルにコピーします。
2. コピーしたフォルダ内の `DavinciAutoLauncher.command` を右クリック → **開く**。
3. 表示されるダイアログの流れに従い、以下を指定します。
   - API キー（任意、空欄可）
   - 台本ファイル
   - 出力フォルダ
   - 実行モード（Self-Check / Fake-TTS / Full Run）
   - TTS は本番モードで Azure 固定（Fake-TTS のみ `fake` を使用）
4. 実行後、結果が完了ダイアログとログファイルに表示されます。Fake-TTS や本番実行では指定した出力フォルダを確認してください。

## 注意
- `DavinciAutoLauncher.command` と `gui_launcher_run.sh` は同じフォルダ内に置いたままにしてください。
- 初回実行時に Gatekeeper 警告が出た場合は、フォルダ全体が信頼済みとなるまで **システム設定 → プライバシーとセキュリティ** で許可してください。
- ログファイルは `~/Library/Logs/davinciauto-cli/launcher-YYYYMMDD-HHMMSS.log` に保存されます。問題発生時はこのファイルを添えて報告してください。
