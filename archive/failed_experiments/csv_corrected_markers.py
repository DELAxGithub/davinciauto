#!/usr/bin/env python3
# csv_corrected_markers.py
# CSVからマーカーを読み込み、正しいフレーム計算で配置
# 修正版：timeline_start_frameを足さない！

import csv
import os
import sys
from datetime import datetime

def log(msg):
    """タイムスタンプ付きログ出力"""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    try:
        print(f"[{timestamp}] {msg}")
        sys.stdout.flush()
    except Exception:
        pass

def get_timeline():
    """タイムライン取得"""
    try:
        app = sys.modules['__main__'].app
        resolve = app.GetResolve()
        pm = resolve.GetProjectManager()
        project = pm.GetCurrentProject()
        timeline = project.GetCurrentTimeline()
        return timeline
    except Exception as e:
        log(f"❌ Timeline access failed: {e}")
        return None

def clear_existing_markers(timeline):
    """既存マーカークリア"""
    log("\n=== CLEARING EXISTING MARKERS ===")
    try:
        existing_markers = timeline.GetMarkers()
        if existing_markers:
            log(f"🧹 Clearing {len(existing_markers)} existing markers...")
            for frame_id in existing_markers.keys():
                result = timeline.DeleteMarkerAtFrame(int(frame_id))
                log(f"  Delete frame {frame_id}: {result}")
            log(f"✅ Existing markers cleared")
            return True
        else:
            log("No existing markers to clear")
            return True
    except Exception as e:
        log(f"⚠️ Could not clear existing markers: {e}")
        return False

def corrected_timecode_to_frame(timecode_str, fps=24.0):
    """
    修正版：タイムコード → フレーム数変換
    timeline_start_frameを足さない！
    """
    try:
        if not timecode_str or ':' not in timecode_str:
            return None
            
        parts = timecode_str.split(':')
        if len(parts) != 4:
            return None
        
        try:
            hours, minutes, seconds, frames = map(int, parts)
        except ValueError:
            return None
        
        # DaVinci Resolveのデフォルト開始時刻 01:00:00:00 からの相対時間
        # 01:00:10:00 なら 10秒 = 240フレーム
        relative_seconds = (hours - 1) * 3600 + minutes * 60 + seconds
        relative_frames = int(relative_seconds * fps + frames)
        
        log(f"  {timecode_str} → {relative_seconds}s + {frames}f = {relative_frames} frames")
        return relative_frames
        
    except Exception as e:
        log(f"Error converting timecode {timecode_str}: {e}")
        return None

def get_marker_color(index):
    """マーカー色循環"""
    colors = [
        "Blue", "Green", "Red", "Yellow", 
        "Cyan", "Magenta", "Orange", "Pink",
        "Purple", "Lime", "Rose", "Teal",
        "Brown", "Violet", "Indigo", "Maroon",
        "Navy", "Olive", "Silver", "Crimson"
    ]
    return colors[index % len(colors)]

def load_csv_edit_points(csv_path):
    """CSVファイルから編集ポイントを読み込み（Start Time + End Time対応）"""
    log(f"\n=== LOADING CSV: {csv_path} ===")
    
    if not os.path.exists(csv_path):
        log(f"❌ CSV file not found: {csv_path}")
        return []
    
    edit_points = []
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                start_time = row.get('Start Time', '').strip()
                end_time = row.get('End Time', '').strip()
                label = row.get('Label', f'Point_{i+1}').strip()
                
                if start_time and start_time != 'Start Time':
                    point = {
                        'start_timecode': start_time,
                        'end_timecode': end_time if end_time and end_time != 'End Time' else None,
                        'label': label[:20],  # 名前を20文字以内に制限
                        'row': i + 2,
                        'index': i + 1
                    }
                    edit_points.append(point)
        
        log(f"✅ Loaded {len(edit_points)} edit points from CSV")
        range_count = sum(1 for p in edit_points if p['end_timecode'])
        log(f"📍 Range markers: {range_count}, Point markers: {len(edit_points) - range_count}")
        return edit_points
        
    except Exception as e:
        log(f"❌ CSV loading failed: {e}")
        return []

def process_csv_markers(timeline, edit_points, fps):
    """CSVの編集ポイントからマーカーを作成（範囲マーカー対応）"""
    log(f"\n=== PROCESSING {len(edit_points)} CSV MARKERS ===")
    log(f"Using CORRECTED frame calculation (no timeline_start_frame offset)")
    
    success_count = 0
    error_count = 0
    
    for point in edit_points:
        try:
            start_timecode = point['start_timecode']
            end_timecode = point['end_timecode']
            label = point['label']
            index = point['index']
            
            if end_timecode:
                log(f"\n--- Processing {index}: {start_timecode} ~ {end_timecode} (RANGE) ---")
            else:
                log(f"\n--- Processing {index}: {start_timecode} (POINT) ---")
            
            # Start時点のフレーム計算
            start_frame = corrected_timecode_to_frame(start_timecode, fps)
            if start_frame is None:
                log(f"❌ Invalid start timecode: {start_timecode}")
                error_count += 1
                continue
            
            # 範囲マーカーの場合
            if end_timecode:
                end_frame = corrected_timecode_to_frame(end_timecode, fps)
                if end_frame is None:
                    log(f"❌ Invalid end timecode: {end_timecode}")
                    error_count += 1
                    continue
                
                # 範囲マーカーの持続時間計算
                duration = max(1, end_frame - start_frame)
                log(f"  Range: {start_frame} to {end_frame} (duration: {duration} frames)")
                
                # 大きな範囲マーカーの場合は追加の安定化処理
                import time
                if duration > 10000:  # 大きな範囲（~7分以上）
                    log(f"  Large range marker detected, using extended stabilization")
                    time.sleep(0.2)  # 大きな範囲の場合はより長い待機
                else:
                    time.sleep(0.1)  # 通常の安定化待機
                
                marker_result = timeline.AddMarker(
                    start_frame,                         # 開始フレーム
                    get_marker_color(index-1),          # 色（循環）
                    f"C{index:02d}",                    # 短い名前パターン
                    f"{label} ({start_timecode}~{end_timecode})",  # ノート
                    duration                            # 持続時間
                )
                
                # 結果確認のための短い待機
                time.sleep(0.05)
                
                log(f"  AddMarker({start_frame}, '{get_marker_color(index-1)}', 'C{index:02d}', '{label} ({start_timecode}~{end_timecode})', {duration})")
                log(f"  Result: {marker_result}")
                
                if marker_result:
                    log(f"✅ SUCCESS: {start_timecode}~{end_timecode} → {label} (RANGE)")
                    success_count += 1
                else:
                    log(f"❌ FAILED: {start_timecode}~{end_timecode}")
                    error_count += 1
            else:
                # ポイントマーカー（従来通り + API安定化処理）
                import time
                time.sleep(0.1)  # API安定化のための短い待機
                
                marker_result = timeline.AddMarker(
                    start_frame,                    # 相対フレーム番号そのまま
                    get_marker_color(index-1),      # 色（循環）
                    f"P{index:02d}",               # 短い名前パターン（Point）
                    f"{label} ({start_timecode})",        # ノート
                    1                               # 持続時間
                )
                
                # 結果確認のための短い待機
                time.sleep(0.05)
                
                log(f"  AddMarker({start_frame}, '{get_marker_color(index-1)}', 'P{index:02d}', '{label} ({start_timecode})', 1)")
                log(f"  Result: {marker_result}")
                
                if marker_result:
                    log(f"✅ SUCCESS: {start_timecode} → {label} (POINT)")
                    success_count += 1
                else:
                    log(f"❌ FAILED: {start_timecode}")
                    error_count += 1
            
        except Exception as e:
            log(f"❌ Processing error for {start_timecode}: {e}")
            error_count += 1
    
    return success_count, error_count

def verify_csv_markers(timeline, expected_count):
    """CSVマーカーの確認"""
    log(f"\n=== CSV MARKER VERIFICATION ===")
    
    try:
        actual_markers = timeline.GetMarkers()
        if actual_markers:
            actual_count = len(actual_markers)
            log(f"Markers found: {actual_count} (expected: {expected_count})")
            
            # すべてのマーカーを表示
            for frame, info in actual_markers.items():
                timecode = frame_to_display_timecode(int(frame), 24.0)
                log(f"  Frame {frame} ({timecode}): {info.get('name', 'unnamed')} - {info.get('color', 'no color')}")
            
            success_rate = (actual_count / expected_count * 100) if expected_count > 0 else 0
            return actual_count, success_rate
            
        else:
            log("No markers found")
            return 0, 0.0
            
    except Exception as e:
        log(f"Error verifying markers: {e}")
        return 0, 0.0

def frame_to_display_timecode(frame, fps=24.0):
    """フレーム番号を表示用タイムコードに変換"""
    try:
        total_seconds = frame / fps
        hours = int(total_seconds // 3600) + 1  # +1 for 01:00:00:00 start
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)
        frames = int((total_seconds % 1) * fps)
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}"
    except:
        return "00:00:00:00"

def main():
    """メイン処理"""
    log("=== CSV CORRECTED MARKERS SCRIPT ===")
    log("Loading CSV and applying CORRECTED frame calculation")
    
    # タイムライン取得
    timeline = get_timeline()
    if not timeline:
        return False
    
    # タイムライン情報
    timeline_name = timeline.GetName()
    fps = float(timeline.GetSetting("timelineFrameRate") or 24.0)
    timeline_start = timeline.GetStartFrame()  # 参考用のみ
    timeline_end = timeline.GetEndFrame()
    
    log(f"✅ Timeline: {timeline_name}")
    log(f"✅ FPS: {fps}")
    log(f"✅ Timeline range: {timeline_start} - {timeline_end} (reference)")
    
    # CSVファイル指定
    csv_path = "/Users/hiroshikodera/Downloads/cutlist_20250901_212818.csv"
    
    # CSV読み込み
    edit_points = load_csv_edit_points(csv_path)
    if not edit_points:
        log("❌ No edit points loaded from CSV")
        return False
    
    # 既存マーカークリア
    clear_existing_markers(timeline)
    
    # CSVマーカー処理（修正版フレーム計算）
    success_count, error_count = process_csv_markers(timeline, edit_points, fps)
    
    # 結果確認
    actual_count, success_rate = verify_csv_markers(timeline, len(edit_points))
    
    # 最終レポート
    log(f"\n{'='*60}")
    log("CSV CORRECTED MARKERS RESULTS")
    log(f"{'='*60}")
    
    log(f"📊 CSV Points: {len(edit_points)}")
    log(f"✅ Successful: {success_count}")
    log(f"❌ Failed: {error_count}")
    log(f"📍 Actual markers: {actual_count}")
    log(f"📈 Success rate: {success_rate:.1f}%")
    
    if success_rate >= 90:
        log(f"\n🎉 EXCELLENT: {success_rate:.1f}% success rate!")
        log(f"🚀 CSV to DaVinci Resolve workflow is working!")
    elif success_rate >= 70:
        log(f"\n🎯 GOOD: {success_rate:.1f}% success rate")
        log(f"📝 Minor issues to resolve")
    else:
        log(f"\n📋 NEEDS IMPROVEMENT: {success_rate:.1f}% success rate")
    
    log(f"\n🔧 KEY IMPROVEMENTS:")
    log(f"✅ Fixed frame calculation (no timeline_start_frame offset)")
    log(f"✅ Markers now placed at correct timecode positions")
    log(f"✅ Range marker support (Start Time ~ End Time)")
    log(f"✅ Point marker fallback for Start Time only")
    
    return success_rate >= 70

if __name__ == "__main__":
    try:
        success = main()
        if success:
            log("\n✅ CSV marker processing completed successfully")
        else:
            log("\n⚠️ CSV marker processing completed with issues")
    except Exception as e:
        log(f"❌ FATAL ERROR: {e}")
        import traceback
        log(f"Traceback: {traceback.format_exc()}")
    
    try:
        input("Press Enter to exit...")
    except EOFError:
        log("Script completed")
    except Exception:
        pass