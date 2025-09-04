# DaVinci Timeline 情報取得コマンド

タイムコードのオフセット問題を解決するため、タイムライン情報を取得するDaVinciコンソール用コマンドです。

## 🎬 DaVinciコンソールに貼り付けるコード

```python
def get_timeline_info():
    """タイムライン情報取得"""
    try:
        project = resolve.GetProjectManager().GetCurrentProject()
        timeline = project.GetCurrentTimeline()
        
        if not project or not timeline:
            print("❌ プロジェクトまたはタイムラインが見つかりません")
            return None
            
        print("🎬 タイムライン情報")
        print("=" * 50)
        
        # 基本情報
        print(f"📝 プロジェクト名: {project.GetName()}")
        print(f"📝 タイムライン名: {timeline.GetName()}")
        
        # フレームレート
        fps = timeline.GetSetting("timelineFrameRate") 
        print(f"🎞️  フレームレート: {fps} fps")
        
        # タイムライン設定
        start_frame = timeline.GetStartFrame()
        end_frame = timeline.GetEndFrame()
        print(f"📍 開始フレーム: {start_frame}")
        print(f"🏁 終了フレーム: {end_frame}")
        
        # デュレーション
        duration_frames = end_frame - start_frame
        duration_seconds = duration_frames / float(fps) if fps else 0
        print(f"⏱️  総フレーム数: {duration_frames}")
        print(f"⏱️  総時間: {duration_seconds:.2f}秒")
        
        # タイムコード設定
        timecode_start = timeline.GetStartTimecode()
        print(f"🕐 開始タイムコード: {timecode_start}")
        
        # 解像度
        width = timeline.GetSetting("timelineResolutionWidth")
        height = timeline.GetSetting("timelineResolutionHeight")
        print(f"📺 解像度: {width}x{height}")
        
        return {
            'fps': fps,
            'start_frame': start_frame,
            'end_frame': end_frame,
            'start_timecode': timecode_start,
            'width': width,
            'height': height
        }
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        return None

def frame_to_timecode(frame, fps=25):
    """フレーム番号をタイムコードに変換"""
    total_seconds = frame // fps
    frames = frame % fps
    
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}"

def test_timecode_conversion():
    """タイムコード変換テスト"""
    info = get_timeline_info()
    if not info:
        return
        
    print("\n🧮 タイムコード変換テスト")
    print("=" * 50)
    
    # テスト用タイムコード (あなたのCSVから)
    test_timecodes = ["01:07:13:23", "01:08:37:23", "01:10:19:23", "01:15:27:23"]
    
    for tc in test_timecodes:
        print(f"\n📍 テスト: {tc}")
        
        # 現在の変換方法
        def current_method(timecode_str):
            h, m, s, f = map(int, timecode_str.split(':'))
            return (h * 3600 + m * 60 + s) * int(info['fps']) + f
        
        # オフセット考慮の変換方法  
        def offset_method(timecode_str):
            h, m, s, f = map(int, timecode_str.split(':'))
            input_frames = (h * 3600 + m * 60 + s) * int(info['fps']) + f
            return input_frames - info['start_frame']
        
        current_frame = current_method(tc)
        offset_frame = offset_method(tc)
        
        print(f"   現在の方法: フレーム {current_frame}")
        print(f"   オフセット考慮: フレーム {offset_frame}")
        print(f"   タイムライン上での位置: {frame_to_timecode(offset_frame, int(info['fps']))}")
        print(f"   差分: {current_frame - offset_frame} フレーム")

def analyze_marker_positions():
    """現在のマーカー位置を分析"""
    try:
        project = resolve.GetProjectManager().GetCurrentProject()
        timeline = project.GetCurrentTimeline()
        
        if not project or not timeline:
            print("❌ プロジェクトまたはタイムラインが見つかりません")
            return
            
        print("🎯 現在のマーカー分析")
        print("=" * 50)
        
        # マーカー取得（DaVinci API で可能な範囲で）
        try:
            markers = timeline.GetMarkers()
            if markers:
                print(f"📍 マーカー数: {len(markers)}")
                fps = int(timeline.GetSetting("timelineFrameRate"))
                for i, (frame, data) in enumerate(markers.items(), 1):
                    tc = frame_to_timecode(int(frame), fps)
                    print(f"   {i}. フレーム{frame} → {tc} | {data.get('name', 'No Name')}")
            else:
                print("📍 マーカーが見つかりません")
        except Exception as e:
            print(f"📍 マーカー情報の取得に失敗: {e}")
            
    except Exception as e:
        print(f"❌ エラー: {e}")

# 実行用メッセージ
print("📋 関数が定義されました。以下を実行してください:")
print(">>> get_timeline_info()")
print(">>> test_timecode_conversion()")
print(">>> analyze_marker_positions()")
```

## 🚀 使用手順

### 1. 関数定義
上記のPythonコードをDaVinciコンソールに貼り付けて実行

### 2. タイムライン情報取得
```python
get_timeline_info()
```

### 3. タイムコード変換テスト
```python
test_timecode_conversion()
```

### 4. 現在のマーカー分析
```python
analyze_marker_positions()
```

## 📊 取得される情報

- **基本情報**: プロジェクト名、タイムライン名
- **フレームレート**: fps情報
- **フレーム範囲**: 開始フレーム、終了フレーム
- **タイムコード**: 開始タイムコード
- **解像度**: 画面サイズ
- **変換テスト**: 現在の方法 vs オフセット考慮

## 🎯 問題の特定

**現象**: 
- CSV: `01:07:13:23` 
- DaVinci実際: `02:10:02:00`

**原因候補**:
1. **タイムライン開始オフセット**: タイムラインが0フレームから始まっていない
2. **タイムコード基準**: プロジェクト設定とCSVの基準時刻が異なる
3. **フレームレート**: 25fps以外の設定

## 🔧 修正方針

取得した情報を基に、正確なタイムコード変換式を作成：

```python
# 修正版タイムコード変換（オフセット考慮）
def corrected_timecode_to_frame(timecode_str, timeline_info):
    h, m, s, f = map(int, timecode_str.split(':'))
    input_frames = (h * 3600 + m * 60 + s) * int(timeline_info['fps']) + f
    return input_frames - timeline_info['start_frame']
```