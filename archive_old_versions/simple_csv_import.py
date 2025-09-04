#!/usr/bin/env python3
"""
DaVinci Resolve 外部スクリプト - シンプルCSVマーカーインポート
Scripts → Edit メニューから直接実行
"""

import csv
import os
import glob

# =============================================================================
# メイン処理
# =============================================================================

print("🎬 DaVinci Resolve - シンプルCSVマーカーインポート")
print("=" * 50)

try:
    # DaVinci接続確認（外部スクリプトでは resolve が直接利用可能）
    project = resolve.GetProjectManager().GetCurrentProject()
    timeline = project.GetCurrentTimeline()
    
    print(f"✅ プロジェクト: {project.GetName()}")
    print(f"✅ タイムライン: {timeline.GetName()}")
    
except Exception as e:
    print(f"❌ DaVinci接続エラー: {str(e)}")
    print("💡 DaVinciでプロジェクトとタイムラインが開いているか確認してください")
    exit()

# CSVファイル検索
downloads_dir = os.path.expanduser("~/Downloads")
patterns = [
    "ダビンチマーカー - DaVinciMarkers*.csv",
    "*DaVinciMarkers*.csv", 
    "DaVinciMarkers*.csv"
]

csv_file = None
for pattern in patterns:
    files = glob.glob(os.path.join(downloads_dir, pattern))
    if files:
        csv_file = max(files, key=os.path.getmtime)  # 最新ファイル
        break

if not csv_file:
    print("❌ CSVファイルが見つかりません")
    print("💡 Google SheetsからCSVをダウンロードしてください")
    print("   推奨ファイル名: ダビンチマーカー - DaVinciMarkers.csv")
    exit()

print(f"✅ CSVファイル: {os.path.basename(csv_file)}")
print("")

# タイムライン情報取得
timeline_fps = float(timeline.GetSetting("timelineFrameRate"))
timeline_start_frame = timeline.GetStartFrame()

print(f"📊 タイムライン FPS: {timeline_fps}")
print(f"📊 開始フレーム: {timeline_start_frame}")
print("")

# タイムコード変換関数
def timecode_to_frame(timecode_str):
    h, m, s, f = map(int, timecode_str.split(':'))
    input_frames = (h * 3600 + m * 60 + s) * int(timeline_fps) + f
    return input_frames - timeline_start_frame

# 色マッピング
color_map = {
    'rose': 'Red', 'mint': 'Green', 'lemon': 'Yellow',
    'cyan': 'Cyan', 'lavender': 'Purple', 'sky': 'Cyan',
    'sand': 'Yellow', 'cream': 'Blue'
}

# CSVインポート実行
success_count = 0
error_count = 0

print("🚀 マーカーインポート開始...")
print("")

try:
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row_num, row in enumerate(reader, 1):
            try:
                # データ変換
                frame = timecode_to_frame(row['timecode'])
                color = color_map.get(row['color'].lower(), 'Blue')
                duration = int(row.get('duration_frames', 1))
                
                note = f"{row['note']}"
                if row.get('keywords'):
                    note += f" (キーワード: {row['keywords']})"
                
                # マーカー追加
                result = timeline.AddMarker(
                    frame,
                    color, 
                    row['marker_name'],
                    note,
                    duration
                )
                
                if result:
                    print(f"✅ {row['marker_name']} @ {row['timecode']} → フレーム{frame} ({color})")
                    success_count += 1
                else:
                    print(f"❌ API失敗: {row['marker_name']}")
                    error_count += 1
                    
            except Exception as e:
                print(f"❌ 行{row_num}エラー: {str(e)}")
                error_count += 1
    
except Exception as e:
    print(f"❌ CSV処理エラー: {str(e)}")

# 結果表示
print("")
print("=" * 50)
if success_count > 0:
    print(f"🎉 インポート完了: 成功 {success_count}個 / エラー {error_count}個")
    print("✅ タイムライン上でマーカーを確認してください")
else:
    print(f"❌ インポート失敗: エラー {error_count}個")
    print("💡 CSVファイルの形式を確認してください")