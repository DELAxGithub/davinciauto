# Mini VTR Pipeline Development Issues

## Phase 1: 即効改善 (1-2週間)

### Issue #001: BGMダッキング自動化システム
**Priority**: High | **Effort**: 2-3 days | **Type**: enhancement

**Description**:
DaVinci Resolve Fairlightでナレーション音声に合わせてBGMを自動ダッキング（音量下げ）するテンプレートシステムを実装

**Acceptance Criteria**:
- [ ] Fairlightサイドチェインテンプレート作成
- [ ] ナレーション検出時にBGM音量を-6〜-9dB自動調整
- [ ] プロジェクト作成時の自動テンプレート適用
- [ ] 設定可能な音量下げ幅・反応速度

**Technical Requirements**:
- DaVinci Resolve 18+ Fairlight API
- Pythonスクリプトでのテンプレート自動適用
- 音声レベル検出機能

**Labels**: `enhancement`, `audio`, `phase-1`, `high-priority`

---

### Issue #002: CPS警告付きSRT生成機能
**Priority**: High | **Effort**: 2-3 days | **Type**: feature

**Description**:
字幕の読み上げ速度（CPS: Characters Per Second）を自動チェックし、基準値超過時に警告マークを付与するSRT生成機能

**Acceptance Criteria**:
- [ ] CPS計算機能（文字数/表示時間）
- [ ] 設定可能な警告閾値（デフォルト: 14CPS）
- [ ] 超過行に `#FAST` マーク自動付与
- [ ] SRT出力前の警告レポート生成

**Technical Requirements**:
- `src/utils/srt.py` の拡張
- 日本語文字カウント機能
- 設定ファイルでの閾値管理

**Labels**: `feature`, `subtitles`, `phase-1`, `high-priority`

---

### Issue #003: プロジェクトテンプレート自動展開
**Priority**: Medium | **Effort**: 3-4 days | **Type**: enhancement

**Description**:
新規プロジェクト作成時にタイムライン構成・トランジション・ローワーサードを自動設定するテンプレートシステム

**Acceptance Criteria**:
- [ ] DaVinci Resolveプロジェクトテンプレート作成
- [ ] Python経由でのテンプレート自動適用
- [ ] トラック構成の標準化（Video1-3, Audio1-4等）
- [ ] 字幕スタイル・フォント設定の自動適用

**Technical Requirements**:
- DaVinci Resolve Project Manager API
- テンプレートファイル（.drp）管理
- 設定JSON による柔軟なカスタマイズ

**Labels**: `enhancement`, `workflow`, `phase-1`

---

### Issue #004: ライセンス情報自動紐付けシステム
**Priority**: High | **Effort**: 4-5 days | **Type**: feature

**Description**:
ストック素材のライセンス情報をCSV/JSONから自動読み込み、DaVinci Resolveのメタデータに紐付ける機能

**Acceptance Criteria**:
- [ ] CSV/JSON形式のライセンスデータベース対応
- [ ] ファイル名・ID による素材とライセンス情報の自動マッチング
- [ ] DaVinci ResolveのNotes/Commentsへの自動書き込み
- [ ] ライセンス有効期限・使用制限の警告機能

**Technical Requirements**:
- ライセンスDB管理（CSV/JSON）
- DaVinci Resolve Media Pool API
- ファイルマッチングアルゴリズム

**Labels**: `feature`, `legal`, `phase-1`, `high-priority`

---

## Phase 2: 音声制作基盤 (3-4週間)

### Issue #005: 音声バッチ処理システム
**Priority**: High | **Effort**: 1 week | **Type**: feature

**Description**:
SUNO/ElevenLabsでの音声生成・LUFS正規化・ファイル整理を一括処理するシステム

**Acceptance Criteria**:
- [ ] ストーリーボードからのBGMプロンプト一括送信
- [ ] 生成音声のLUFS正規化（-16〜-14dB）
- [ ] 自動トリミング・フェードイン/アウト処理
- [ ] セクション番号によるファイル自動リネーム

**Technical Requirements**:
- SUNO API統合
- pydub/FFmpegによる音声処理
- 非同期バッチ処理機能
- プログレス表示・エラー処理

**Labels**: `feature`, `audio`, `phase-2`, `high-priority`

---

### Issue #006: 発音辞書システム
**Priority**: Medium | **Effort**: 5-6 days | **Type**: feature

**Description**:
固有名詞・外来語の正確な読み方を管理し、TTS生成時にSSML/phonemeで発音を制御するシステム

**Acceptance Criteria**:
- [ ] JSON形式の発音辞書データベース
- [ ] 単語自動検出・辞書マッチング機能
- [ ] ElevenLabs SSML形式での発音指定
- [ ] 辞書更新・管理インターフェース

**Technical Requirements**:
- 日本語形態素解析（MeCab等）
- ElevenLabs SSML対応
- 発音辞書管理機能
- 正規表現による単語マッチング

**Labels**: `feature`, `tts`, `phase-2`

---

### Issue #007: 自動QCレポート生成
**Priority**: Medium | **Effort**: 4-5 days | **Type**: feature

**Description**:
出力前の品質チェックを自動実行し、問題点をMarkdownレポートで出力する機能

**Acceptance Criteria**:
- [ ] 音声レベル・無音区間の自動検出
- [ ] 字幕の時間重複・画面外はみ出しチェック
- [ ] フレームレート・解像度混在の警告
- [ ] Markdownレポートの自動生成

**Technical Requirements**:
- 音声解析（librosa/pydub）
- SRTファイル解析
- 動画メタデータ解析
- レポート生成テンプレート

**Labels**: `feature`, `quality`, `phase-2`

---

## Phase 3: AI支援高度化 (6-8週間)

### Issue #008: ショット候補スコアリング
**Priority**: Medium | **Effort**: 2 weeks | **Type**: feature

**Description**:
ストーリーボードキーワードと映像素材を分析し、適合度をスコアリングして候補を自動ランキング

**Acceptance Criteria**:
- [ ] キーワードマッチングアルゴリズム
- [ ] 映像の色調・動き・雰囲気の自動分析
- [ ] 適合度スコア計算・ランキング表示
- [ ] 学習機能（フィードバックによる精度向上）

**Technical Requirements**:
- OpenCV/機械学習モデル
- 映像特徴量抽出
- 自然言語処理（キーワード分析）
- スコアリングアルゴリズム

**Labels**: `feature`, `ai`, `phase-3`

---

### Issue #009: 重複クリップ検出システム
**Priority**: Low | **Effort**: 1 week | **Type**: feature

**Description**:
pHash（知覚ハッシュ）を使用してほぼ同じ映像を検出し、重複購入・使用を防止

**Acceptance Criteria**:
- [ ] 映像ファイルのpHash計算
- [ ] 類似度閾値による重複判定
- [ ] 重複候補のグループ化・表示
- [ ] 代表クリップ選択支援機能

**Technical Requirements**:
- pHash実装（OpenCV/imagehash）
- 大量ファイル処理の最適化
- データベース設計（類似度管理）
- UI での重複表示機能

**Labels**: `feature`, `optimization`, `phase-3`

---

### Issue #010: 納品パッケージ自動生成
**Priority**: Medium | **Effort**: 5-6 days | **Type**: feature

**Description**:
マスター動画・素材・字幕・ライセンス情報を構成固定のパッケージで自動生成

**Acceptance Criteria**:
- [ ] 指定フォルダ構成での自動パッケージング
- [ ] バージョン管理ID（S01E03_v02）の自動付与
- [ ] MD5ハッシュ・メタデータの自動生成
- [ ] Zip圧縮・パスワード設定機能

**Technical Requirements**:
- ファイルシステム操作
- Zip圧縮・暗号化
- メタデータ生成・埋め込み
- バージョン管理システム

**Labels**: `feature`, `workflow`, `phase-3`

---

## Phase 4: 番組特化・運用最適化

### Issue #011: 星座モーショングラフィックス
**Priority**: Low | **Effort**: 1 week | **Type**: feature

**Description**:
オリオン座等の星座を線で結ぶアニメーションを自動生成するFusion/AEテンプレート

**Acceptance Criteria**:
- [ ] 星座座標データベース
- [ ] 星の出現→線描画アニメーション
- [ ] テキスト差し替え対応
- [ ] DaVinci Fusion テンプレート化

**Technical Requirements**:
- Fusion scripting
- 星座座標データ
- アニメーション生成アルゴリズム
- テンプレート管理システム

**Labels**: `feature`, `graphics`, `phase-4`

---

### Issue #012: クラウド納品システム
**Priority**: Low | **Effort**: 1 week | **Type**: feature

**Description**:
S3/Google Drive への自動アップロード・共有リンク発行・権限管理システム

**Acceptance Criteria**:
- [ ] クラウドサービス API統合
- [ ] 自動アップロード・権限設定
- [ ] 期限付き共有リンク生成
- [ ] アップロード進捗・完了通知

**Technical Requirements**:
- AWS S3/Google Drive API
- 認証・権限管理
- 非同期アップロード処理
- 通知システム

**Labels**: `feature`, `cloud`, `phase-4`

---

## 実装補助タスク

### Issue #013: 開発環境・CI/CD構築
**Priority**: Medium | **Effort**: 3-4 days | **Type**: infrastructure

**Description**:
開発効率化のためのテスト・ビルド・デプロイメント自動化

**Acceptance Criteria**:
- [ ] pytest による単体テスト環境
- [ ] GitHub Actions CI/CD パイプライン
- [ ] コードフォーマット・リント自動化
- [ ] ドキュメント自動生成

**Labels**: `infrastructure`, `ci-cd`

---

### Issue #014: 詳細ドキュメント整備
**Priority**: Medium | **Effort**: 2-3 days | **Type**: documentation

**Description**:
各機能の使用方法・トラブルシューティング・API仕様書の整備

**Acceptance Criteria**:
- [ ] 機能別使用ガイド作成
- [ ] トラブルシューティング FAQ
- [ ] API リファレンス自動生成
- [ ] 設定ファイル仕様書

**Labels**: `documentation`

---

## マイルストーン設定

- **v1.1 (Phase 1)**: 基本効率化 - 2週間後
- **v1.2 (Phase 2)**: 音声基盤強化 - 6週間後  
- **v2.0 (Phase 3)**: AI支援機能 - 12週間後
- **v2.1 (Phase 4)**: 特化機能 - 継続的リリース

## ラベル体系

**Type**: `feature`, `enhancement`, `bug`, `infrastructure`, `documentation`
**Priority**: `high-priority`, `medium-priority`, `low-priority`  
**Component**: `audio`, `subtitles`, `workflow`, `ai`, `graphics`, `cloud`, `quality`, `legal`
**Phase**: `phase-1`, `phase-2`, `phase-3`, `phase-4`