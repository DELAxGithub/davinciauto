# Repository Structure and Conventions

目的: 迷子にならない“地図”を提供し、将来の分業化に向けた土台を作る。現時点ではファイル移動は行わず、共通スキーマと可視化ツールを導入する。

## Top-Level Roles

- backend: FastAPI エンドポイント、MCP 連携、Azure Speech ベースのTTS API
- gui_steps: 既存 GUI（統合 UI、ステップ別 GUI）
- minivt_pipeline: 旧パイプライン（utils/clients 資産）
- projects: 各種ユーティリティ（autocut 等）、プロジェクト単位の素材
- prompts: LLM プロンプト
- docs: ドキュメント（本ファイル含む）
- scripts: 補助スクリプト（repo_tree など）
- core: 共通データモデル（Pydantic スキーマ）
- output, thumbnails: 出力物・中間成果（検索対象から除外）

将来の目標イメージ（リファクタ後）:

- apps/api: API アプリ（FastAPI）
- workers/*: フェーズ別ワーカー（narration/telop/storyboard/bgm/se/assembly）
- apps/ui/*: フェーズ別 UI（ダッシュボード、脚本、ナレ、テロップ、映像、音、アセンブリ）

まずは“地図”と“共通スキーマ”のみ追加し、既存コードはそのまま運用する。

## Conventions

- プロジェクトルート配下に、分業に必要なアーティファクトは `projects/<project_name>/exports/...` に集約。
- 共有スキーマは `core/schemas.py` に定義（Project/LineItem/Task/Artifact）。
- 検索除外は `.rgignore` で管理（バイナリ・巨大生成物・ビルド成果を除外）。
- レポ構造の可視化は `scripts/repo_tree.sh` を使用。

## Quick Map (current)

```
backend/
  main.py            # DaVinci Auto Backend（FastAPI）
  azure_server.py    # Azure Speech Worker (legacy helper)
  eleven_server.py   # [Legacy] ElevenLabs ワーカー（保守目的で残置）
gui_steps/
  llm_workspace.html # 統合 UI
  step*_*.py         # ステップ別 GUI
minivt_pipeline/
  src/               # 旧パイプライン、utils/clients
projects/
  autocut/           # CSV/XML カッター、Premiere/Resolve 支援
prompts/
docs/
scripts/
core/
output/, thumbnails/ # 生成物（検索除外対象）
```

実体の main/models は `backend/` 配下にあります（IDE の古いタブに root の重複表示がある場合は閉じてください）。

## repo_tree の使い方

主要ファイルだけを 2〜3 階層までツリー表示し、出力物やバイナリを除外します。

```bash
chmod +x scripts/repo_tree.sh
./scripts/repo_tree.sh . 3
```

引数:
- 第1引数: ルート（省略時 `.`）
- 第2引数: 最大深さ（省略時 `3`）

## Shared Schemas (core/schemas.py)

分業化のアンカーとなる最小スキーマ:

- Project: id, title, root_dir, fps, language, script
- Script: raw_text, version, segments
- LineItem: id, index, role(NA/DL/Q/EX…), character, text, tags, timing(tStart/tEnd/tDur), locked
- Task: id, type(narration, telop, storyboard, bgm, se, cg, assemble), input_refs, status, assignee, params
- Artifact: id, type(audio_narr, telop_csv, storyboard_json, bgm_track, se_track, timeline_xml…), path, meta, source_task_id

現状の UI/バックエンドは `backend/models.py` の RowData を使用しています。移行は段階的に行い、アダプタ層（RowData ↔ LineItem）を整備します。

## Naming

- スクリプト/脚本: `projects/<name>/project.json` に保存（将来）
- 音声: `projects/<name>/exports/audio/narr/`（Azure Speech 出力を保存）
- BGM/SE: `projects/<name>/exports/audio/bgm|se/`
- テロップ/SRT: `projects/<name>/exports/subtitles/`
- タイムライン: `projects/<name>/exports/timelines/`

## What We Are NOT Doing Yet

- 物理的なファイル移動・リネームはまだ行わない
- 大きな API 改修は行わない
- 既存 UI の大規模分割は行わない

まずは“迷わない”ことを最優先に、スキーマと可視化から整えます。

## Archiving Policy (実運用)

- フェーズごとに「使う/使わない」を現場で判定するため、アーカイブ→必要時復活の運用を用意。
- スクリプト:
  - `python scripts/usage_audit.py --format markdown > usage_report.md` で候補抽出
  - `python scripts/archive_phase.py --dry-run` で計画確認
  - `python scripts/archive_phase.py --mode candidates` で候補を `experiments/archive/` へ退避（manifest保存）
  - `python scripts/archive_phase.py --mode all` でホワイトリスト以外を一括退避
  - `python scripts/restore_from_archive.py --list|--paths ...|--all` で復活
- いずれも Git 管理下であれば `git mv` を優先利用し履歴を保持します。
