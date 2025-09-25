# ADR-001: GUI と CLI の連携方式

## 状況
SwiftUI + Xcode のバンドル構成では、リソースコピー・依存ライブラリの取り扱いが複雑で、手作業や端末依存のトラブルが多発している。PyInstaller ベースで GUI を再構築するにあたり、GUI とパイプライン CLI をどう連携させるか決定する必要がある。

## 決定
- リリースビルドは **外部 EXE 方式 (B)** を必須とする。
  - GUI は同梱した CLI 実行ファイルを `QProcess` で起動する。
  - IPC は CLI の引数と JSONL ログ、および標準エラー出力を用いる。
  - 配布形態は PyInstaller の **OneDir** を標準とする。
- 開発用途では `APP_EMBEDDED=1` を指定した場合のみ **同一プロセス方式 (A)** を許可する。
  - `runpy.run_module('davinciauto_core.cli')` で直接呼び出し、障害調査やデバッグを容易にする。

## 根拠
- 外部 EXE 方式はクラッシュ分離ができ、GUI 側でリカバリしやすい。
- PyInstaller の `_MEIPASS` を考慮したリソース解決がしやすい。
- CLI の仕様変更があっても GUI との結合度が低く保てる。

## 影響
- GUI から CLI を起動する際は、PATH に依存せず同梱ファイルを解決する必要がある。
- CLI がクラッシュしても GUI は生存し、再実行ボタンを表示する。
- OneFile 配布は将来の課題として別 ADR を検討する。

## Done Definition
- GUI から同梱 CLI だけを起動し、外部 Python には依存しない。
- CLI が異常終了しても GUI は操作可能なまま再実行導線を提示する。
- `APP_EMBEDDED=1` で起動した場合、同一プロセス実行が成功しログが GUI に反映される。
