# DaVinci Autocut - Cleanup Log

## 実行日: 2024-09-03

## 整理内容
昨日の試行錯誤で作成された17個の失敗/実験用Pythonファイルを `archive/failed_experiments/` に移動しました。

## 移動されたファイル (17個)
- `complete_marker_workflow.py` - マーカーワークフロー完全版の試行
- `corrected_frame_test.py` - フレーム修正テスト
- `csv_corrected_markers.py` - CSV修正版マーカー処理
- `debug_marker_addition.py` - マーカー追加デバッグ
- `debug_timeline_limits.py` - タイムライン制限デバッグ
- `direct_timecode_test.py` - 直接タイムコードテスト
- `final_marker_workflow.py` - 最終マーカーワークフロー
- `reproduce_csv_success.py` - CSV成功再現
- `test_120_frames.py` - 120フレームテスト
- `test_failure_patterns.py` - 失敗パターンテスト
- `test_marker_cut_enhanced.py` - 拡張マーカーカット
- `test_marker_cut_fixed.py` - 修正版マーカーカット
- `test_marker_cut.py` - 基本マーカーカット
- `test_memory_limit.py` - メモリ制限テスト
- `test_track_split_fixed.py` - 修正版トラック分割
- `test_track_split.py` - トラック分割テスト
- `working_marker_script.py` - 作業中マーカースクリプト

## 整理の理由
1. **新環境構築**: `davinci_autocut/` で整理された新環境を作成
2. **混在回避**: 古い試行錯誤ファイルと新しいクリーンなコードの分離
3. **保守性向上**: 17個のファイルは管理が困難

## 新しい構造
```
davinciauto/
├── davinci_autocut/          # 新しいクリーンな環境
│   ├── main.py              # 整理されたメインスクリプト
│   └── lib/resolve_utils.py # ユーティリティ
├── minivt_pipeline/         # 既存の音声自動化
└── archive/                 # 過去の実験ファイル
    └── failed_experiments/
```

## 注意事項
- アーカイブされたファイルは削除されていません
- 必要に応じて参照・復元可能
- 新しい開発は `davinci_autocut/` で実行