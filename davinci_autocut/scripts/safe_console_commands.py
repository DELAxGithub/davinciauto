#!/usr/bin/env python3
"""
プロ仕様・安全なタイムコードベースのDaVinci Resolveコンソールテスト

スーパーバイザーの教え：
- GetCurrentFrame()は存在しない (None)
- タイムコード文字列から自力でフレーム番号を計算する
- APIドキュメントを鵜呑みにしない、実際に確認する
"""

def tc_to_frames_inline(tc_string, frame_rate):
    """タイムコード文字列を総フレーム数に変換（インライン版）"""
    h, m, s, f = map(int, tc_string.split(':'))
    return (h * 3600 + m * 60 + s) * int(frame_rate) + f

def print_safe_commands():
    """DaVinci Resolveコンソール用の安全なワンライナーコマンド集を表示"""
    
    print("🎬 プロ仕様・安全なDaVinci Resolveコンソールコマンド集")
    print("=" * 60)
    
    print("\n## 🔍 API検証（スーパーバイザー推奨）")
    print("resolve = scriptapp('Resolve'); timeline = resolve.GetProjectManager().GetCurrentProject().GetCurrentTimeline(); print(f'Timeline: {timeline}'); print(f'GetCurrentFrame: {getattr(timeline, \"GetCurrentFrame\", \"Not Found\")}'); print(f'AddMarker: {getattr(timeline, \"AddMarker\", \"Not Found\")}')")
    
    print("\n## 📊 基本情報取得（確実版）")
    print("resolve = scriptapp('Resolve'); project = resolve.GetProjectManager().GetCurrentProject(); timeline = project.GetCurrentTimeline(); print(f'プロジェクト: {project.GetName()}'); print(f'タイムライン: {timeline.GetName()}'); print(f'FPS: {timeline.GetSetting(\"timelineFrameRate\")}'); print(f'開始: {timeline.GetStartTimecode()}'); print(f'終了: {timeline.GetEndTimecode()}')")
    
    print("\n## 🎞️ タイムコードベース・現在位置取得")
    print("resolve = scriptapp('Resolve'); timeline = resolve.GetProjectManager().GetCurrentProject().GetCurrentTimeline(); current_tc = timeline.GetCurrentTimecode(); frame_rate = float(timeline.GetSetting('timelineFrameRate')); h, m, s, f = map(int, current_tc.split(':')); current_frame = (h * 3600 + m * 60 + s) * int(frame_rate) + f; print(f'現在位置: {current_tc} = {current_frame}フレーム @ {frame_rate}fps')")
    
    print("\n## 🔪 安全な分割テスト（タイムコードベース）")
    print("resolve = scriptapp('Resolve'); timeline = resolve.GetProjectManager().GetCurrentProject().GetCurrentTimeline(); clips = timeline.GetItemListInTrack('video', 1); clip = list(clips.values())[0] if clips else None; start_tc = timeline.GetStartTimecode(); end_tc = timeline.GetEndTimecode(); frame_rate = float(timeline.GetSetting('timelineFrameRate')); h1, m1, s1, f1 = map(int, start_tc.split(':')); h2, m2, s2, f2 = map(int, end_tc.split(':')); start_frame = (h1 * 3600 + m1 * 60 + s1) * int(frame_rate) + f1; end_frame = (h2 * 3600 + m2 * 60 + s2) * int(frame_rate) + f2; split_frame = start_frame + (end_frame - start_frame) // 3; timeline.SetCurrentTimecode(int(split_frame)); print(f'1/3地点({split_frame}フレーム)に再生ヘッドを移動')")
    
    print("\n## 🏷️ 確実なマーカー追加（タイムコードベース）")
    print("resolve = scriptapp('Resolve'); timeline = resolve.GetProjectManager().GetCurrentProject().GetCurrentTimeline(); current_tc = timeline.GetCurrentTimecode(); frame_rate = float(timeline.GetSetting('timelineFrameRate')); h, m, s, f = map(int, current_tc.split(':')); current_frame = (h * 3600 + m * 60 + s) * int(frame_rate) + f; result = timeline.AddMarker(int(current_frame), 'Blue', 'プロテスト', f'タイムコード{current_tc}からフレーム{current_frame}を計算', 60); print(f'マーカー追加結果: {result} @ {current_tc} ({current_frame}フレーム)')")
    
    print("\n## ⚡ V1トラック最初のクリップを中央分割（完全版）")
    print("resolve = scriptapp('Resolve'); timeline = resolve.GetProjectManager().GetCurrentProject().GetCurrentTimeline(); clips = timeline.GetItemListInTrack('video', 1); clip = list(clips.values())[0] if clips else None; start_frame = clip.GetStart() if clip else 0; end_frame = clip.GetEnd() if clip else 0; split_frame = (start_frame + end_frame) // 2 if clip else 0; timeline.SetCurrentTimecode(int(split_frame)) if clip else None; result = timeline.SplitClip(clip, int(split_frame)) if clip else False; print(f'クリップ分割: {clip.GetName() if clip else \"なし\"}, フレーム{start_frame}-{end_frame}, 分割位置{split_frame}, 結果{result}')")
    
    print("\n## 🎯 タイムライン情報完全取得")
    print("resolve = scriptapp('Resolve'); timeline = resolve.GetProjectManager().GetCurrentProject().GetCurrentTimeline(); start_tc = timeline.GetStartTimecode(); end_tc = timeline.GetEndTimecode(); frame_rate = float(timeline.GetSetting('timelineFrameRate')); h1, m1, s1, f1 = map(int, start_tc.split(':')); h2, m2, s2, f2 = map(int, end_tc.split(':')); start_frame = (h1 * 3600 + m1 * 60 + s1) * int(frame_rate) + f1; end_frame = (h2 * 3600 + m2 * 60 + s2) * int(frame_rate) + f2; duration = end_frame - start_frame; print(f'タイムライン: {timeline.GetName()}, {frame_rate}fps'); print(f'範囲: {start_tc}({start_frame}) 〜 {end_tc}({end_frame})'); print(f'長さ: {duration}フレーム = {duration/frame_rate:.2f}秒'); print(f'トラック: V{timeline.GetTrackCount(\"video\")} A{timeline.GetTrackCount(\"audio\")}')")

if __name__ == "__main__":
    print_safe_commands()