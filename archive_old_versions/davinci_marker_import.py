#!/usr/bin/env python3
"""
DaVinci Resolve 外部スクリプト - CSVマーカーインポート
Scripts → Edit メニューから直接実行
"""

import csv
import os
import glob

def get_resolve_connection():
    """DaVinci Resolve接続取得（外部スクリプト用）"""
    try:
        # DaVinci外部スクリプトでは resolve が直接利用可能
        if 'resolve' not in globals():
            print("❌ DaVinci Resolve環境でスクリプトを実行してください")
            return None, None, None
        
        if not resolve:
            print("❌ DaVinci Resolveに接続できません")
            return None, None, None
            
        project_manager = resolve.GetProjectManager()
        project = project_manager.GetCurrentProject()
        if not project:
            print("❌ プロジェクトが開いていません")
            return None, None, None
            
        timeline = project.GetCurrentTimeline()
        if not timeline:
            print("❌ タイムラインが選択されていません")
            return None, None, None
            
        return resolve, project, timeline
        
    except Exception as e:
        print(f"❌ DaVinci Resolve接続エラー: {str(e)}")
        return None, None, None

def find_latest_csv():
    """最新のDaVinciマーカーCSVを検索"""
    downloads_dir = os.path.expanduser("~/Downloads")
    
    patterns = [
        "ダビンチマーカー - DaVinciMarkers*.csv",
        "*DaVinciMarkers*.csv", 
        "DaVinciMarkers*.csv",
        "davinci*markers*.csv"
    ]
    
    latest_file = None
    latest_time = 0
    
    for pattern in patterns:
        files = glob.glob(os.path.join(downloads_dir, pattern))
        for file in files:
            mtime = os.path.getmtime(file)
            if mtime > latest_time:
                latest_time = mtime
                latest_file = file
    
    return latest_file

def select_csv_file():
    """CSVファイル選択（外部スクリプト用 - 自動検出のみ）"""
    # 最新ファイル自動検出
    auto_file = find_latest_csv()
    if auto_file:
        print(f"✅ 最新CSVファイルを検出: {os.path.basename(auto_file)}")
        return auto_file
    else:
        print("❌ CSVファイルが見つかりません")
        print("💡 Google SheetsからCSVをダウンロードしてください")
        print("   推奨ファイル名: ダビンチマーカー - DaVinciMarkers.csv")
        return None

def import_csv_markers(csv_path, timeline):
    """CSVファイルからマーカーインポート"""
    try:
        # タイムライン情報
        timeline_fps = float(timeline.GetSetting("timelineFrameRate"))
        timeline_start_frame = timeline.GetStartFrame()
        
        print(f"タイムライン FPS: {timeline_fps}")
        print(f"開始フレーム: {timeline_start_frame}")
        
        # タイムコード → フレーム変換
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
        
        success_count = 0
        error_count = 0
        
        with open(csv_path, 'r', encoding='utf-8') as f:
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
                        print(f"✅ {row['marker_name']} @ {row['timecode']} → フレーム{frame}")
                        success_count += 1
                    else:
                        print(f"❌ API失敗: {row['marker_name']}")
                        error_count += 1
                        
                except Exception as e:
                    print(f"❌ 行{row_num}エラー: {str(e)}")
                    error_count += 1
        
        return success_count, error_count
        
    except Exception as e:
        print(f"❌ CSV処理エラー: {str(e)}")
        return 0, 1

def main():
    """メイン実行関数"""
    print("🎬 DaVinci Resolve - CSVマーカーインポート開始")
    print("=" * 50)
    
    # DaVinci接続
    resolve_obj, project, timeline = get_resolve_connection()
    if not all([resolve_obj, project, timeline]):
        return
    
    print(f"✅ 接続成功: プロジェクト '{project.GetName()}'")
    print(f"✅ タイムライン: '{timeline.GetName()}'")
    
    # CSVファイル選択
    csv_path = select_csv_file()
    if not csv_path:
        print("❌ CSVファイルの選択に失敗しました")
        return
    
    if not os.path.exists(csv_path):
        print(f"❌ ファイルが見つかりません: {csv_path}")
        return
    
    print(f"✅ CSVファイル: {os.path.basename(csv_path)}")
    print("")
    print("📋 インポート設定:")
    print(f"   プロジェクト: {project.GetName()}")
    print(f"   タイムライン: {timeline.GetName()}")
    print(f"   CSVファイル: {os.path.basename(csv_path)}")
    print("")
    
    # マーカーインポート実行
    print("🚀 マーカーインポート開始...")
    success_count, error_count = import_csv_markers(csv_path, timeline)
    
    # 結果表示
    print("")
    print("=" * 50)
    if success_count > 0:
        print(f"🎉 インポート完了: 成功 {success_count}個 / エラー {error_count}個")
        print("✅ タイムライン上でマーカーを確認してください")
    else:
        print(f"❌ インポート失敗: エラー {error_count}個")
        print("💡 CSVファイルの形式を確認してください")

if __name__ == "__main__":
    main()