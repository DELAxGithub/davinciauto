# DaVinci Autocut

DaVinci Resolve用の自動カット・マーカー処理システムです。

## プロジェクト構造

```
davinci_autocut/
├── README.md           # このファイル
├── main.py            # メイン処理スクリプト
├── lib/               # ユーティリティモジュール
│   └── resolve_utils.py
├── tests/             # テストスクリプト
├── data/              # CSVデータ
│   └── markers.csv
└── scripts/           # 追加スクリプト
```

## 機能分離

- **minivt_pipeline/**: 音声・TTS・字幕の自動化パイプライン
- **davinci_autocut/**: DaVinci Resolveのタイムライン操作・マーカー処理

## 使用方法

```bash
cd davinci_autocut
python main.py [CSVファイルパス]
```

## 依存関係

- DaVinci Resolve Studio (必須)
- Python 3.7+
- DaVinciResolveScript モジュール