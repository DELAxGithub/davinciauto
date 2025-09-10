# Requirements Document

## Project Description (Input)
DaVinci Resolveの「DaVinci Resolve Script」フォルダに配置されるPythonスクリプトの作成。現在のパイプラインで生成されるSRTファイルをDaVinci Resolveのタイムラインに自動的にインポートし、レンダリング設定を適用してVideo Export Queueに追加する機能を実装する。

既存のresolve_import.pyスクリプトの機能を拡張し、以下の機能を追加：
1. SRTファイルの自動読み込み（minivt_pipeline/output/subtitles/script.srt）
2. DaVinci Resolveタイムラインへの字幕データの配置
3. Export設定（H.264、YouTube最適化設定）の適用
4. Export Queueへの自動追加
5. プロジェクト保存機能

技術要件：
- DaVinci Resolve Python API (resolve)を使用
- Fusionスクリプトとして動作（Scripts > Edit）
- 既存パイプライン（minivt_pipeline）との連携
- エラーハンドリングとログ出力機能

## Requirements
<!-- Will be generated in /kiro:spec-requirements phase -->