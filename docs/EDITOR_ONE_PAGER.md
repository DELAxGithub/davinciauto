# 編集ワークフロー 1枚ガイド（ボタン付き）

目的: ターミナル不要で「どこを自動化しているか」「何を押せばよいか」をひと目で把握。

## 全体像（Import → Process → Export）

- Script: 脚本を取り込む（txt/markdown）→ 行に分解 → project.json に保存
- Telop: フォロー/注釈を整える → CSV/SRTに出力（Resolve/Premiere対応）
- Narration: Azure Speechで台本から音声を作る（NA/セリフ/引用）
- BGM/SE: 指示書からBGM/SEを自動生成
- Assembly: XMLやCSVからタイムラインを合体（Premiere/Resolve）

## フォルダ（Resolveにそのまま入る）

- テロップ類/CSV, SRT
- サウンド類/Narration, BGM, SE
- 映像類/Stock, Recordings, CG

## よく使う操作（UI上部で完結）

1) フォルダを選ぶ → 保存/出力
- フォルダ: プロジェクトフォルダ（例: OrionEp1）を選択
- 脚本: txtを取り込み（行が並ぶ）
- 出力一式: project.json, テロップCSV, README をプロジェクトに保存

2) サーバ保存/読込（バックアップ/共有）
- パスを入力 → 保存API/読込API ボタン
- SRT保存 → テロップ類/SRT/{Project}_Sub_follow.srt を生成

3) 音声生成（Azure Speech ワーカー起動時）
- 右ペインの指示に従い、ナレーションやBGM/SEを送信
- サウンド類/* に自動保存（Resolveでそのままインポート）

## 1クリック操作の簡易パネル（ブラウザ）

- Quick Panel: `http://127.0.0.1:8000/static/editor_quick_panel.html`
- 使い方: プロジェクトフォルダを指定 → ボタンで保存/SRT出力を実行

補足
- ワーカー: Azure Speechワーカー（port 8788）が起動していると音声の自動保存が有効
- 既存の統合UI: `/` で開く LLM ワークスペース（詳細操作）
