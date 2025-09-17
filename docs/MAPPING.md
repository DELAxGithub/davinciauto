# RowData ↔ LineItem Mapping Policy

目的: 既存フロント/バックエンド（RowData）と、将来の分業スキーマ（LineItem）を安全に橋渡しするためのポリシーを明文化します。

## 現行 RowData（gui/backend 互換）
- キーフィールド: `original`, `narr`, `follow`, `role`, `character`, `tStart`, `tEnd`, `tDur`, `status`, `notes`, `rate`, `locked`
- 時間系はフラット（tStart/tEnd/tDur）

## 将来 LineItem（core/schemas.py）
- キーフィールド: `text`, `role`, `character`, `timing{tStart,tEnd,tDur}`, `tags`, `locked`, `status`, `notes`
- `id`: `L{line:04d}` / `index`: 行番号

## テキスト源の原則（text_source）
- 保存用（プロジェクトの“地図”）: `original` を既定とする
  - 理由: LLMや人手で派生（narr/follow）をいくらでも再生成できるため、台本の一次情報を保持
- ナレーション（生成/実行）: `narr` を優先、空なら `original`
- テロップ（生成/実行）: `follow` を優先、空なら適宜ポリシー（UI側の一括生成/置換で補う）

このポリシーはアダプタで実装済み:
- `backend/adapters.py`
  - `row_to_lineitem(row, text_source='original'|'narr'|'follow')`
  - `lineitem_to_row(item)`

## タイミング
- `RowData.tStart/tEnd/tDur` ↔ `LineItem.timing.{tStart,tEnd,tDur}` を1:1で写像
- 未設定時は 0.0 とし、音声長に応じて再計算可（バックエンド/ワーカー側）

## ステータスと拡張
- `status` は両者とも任意の辞書を保持（UIジョブ状態・ワーカー結果を保持）
- `tags` は将来の分類/フラグ用途で LineItem に追記（RowData には未導入）

## 互換性
- UI の `project.json` は当面 `{name, savedAt, data:[RowData...]}` を維持
- バックエンドの `/api/projects/(save|load)` は任意 JSON を受け渡し（将来の完全な Project スキーマへ移行可能）

