# Output Folder and Naming Convention (Resolve-ready)

目的: DaVinci Resolve にフォルダを丸ごとドラッグしただけで、プロジェクト内のビン構成がそのまま再現されるようにする。

## Project Root Layout

```
<ProjectName>/
  テロップ類/
    SRT/
    CSV/
  サウンド類/
    Narration/
    BGM/
    SE/
  映像類/
    Stock/
    Recordings/
    CG/
  inputs/
  project.json
```

- フォルダ名は Resolve のビンとしてミラー表示されます。
- システム出力は原則として上記の配下にのみ生成します（散在禁止）。

## File Naming

- Narration: `サウンド類/Narration/{Project}_{line:04d}_{Voice}.mp3`
- BGM: `サウンド類/BGM/{Project}_BGM{index:02d}.mp3`
- SE: `サウンド類/SE/{Project}_SE{index:02d}.mp3`
- SRT: `テロップ類/SRT/{Project}_Sub_{source}.srt` 例: `_Sub_follow.srt`
- Telop CSV: `テロップ類/CSV/{Project}_TEL_vertical.csv`

注意:
- `{Project}` はプロジェクトルートのフォルダ名、または UI の `projectName` を使用。
- 音声系は 24kHz/160kbps の MP3（Azure Speech 既定）を標準とし、用途に応じて変更可能。

## System Defaults (実装)

- Azure Speech Worker (backend/azure_server.py)
  - Narration 出力先: `サウンド類/Narration/`
  - BGM 出力先: `サウンド類/BGM/`
  - SE 出力先: `サウンド類/SE/`
- SRT 保存 API (backend/main.py)
  - 既定保存先: `テロップ類/SRT/`
- UI (gui_steps/llm_workspace.html)
  - Telop CSV: `テロップ類/CSV/{Project}_TEL_vertical.csv`
  - SRT 保存: `テロップ類/SRT/{Project}_Sub_follow.srt`

## Future (Video Assets)

- Stock 素材: `映像類/Stock/*`
- 収録素材: `映像類/Recordings/*`
- CG: `映像類/CG/*`

将来的に自動ダウンロード/自動整理を追加する場合も、上記配下に統一します。
