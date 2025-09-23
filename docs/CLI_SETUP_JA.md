# CLI セットアップガイド（日本語）

DaVinci Auto のパイプラインを `davinciauto-cli` で実行するための手順をまとめています。DMG で配布されるバンドルを想定しています。

## 1. 同梱物

- `davinciauto-cli` … CLI 実行ファイル
- `DavinciAutoLauncher.command` … 簡易ランチャー（ダブルクリックでGUIフロー）
- `gui_launcher_run.sh` … ランチャー内部で呼び出すシェルスクリプト
- `samples/sample_script.txt` … 動作確認用スクリプト
- 本ドキュメントと `CLI_SETUP.md`（英語版）

## 2. 必要環境

- macOS (ARM64/M1-M4)
- Python 3.11 がインストールされていること
- `ffmpeg` / `ffprobe` が利用可能であること（Homebrew の `brew install ffmpeg` 推奨）
- Azure Speech Service のキーとリージョン
  - `.env` もしくは実行時環境変数に `AZURE_SPEECH_KEY` と `AZURE_SPEECH_REGION` を設定

> **メモ**: 旧ElevenLabs設定は不要です。TTSはAzure固定です。

## 3. インストール手順

1. DMG をマウントし、`davinciauto-cli-<version>-arm64` フォルダをドラッグしてローカル（例: `~/Applications` やデスクトップ）へコピー
2. コピー先フォルダを開き、`DavinciAutoLauncher.command` を右クリック→「開く」で初回実行許可（macOSのGatekeeper対策）
3. ランチャー起動後、必要事項を入力して実行
   - スクリプト: `.txt` や `.md` の台本ファイルを指定
   - 出力先: 空のディレクトリ、または既存プロジェクト内の `exports` ディレクトリ等

CLI を直接使う場合はターミナルで以下のように実行します。

```bash
./davinciauto-cli run \
  --script /path/to/script.txt \
  --output /path/to/output_dir \
  --provider azure \
  --target resolve
```

### 環境変数の設定例

```bash
export AZURE_SPEECH_KEY="<YourAzureSpeechKey>"
export AZURE_SPEECH_REGION="japaneast"  # 例: japaneast, eastus2 など
```

`ffmpeg` と `ffprobe` が標準PATHにない場合は、以下の環境変数で明示指定できます。

```bash
export DAVINCIAUTO_FFMPEG="/usr/local/bin/ffmpeg"
export DAVINCIAUTO_FFPROBE="/usr/local/bin/ffprobe"
```

## 4. 動作確認（フェイクTTS）

Azureキーが準備できていない場合でも、`--fake-tts` オプションを付けることで無音ファイルを生成してパイプラインを確認できます。

```bash
./davinciauto-cli run \
  --script samples/sample_script.txt \
  --output ./output_test \
  --fake-tts \
  --provider azure
```

## 5. よくあるトラブル

| 症状 | 対処方法 |
| --- | --- |
| `AZURE_SPEECH_KEY is not set` と表示される | 環境変数 `AZURE_SPEECH_KEY` / `AZURE_SPEECH_REGION` を設定して再実行 |
| `ffmpeg`/`ffprobe` が見つからない | Homebrewでインストール、または `DAVINCIAUTO_FFMPEG` / `DAVINCIAUTO_FFPROBE` でパス指定 |
| ランチャーが `No such file or directory` で終了 | DMG上ではなくコピーしたフォルダから `DavinciAutoLauncher.command` を実行 |
| AzureのAPIエラー (401/403/429等) | キー/リージョンの確認、Azureポータルでの利用状況チェック、待機して再試行 |

## 6. 出力物

成功すると指定ディレクトリに以下が作成されます。

- `audio/narration.mp3` と各行MP3
- `subtitles/script.srt`
- `subtitles_plain.txt`
- `storyboard/pack.json`

DaVinci Resolve や他の編集ツールにそのまま取り込めます。

---

詳細は `docs/USER_GUIDE.md`（英語/日本語含む）や `docs/EDITOR_ONE_PAGER.md` を参照してください。
