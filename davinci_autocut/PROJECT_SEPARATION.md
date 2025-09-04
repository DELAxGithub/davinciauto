# プロジェクト分離設計書

## 概要
このドキュメントでは、既存の`minivt_pipeline`（音声・TTS自動化）と新しい`davinci_autocut`（DaVinci Resolve自動化）の分離方針を説明します。

## 分離方針

### 1. フォルダ構造分離
```
davinciauto/                    # プロジェクトルート
├── minivt_pipeline/           # 既存：音声・TTS・字幕自動化
│   ├── src/
│   ├── output/
│   └── data/
├── davinci_autocut/          # 新規：DaVinci Resolve自動化
│   ├── lib/
│   ├── data/
│   ├── tests/
│   └── scripts/
└── [ルート共通ファイル]        # 既存テストスクリプト群
```

### 2. 機能分離
| 領域 | minivt_pipeline | davinci_autocut |
|------|-----------------|-----------------|
| **目的** | 音声・字幕生成 | タイムライン操作 |
| **入力** | テキストスクリプト | CSVマーカーデータ |
| **出力** | MP3, SRT, JSON | DaVinci Timeline |
| **依存** | ElevenLabs, OpenAI | DaVinciResolveScript |
| **API** | 外部Web API | ローカルResolve API |

### 3. 依存関係分離
- **minivt_pipeline**: `requirements.txt` でPythonパッケージ管理
- **davinci_autocut**: DaVinciResolveScript（システム依存）のみ

### 4. データフロー分離
```
[独立フロー1] Script → minivt_pipeline → Audio/SRT
[独立フロー2] CSV → davinci_autocut → Timeline
```

### 5. 開発環境分離
- **minivt_pipeline**: 通常のPython環境 + API キー
- **davinci_autocut**: DaVinci Resolve + Script API

## 混在回避策

### 1. 名前空間分離
- パッケージ名: `minivt_*` vs `davinci_*`
- 関数名: 明確なプレフィックス使用
- 変数名: 機能別命名規則

### 2. 設定ファイル分離
- **minivt_pipeline**: `.env`でAPI設定
- **davinci_autocut**: Resolveプロジェクト設定

### 3. 実行分離
- 独立したエントリーポイント
- 異なるコマンドライン引数
- 別々のエラーハンドリング

### 4. テスト分離
- 独立したテストスイート
- 異なるモックオブジェクト
- 分離されたテストデータ

## 将来的な統合ポイント
必要に応じて以下の統合が可能：
1. **ワークフロー統合**: Script → Audio → Timeline
2. **設定統合**: 共通の設定管理システム
3. **ユーティリティ共有**: 共通モジュールの抽出

## 注意事項
- 既存の`minivt_pipeline`への変更は最小限に
- 新機能は`davinci_autocut`内に封じ込め
- 共通ユーティリティは慎重に設計