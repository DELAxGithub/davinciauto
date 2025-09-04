#!/usr/bin/env python3
"""
DaVinci Resolveコンソールテスト - 現在のシーケンス情報を取得
"""

import sys

try:
    import DaVinciResolveScript as dvr
    print("✅ DaVinciResolveScript モジュール読み込み成功")
except ImportError as e:
    print(f"❌ DaVinciResolveScript モジュールが見つかりません: {e}")
    sys.exit(1)

def get_current_sequence_info():
    """現在のシーケンス（タイムライン）の詳細情報を取得"""
    
    try:
        # DaVinci Resolveに接続
        resolve = dvr.scriptapp("Resolve")
        if not resolve:
            print("❌ DaVinci Resolveに接続できません")
            return
        
        print("✅ DaVinci Resolveに接続成功")
        
        # プロジェクトマネージャーとプロジェクトを取得
        pm = resolve.GetProjectManager()
        project = pm.GetCurrentProject()
        
        if not project:
            print("❌ アクティブなプロジェクトがありません")
            return
            
        print(f"📁 プロジェクト名: {project.GetName()}")
        
        # 現在のタイムラインを取得
        timeline = project.GetCurrentTimeline()
        
        if not timeline:
            print("❌ アクティブなタイムラインがありません")
            return
        
        # タイムライン基本情報
        print(f"\n🎬 タイムライン名: {timeline.GetName()}")
        print(f"📺 解像度: {timeline.GetSetting('timelineResolutionWidth')} x {timeline.GetSetting('timelineResolutionHeight')}")
        print(f"🎞️  フレームレート: {timeline.GetSetting('timelineFrameRate')} fps")
        print(f"⏱️  開始タイムコード: {timeline.GetStartTimecode()}")
        print(f"⏰ 終了タイムコード: {timeline.GetEndTimecode()}")
        
        # トラック情報
        video_tracks = timeline.GetTrackCount("video")
        audio_tracks = timeline.GetTrackCount("audio")
        print(f"\n📹 ビデオトラック数: {video_tracks}")
        print(f"🔊 オーディオトラック数: {audio_tracks}")
        
        # 各ビデオトラックのクリップ情報
        print(f"\n📋 クリップ詳細:")
        for i in range(1, video_tracks + 1):
            clips = timeline.GetItemListInTrack("video", i)
            clip_count = len(clips) if clips else 0
            print(f"  📹 Vトラック{i}: {clip_count}個のクリップ")
            
            if clips:
                for clip_id, clip in clips.items():
                    clip_name = clip.GetName() or "Unnamed"
                    start_frame = clip.GetStart()
                    end_frame = clip.GetEnd()
                    duration = clip.GetDuration()
                    print(f"    - '{clip_name}': {start_frame}〜{end_frame} ({duration}フレーム)")
        
        # 各オーディオトラックのクリップ情報
        for i in range(1, audio_tracks + 1):
            clips = timeline.GetItemListInTrack("audio", i)
            clip_count = len(clips) if clips else 0
            print(f"  🔊 Aトラック{i}: {clip_count}個のクリップ")
            
            if clips and i <= 2:  # 最初の2トラックのみ詳細表示（多すぎる場合）
                for clip_id, clip in clips.items():
                    clip_name = clip.GetName() or "Unnamed"
                    start_frame = clip.GetStart()
                    end_frame = clip.GetEnd()
                    duration = clip.GetDuration()
                    print(f"    - '{clip_name}': {start_frame}〜{end_frame} ({duration}フレーム)")
        
        # マーカー情報
        markers = timeline.GetMarkers()
        if markers:
            print(f"\n🏷️  既存マーカー: {len(markers)}個")
            for marker_id, marker_data in markers.items():
                print(f"  - ID{marker_id}: {marker_data}")
        else:
            print(f"\n🏷️  既存マーカー: なし")
        
        print(f"\n✅ シーケンス情報取得完了")
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🎬 DaVinci Resolve - 現在のシーケンス情報取得")
    print("=" * 50)
    get_current_sequence_info()