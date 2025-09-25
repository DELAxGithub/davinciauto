# SPEC-020: GUI ⇄ CLI IPC 契約

## 起動
- GUI は `QProcess` で `Resources/bin/davinciauto_cli` を実行する。
- 引数は配列渡しで、シェル展開は禁止する。
- 環境変数 `AZURE_SPEECH_KEY` など資格情報は GUI から設定する。
- 終了は `TERM → タイムアウト 5s → KILL`（Windows は `CTRL_BREAK_EVENT` → `TerminateProcess`）。

## 引数
```
cli_exe --config <config.json> --progress-log <log.jsonl> [--self-check] [--dry-run]
```
- `--config`: パイプライン設定 JSON ファイルへのパス。
- `--progress-log`: GUI が tail する JSONL ログファイルへのパス。
- `--self-check`: Self-check モード。
- `--dry-run`: 副作用を伴わない実行。

## 終了コード
| code | 内容 |
| ---- | ---- |
| 0 | 成功 |
| 2 | 入力不正 |
| 3 | 環境不足（依存欠如等） |
| 4 | 実行時エラー（再実行で改善しないもの） |
| 5 | ユーザー中断 |
| その他 | 4 に丸める |

## JSONL ログ仕様
- UTF-8 / 1 行 = 1 イベント / 最大 64 KB。
- スキーマ:
```jsonc
{
  "ts": "2025-09-23T12:34:56.789Z",
  "level": "debug|info|warn|error|progress|artifact",
  "code": "PIPELINE.START|STEP.DONE|...",
  "msg": "短い説明文",
  "payload": { "free": "any json" },
  "step": "narration|subtitles|...",
  "progress": { "current": 3, "total": 10 }
}
```
- GUI は未知フィールドを無視し、JSON デコード失敗時はイベント捨て。

## GUI 側の取り扱い
- 未完行はバッファ保持し、次回読み取り時に再試行。
- 最大保持行数は 5,000、超過分は先頭から破棄。
- `artifact` イベント到着で成果物リンクを更新。
- `error` レベル到着後も UI を継続操作可能とする。

## 参考イベント
```json
{"ts":"2025-09-23T01:23:45Z","level":"info","code":"PIPELINE.START","msg":"Start","payload":{"version":"1"}}
{"ts":"2025-09-23T01:23:46Z","level":"progress","code":"STEP.PROGRESS","msg":"Transcribing","progress":{"current":2,"total":7}}
{"ts":"2025-09-23T01:24:10Z","level":"artifact","code":"ARTIFACT.CREATED","msg":"WAV exported","payload":{"path":"/abs/out/foo.wav"}}
{"ts":"2025-09-23T01:25:00Z","level":"info","code":"PIPELINE.END","msg":"Done"}
```
