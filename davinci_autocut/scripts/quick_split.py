#!/usr/bin/env python3
"""
DaVinci Resolve - クイック分割テスト
現在のタイムラインを指定位置で分割してテスト
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.resolve_utils import tc_to_frames, frames_to_tc

try:
    import DaVinciResolveScript as dvr
except ImportError:
    print("❌ DaVinciResolveScript モジュールが見つかりません")
    sys.exit(1)

def quick_split_test(split_positions=None):
    """現在のタイムラインを指定位置で分割テスト
    
    Args:
        split_positions (list): 分割位置のタイムコードリスト（例: ["01:01:30:00", "01:02:00:00"]）
    """
    
    try:
        # DaVinci Resolveに接続
        resolve = dvr.scriptapp("Resolve")
        if not resolve:
            print("❌ DaVinci Resolveに接続できません")
            return
        
        pm = resolve.GetProjectManager()
        project = pm.GetCurrentProject()
        timeline = project.GetCurrentTimeline()
        
        if not timeline:
            print("❌ アクティブなタイムラインがありません")
            return
        
        # タイムライン情報
        timeline_name = timeline.GetName()
        frame_rate = float(timeline.GetSetting("timelineFrameRate"))
        start_tc = timeline.GetStartTimecode()
        end_tc = timeline.GetEndTimecode()
        
        print(f"🎬 タイムライン: {timeline_name}")
        print(f"🎞️  フレームレート: {frame_rate} fps")
        print(f"⏱️  範囲: {start_tc} 〜 {end_tc}")
        
        # デフォルト分割位置（タイムラインの1/3と2/3の位置）
        if not split_positions:
            start_frame = tc_to_frames(start_tc, frame_rate)
            end_frame = tc_to_frames(end_tc, frame_rate)
            total_duration = end_frame - start_frame
            
            split_frame_1 = start_frame + (total_duration // 3)
            split_frame_2 = start_frame + (2 * total_duration // 3)
            
            split_tc_1 = frames_to_tc(split_frame_1, frame_rate)
            split_tc_2 = frames_to_tc(split_frame_2, frame_rate)
            
            split_positions = [split_tc_1, split_tc_2]
            print(f"📍 自動計算された分割位置: {split_positions}")
        
        # 分割位置をフレーム数に変換
        split_frames = []
        for tc in split_positions:
            frame = tc_to_frames(tc, frame_rate)
            split_frames.append(frame)
            print(f"🔪 分割予定: {tc} (フレーム {frame})")
        
        # 確認
        response = input(f"\n上記の位置でタイムラインを分割しますか？ (y/N): ")
        if response.lower() != 'y':
            print("⏹️  分割をキャンセルしました")
            return
        
        print(f"\n🚀 分割処理開始...")
        
        # トラックごとに分割処理
        for track_type in ["video", "audio"]:
            track_count = timeline.GetTrackCount(track_type)
            print(f"\n📹 {track_type.capitalize()}トラック ({track_count}個) を処理中...")
            
            for i in range(1, track_count + 1):
                clips = timeline.GetItemListInTrack(track_type, i)
                if not clips:
                    print(f"  - {track_type}トラック{i}: クリップなし")
                    continue
                
                print(f"  - {track_type}トラック{i}: {len(clips)}個のクリップを確認")
                
                # 各クリップに対して分割処理
                for clip_id, clip in clips.items():
                    start = clip.GetStart()
                    end = clip.GetEnd()
                    clip_name = clip.GetName() or "Unnamed"
                    
                    # このクリップ内にある分割点で分割（後ろから処理）
                    clip_splits = sorted([f for f in split_frames if start < f < end], reverse=True)
                    
                    if clip_splits:
                        print(f"    📎 '{clip_name}' ({start}-{end}) を {len(clip_splits)}箇所で分割")
                        
                        for split_frame in clip_splits:
                            print(f"      🔪 フレーム {split_frame} で分割実行...")
                            
                            # 再生ヘッドを移動
                            timeline.SetCurrentTimecode(int(split_frame))
                            
                            # クリップ分割
                            result = timeline.SplitClip(clip, int(split_frame))
                            if result:
                                print(f"      ✅ 分割成功")
                            else:
                                print(f"      ⚠️  分割結果不明（APIの戻り値はFalse）")
                    else:
                        print(f"    📎 '{clip_name}': 分割対象外")
        
        print(f"\n🎉 分割処理完了！タイムラインを確認してください。")
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🔪 DaVinci Resolve - クイック分割テスト")
    print("=" * 40)
    
    # コマンドライン引数で分割位置を指定可能
    if len(sys.argv) > 1:
        split_positions = sys.argv[1:]
        print(f"📍 指定された分割位置: {split_positions}")
    else:
        split_positions = None
        print("📍 分割位置：自動計算（1/3, 2/3の位置）")
    
    quick_split_test(split_positions)