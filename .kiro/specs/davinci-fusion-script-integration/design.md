# Design Document

## Architecture Overview

Fusionスクリプト（Workspace → Scripts → Edit）として実行される単一Pythonモジュール。最小UI（必要時のみSRT選択ダイアログ）で、Resolve APIに接続し、字幕インポート→レンダー設定適用→Render Queue追加→保存までを自動化する。

```
Entry (Fusion Script)
  ├─ Env/Path Resolver           # SRT既定パス推定・検証
  ├─ Resolve Connector           # API接続・Project/Timeline取得
  ├─ Subtitle Importer           # タイムラインへのSRT取り込み
  ├─ Render Settings Applier     # プリセット/カスタム設定適用
  ├─ Render Queue Manager        # ジョブ追加・(任意)開始
  └─ Project Saver               # プロジェクト保存
```

## Components

- Entry Point
  - `main()`：実行フローを司る。例外を捕捉しログ出力。

- Env/Path Resolver
  - `find_default_srt()`：既定のSRTパス（`minivt_pipeline/output/subtitles/script.srt`）を探索
  - `choose_srt_file()`：見つからない場合のファイル選択（`tkinter` 可能なら使用）

- Resolve Connector
  - `get_resolve()`：`DaVinciResolveScript`の読み込みと`Resolve`インスタンス取得
  - `require_project_timeline(resolve)`：Project/Timelineの取得と検証

- Subtitle Importer
  - メソッド探索: `ImportSubtitles` → `ImportSubtitle` → `ImportTimelineSubtitle`
  - 字幕トラックが無ければ新規作成（可能なAPIで対応。不可ならインポート側に委譲）
  - 失敗時のフォールバック: `MediaPool.ImportMedia([srt])`＋ユーザーガイダンス

- Render Settings Applier
  - 既存プリセット（`YouTube 1080p`等）の適用を試行
  - 失敗時は`SetRenderSettings`でカスタム値を設定
    - Format=mp4, VideoCodec=H.264, Resolution/FrameRate=Timeline準拠, Audio=AAC 320kbps
  - レンジ: Entire Timeline

- Render Queue Manager
  - `Project.AddRenderJob()` でキュー追加
  - 設定で `Project.StartRendering()` の自動開始をオプトイン
  - 出力パス決定ロジック：
    - SRTの親ディレクトリから`../video/`を作成
    - 作成不可時は`~/Movies/DaVinciAuto/`

- Project Saver
  - `Project.Save()` 実行・検証

## Control Flow

1. 既定SRTパス探索 → 無ければファイル選択 → パス確定
2. Resolve接続 → Project/Timeline取得（無ければエラー終了）
3. 字幕インポート（APIメソッドを順に試行、失敗時はメディアプール）
4. レンダー設定適用（プリセット優先、失敗時カスタム）
5. 出力先パスを決定しジョブ追加（必要に応じてレンダリング開始）
6. プロジェクト保存 → 成否ログ

## Error Handling Strategy

- すべての主要操作で`try/except`し、詳細メッセージをログ
- リカバリ可能な失敗はフォールバックを用意（インポート/プリセット/パス作成）
- 重大失敗（Resolve接続不可/Projectなし/Timelineなし）は即時終了

## Configuration

- 既定設定（ハードコード最小限）
  - `AUTO_START_RENDER=False`
  - `DEFAULT_PRESET="YouTube 1080p"`
  - `FALLBACK_FMT={ mp4/H.264/TimelineFR/1080p/AAC }`
- 設定の外部化は次段階（INI/JSONのサイドカー、環境変数）

## API Usage (Resolve)

- `scriptapp("Resolve")`
- `Resolve.GetProjectManager().GetCurrentProject()`
- `Project.GetCurrentTimeline()`
- `Timeline.ImportSubtitles` / `ImportSubtitle` / `ImportTimelineSubtitle`
- `Project.GetMediaPool().ImportMedia([...])`
- `Project.SetRenderSettings({...})`
- `Project.AddRenderJob()` / `Project.StartRendering()`
- `Project.Save()`

## Compatibility Notes

- Resolve 18+ を対象（Studio差異あり）
- `tkinter`が利用不可の環境ではファイル選択をスキップして失敗を明示

