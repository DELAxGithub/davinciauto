#!/usr/bin/env python3
"""
DaVinci Resolve コンソール用マーカー付与スクリプト
DaVinci内蔵Pythonコンソールで直接実行
"""

# DaVinci Resolve内蔵コンソールではAPIが自動で利用可能

def test_markers_console():
    """DaVinci内蔵コンソール用テストマーカー"""
    
    try:
        # 現在のプロジェクトとタイムライン取得
        project = resolve.GetProjectManager().GetCurrentProject()
        if not project:
            print("❌ プロジェクトが開いていません")
            return False
            
        timeline = project.GetCurrentTimeline()
        if not timeline:
            print("❌ タイムラインが選択されていません")
            return False
            
        print(f"✅ 接続成功: プロジェクト '{project.GetName()}'")
        print(f"✅ タイムライン: '{timeline.GetName()}'")
        
        # 話題別色分けテストマーカー
        test_data = [
            {"frame": 375, "color": "Blue", "name": "番組開始", "note": "オープニング話題", "duration": 75},
            {"frame": 1250, "color": "Red", "name": "重要発言", "note": "メインテーマ話題 - カット不可", "duration": 150},  
            {"frame": 2750, "color": "Green", "name": "深掘り開始", "note": "深掘り討論話題", "duration": 300},
            {"frame": 4500, "color": "Yellow", "name": "CMタイム", "note": "コマーシャル話題", "duration": 1500},
            {"frame": 6000, "color": "Blue", "name": "番組終了", "note": "オープニング話題に戻る", "duration": 100}
        ]
        
        success_count = 0
        for i, data in enumerate(test_data, 1):
            try:
                result = timeline.AddMarker(
                    data["frame"], 
                    data["color"], 
                    data["name"], 
                    data["note"], 
                    data["duration"]
                )
                
                if result:
                    print(f"✅ {i}. {data['name']} @ フレーム{data['frame']} ({data['color']}) - {data['note']}")
                    success_count += 1
                else:
                    print(f"❌ {i}. マーカー追加失敗: {data['name']}")
                    
            except Exception as e:
                print(f"❌ {i}. エラー: {data['name']} - {e}")
                
        print(f"\n🎉 結果: {success_count}/{len(test_data)} 個のマーカーを追加")
        print("\n📋 色分けルール:")
        print("   🔵 Blue: オープニング話題")
        print("   🔴 Red: メインテーマ話題")  
        print("   🟢 Green: 深掘り討論話題")
        print("   🟡 Yellow: コマーシャル話題")
        
        return success_count > 0
        
    except Exception as e:
        print(f"❌ 実行エラー: {e}")
        return False

def add_csv_markers_console(csv_path):
    """CSVファイルからマーカー追加（DaVinciコンソール用）"""
    import csv
    
    try:
        project = resolve.GetProjectManager().GetCurrentProject()
        timeline = project.GetCurrentTimeline()
        
        if not project or not timeline:
            print("❌ プロジェクトまたはタイムラインが見つかりません")
            return False
            
        print(f"✅ CSVマーカー付与開始: {csv_path}")
        
        # タイムライン情報取得
        timeline_fps = float(timeline.GetSetting("timelineFrameRate"))
        timeline_start_frame = timeline.GetStartFrame()
        
        print(f"🎞️  タイムライン情報: {timeline_fps}fps, 開始フレーム: {timeline_start_frame}")
        
        # タイムコード → フレーム変換関数（オフセット修正版）
        def timecode_to_frame(timecode_str, fps=None):
            if fps is None:
                fps = int(timeline_fps)
            h, m, s, f = map(int, timecode_str.split(':'))
            input_frames = (h * 3600 + m * 60 + s) * fps + f
            # タイムライン開始フレーム分を差し引く
            return input_frames - timeline_start_frame
        
        # フレーム → タイムコード変換関数（アウト点表示用）
        def frame_to_timecode(frame, fps=None):
            if fps is None:
                fps = int(timeline_fps)
            # タイムライン開始フレーム分を加える
            total_frames = frame + timeline_start_frame
            h = int(total_frames // (fps * 3600))
            m = int((total_frames % (fps * 3600)) // (fps * 60))
            s = int((total_frames % (fps * 60)) // fps)
            f = int(total_frames % fps)
            return f"{h:02d}:{m:02d}:{s:02d}:{f:02d}"
        
        # 色マッピング（GAS色名 → DaVinci色名）
        color_map = {
            'blue': 'Blue', 'red': 'Red', 'green': 'Green', 
            'yellow': 'Yellow', 'cyan': 'Cyan', 'purple': 'Purple',
            # GAS最終版の色対応
            'rose': 'Red', 'mint': 'Green', 'lemon': 'Yellow',
            'lavender': 'Purple', 'sky': 'Cyan', 'sand': 'Yellow', 'cream': 'Blue'
        }
        
        success_count = 0
        error_count = 0
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row_num, row in enumerate(reader, 1):
                try:
                    # CSV形式の判定（新形式はtimecode_in/timecode_out、旧形式はtimecode）
                    if 'timecode_in' in row:
                        # 新形式（アウト点明示）
                        timecode_in = row['timecode_in']
                        timecode_out = row['timecode_out']
                        frame_in = timecode_to_frame(timecode_in)
                        frame_out = timecode_to_frame(timecode_out) 
                        duration_frames = frame_out - frame_in
                    else:
                        # 旧形式（デュレーション計算）
                        timecode_in = row['timecode']
                        frame_in = timecode_to_frame(timecode_in)
                        duration_frames = int(row.get('duration_frames', 1))
                        frame_out = frame_in + duration_frames
                        timecode_out = frame_to_timecode(frame_out)
                    
                    # 色変換
                    color = color_map.get(row['color'].lower(), 'Blue')
                    
                    # デバッグ情報
                    print(f"🔍 {row_num}. {timecode_in}-{timecode_out} → フレーム{frame_in}-{frame_out} ({row['marker_name']})")
                    
                    # マーカー追加（アウト点情報をnoteに含める）
                    enhanced_note = f"{row['note']} | アウト点: {timecode_out} | キーワード: {row.get('keywords', 'なし')}"
                    
                    result = timeline.AddMarker(
                        frame_in,
                        color,
                        row['marker_name'],
                        enhanced_note,
                        duration_frames
                    )
                    
                    if result:
                        print(f"✅ {row_num}. {row['marker_name']} @ {timecode_in}-{timecode_out} ({color})")
                        success_count += 1
                    else:
                        print(f"❌ {row_num}. API失敗: {row['marker_name']}")
                        error_count += 1
                        
                except Exception as e:
                    print(f"❌ {row_num}. エラー: {row.get('marker_name', '不明')} - {e}")
                    error_count += 1
                    
        print(f"\n🎉 処理完了: 成功 {success_count}個 / エラー {error_count}個")
        return success_count > 0
        
    except Exception as e:
        print(f"❌ CSV処理エラー: {e}")
        return False

# =============================================================================
# 🎬 DaVinci内蔵コンソール実行用
# =============================================================================

def run_test():
    """テスト実行関数"""
    print("🎬 DaVinci内蔵コンソール - マーカーテスト")
    print("=" * 50)
    test_markers_console()

def find_latest_davinci_csv():
    """ダウンロードフォルダから最新のDaVinciマーカーCSVを検索"""
    import os
    import glob
    
    downloads_dir = "/Users/hiroshikodera/Downloads"
    
    # パターン検索（実際のファイル名パターンに対応）
    patterns = [
        "ダビンチマーカー - DaVinciMarkers*.csv",  # 実際のファイル名
        "*DaVinciMarkers*.csv",
        "DaVinciMarkers*.csv",
        "davinci*markers*.csv", 
        "ダビンチマーカー*.csv"
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

def run_csv(csv_file=None):
    """CSV実行関数 - デフォルトでDownloadsのDaVinci区間マーカーCSVを読み込み"""
    import os
    
    # デフォルトパス設定
    if csv_file is None:
        # 最新ファイルを自動検索
        csv_path = find_latest_davinci_csv()
        if csv_path:
            display_name = os.path.basename(csv_path)
        else:
            # フォールバック: 実際のファイル名パターン
            csv_path = "/Users/hiroshikodera/Downloads/ダビンチマーカー - DaVinciMarkers.csv"
            display_name = "ダビンチマーカー - DaVinciMarkers.csv"
    else:
        # 相対パス指定の場合は従来通りプロジェクトディレクトリから
        csv_path = f"/Users/hiroshikodera/repos/_active/tools/davinciauto/{csv_file}"
        display_name = csv_file
    
    print(f"🎬 DaVinci内蔵コンソール - CSV実行: {display_name}")
    print("=" * 50)
    
    if not csv_path or not os.path.exists(csv_path):
        print(f"❌ ファイルが見つかりません: {csv_path}")
        if csv_file is None:
            print("💡 ヒント: Google Sheetsの「DaVinciMarkers」シートをCSVダウンロードしてください")
            print("   ファイル名: ダビンチマーカー - DaVinciMarkers.csv")
        return False
    
    print(f"✅ ファイル確認: {csv_path}")    
    add_csv_markers_console(csv_path)

# コンソールで直接実行用の関数を定義
print("""
🎬 DaVinci Resolve 内蔵コンソール用マーカー関数

使用方法:
  run_csv()                          # 最新のDaVinciマーカーCSV自動読み込み
  run_test()                          # テストマーカー付与
  run_csv("your_file.csv")           # 指定ファイル読み込み

例:
  >>> run_csv()                       # 毎回これだけでOK！最新ファイル自動検出
  
🔍 自動検索パターン:
   • ダビンチマーカー - DaVinciMarkers*.csv (推奨)
   • *DaVinciMarkers*.csv
   • DaVinciMarkers*.csv
   • davinci*markers*.csv
   
📁 検索場所: /Users/hiroshikodera/Downloads/
""")