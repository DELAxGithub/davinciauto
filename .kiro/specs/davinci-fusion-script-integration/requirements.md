# Requirements Document

## Project Description (Input)
DaVinci Resolveの「DaVinci Resolve Script」フォルダに配置されるPythonスクリプトの作成。現在のパイプラインで生成されるSRTファイルをDaVinci Resolveのタイムラインに自動的にインポートし、レンダリング設定を適用してVideo Export Queueに追加する機能を実装する。

既存の`minivt_pipeline/src/resolve_import.py`の機能を拡張し、以下の機能を追加：
1. SRTファイルの自動読み込み（`minivt_pipeline/output/subtitles/script.srt`）
2. DaVinci Resolveタイムラインへの字幕データの配置（トラック自動作成含む）
3. Export設定（H.264／YouTube最適化）の適用
4. Render Queueへの自動追加（オプションで自動開始）
5. プロジェクト保存機能（自動保存）

技術要件：
- DaVinci Resolve Python API (`DaVinciResolveScript`) を使用
- Fusionスクリプトとして動作（Workspace → Scripts → Edit）
- 既存パイプライン（`minivt_pipeline`）出力との連携
- エラーハンドリングとログ出力（コンソール／メッセージ）

---

## Functional Requirements

1) SRT自動検出と入力
- デフォルトのSRTパスを探索する：
  - 優先: スクリプト実行ディレクトリ近傍の`minivt_pipeline/output/subtitles/script.srt`
  - 次点: ワークスペース直下の`minivt_pipeline/output/subtitles/script.srt`
  - 見つからない場合: ファイル選択ダイアログでユーザーに選択させる
- 検出したSRTファイルの存在と拡張子を検証する

2) Resolve接続とプロジェクト/タイムライン検証
- `Resolve`スクリプトアプリに接続できること
- アクティブなプロジェクトが存在すること（存在しない場合はエラーメッセージ）
- アクティブなタイムラインが存在すること（存在しない場合はエラーメッセージ）

3) 字幕インポート処理
- タイムラインに字幕トラックが無い場合は自動作成する
- `timeline.ImportSubtitles` / `ImportSubtitle` / `ImportTimelineSubtitle` の順に利用可能メソッドでインポートする
- インポート開始位置はタイムライン先頭（00:00:00:00）を既定とする
- 設定可能項目（将来拡張のためのオプション化）
  - 言語（`Japanese` 既定）
  - 文字エンコーディング（UTF-8 既定）
  - 字幕表示スタイル（トラックレベルでの既定スタイル利用）

4) レンダリング設定の適用
- 既定のレンダー設定プリセットを適用（以下のいずれか）
  - `YouTube 1080p`（あれば）
  - 代替: カスタム設定
    - `Format`: mp4
    - `VideoCodec`: H.264
    - `Quality`: Automatic/Best
    - `Resolution`: 1920x1080（タイムライン解像度優先で一致）
    - `FrameRate`: タイムラインに一致
    - `AudioCodec`: AAC 320kbps Stereo
- レンダーレンジ: Entire timeline（既定）
- 出力ファイルパスの既定値を決定：
  - SRTの親ディレクトリに`../video/`を作り、`<project>_<YYYYMMDD-HHMM>.mp4`
  - 作成不可の場合はユーザーのホーム`Movies/DaVinciAuto/`へフォールバック

5) Render Queueへの追加と保存
- `Project.AddRenderJob` でキューに追加する
- 既定では自動レンダリングは開始しない（`StartRendering`はオプション）
- キュー追加後に`Project.Save()`を実行する

6) ログとユーザー通知
- 重要操作と失敗は`print`でログ出力
- 重大エラー時は簡易メッセージ表示（可能であればダイアログ）

---

## Non-Functional Requirements

- 互換性: DaVinci Resolve 18以降（Studio/非Studio両対応を目指す。API制限時は安全にフォールバック）
- パフォーマンス: 字幕インポート〜キュー追加まで5秒以内（環境依存）
- 可搬性: Resolve内Python環境のみで動作。外部依存の導入を避ける
- 可観測性: 主要イベントをログ出力し、障害解析に必要な情報（例: 利用APIメソッド名）を含む
- 安全性: 既存タイムラインの破壊的変更を行わない（既定では新規字幕トラックに追加）

---

## Constraints & Assumptions

- ResolveのPython APIは環境により利用可能メソッドが異なる（Studio差異、マイナーバージョン差異）
- ResolveのFusionスクリプト環境では標準GUIライブラリに制限がある場合がある（`tkinter`は利用可否が環境依存）
- パイプライン出力の既定パスは`minivt_pipeline/output/subtitles/script.srt`（相対基準はSRTから推定）
- 出力先ディレクトリ作成に失敗する可能性がある（パーミッション）

---

## Acceptance Criteria

AC-1 SRT検出
- 既定パスにSRTが存在する場合、ダイアログ無しでそのSRTを使用する
- 既定パスに無い場合、ユーザーにSRTファイル選択を促す

AC-2 Resolve接続
- Resolveに接続できない場合は明確なエラーメッセージを表示し終了する
- プロジェクト／タイムラインが無ければエラーメッセージを表示し終了する

AC-3 字幕インポート
- 少なくとも1つのAPIメソッドで字幕がタイムラインに追加される
- 失敗時、メディアプールへのインポートにフォールバックし、指示メッセージを表示する

AC-4 レンダリング設定
- 指定のプリセット適用に成功するか、指定カスタム設定がプロジェクトに反映される
- レンダーレンジがEntireに設定される

AC-5 Render Queue
- 少なくとも1件のレンダージョブがRender Queueに追加される
- 既定ではレンダリングは開始されない（設定により自動開始可）

AC-6 プロジェクト保存
- Render Queue追加後にプロジェクトが保存される（`Save()`が成功）

AC-7 ログ
- 実行ログに「SRTパス」「利用APIメソッド」「Render設定適用」「キュー追加」「保存完了/失敗」が含まれる

---

## Out of Scope

- 自動プロジェクト作成・テンプレート適用（将来拡張）
- 自動レンダリング開始（既定はキュー追加のみ。設定で有効化）
- 字幕スタイルの詳細編集（Resolve UI設定に依存）

---

## Dependencies

- DaVinci Resolve 18+（Fusion Scripts API 有効）
- 既存パイプラインが生成するSRT（`output/subtitles/script.srt`）

---

## Risks

- Resolve APIの差分により一部メソッドが利用不可 → フォールバック実装で吸収
- Resolve環境での`tkinter`利用可否 → 代替としてダイアログ無し運用/メディアプール運用を案内
- 出力ディレクトリの権限問題 → ホーム配下へのフォールバックで回避

---

## Open Questions

1. プロジェクト/タイムライン未存在時の挙動（自動作成 or エラー終了）
2. 出力の既定解像度（タイムライン依存 vs 固定1080p）
3. 自動レンダリング開始の既定値（falseを推奨）

---

## Traceability to Existing Script

- 既存 `minivt_pipeline/src/resolve_import.py` は手動選択→字幕インポートとメディアプールフォールバックを実装済み
- 本機能ではこれに「自動SRT検出」「レンダー設定の適用」「Render Queue追加」「保存」を追加する
