# DaVinci Resolve API環境設定デバッグ

## エラー: `ModuleNotFoundError: No module named 'DaVinciResolveScript'`

### 📋 原因と対策

DaVinci ResolveのPythonコンソールでDaVinciResolveScriptモジュールが見つからない場合の診断と修正方法

## 🔍 Step 1: 環境変数確認

### DaVinci Resolveコンソールで実行:
```python
import sys; import os; print("Python Path:"); [print(f"  {p}") for p in sys.path]; print(f"\nRESOLVE_SCRIPT_API: {os.environ.get('RESOLVE_SCRIPT_API', 'None')}"); print(f"RESOLVE_SCRIPT_LIB: {os.environ.get('RESOLVE_SCRIPT_LIB', 'None')}")
```

## 🛠️ Step 2: 手動パス追加

### macOSの場合（通常のパス）:
```python
import sys; sys.path.append("/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules/"); print("パス追加完了")
```

### その後importテスト:
```python
import DaVinciResolveScript as dvr; print("✅ import成功")
```

## 🔧 Step 3: 代替方法 - 直接Resolve API使用

DaVinciResolveScriptが使えない場合は、Resolveの内蔵オブジェクトを直接使用:

### Resolveオブジェクト直接取得:
```python
try: resolve = scriptapp("Resolve"); print(f"✅ Resolve直接接続成功: {resolve}")
except: print("❌ scriptapp使用不可")
```

### プロジェクト・タイムライン情報取得:
```python
resolve = scriptapp("Resolve"); project = resolve.GetProjectManager().GetCurrentProject(); timeline = project.GetCurrentTimeline(); print(f"プロジェクト: {project.GetName()}, タイムライン: {timeline.GetName()}")
```

## 🎯 Step 4: 簡易テストコマンド集

### タイムライン基本情報（DaVinciResolveScript不使用版）:
```python
resolve = scriptapp("Resolve"); project = resolve.GetProjectManager().GetCurrentProject(); timeline = project.GetCurrentTimeline(); print(f"タイムライン: {timeline.GetName()}, FPS: {timeline.GetSetting('timelineFrameRate')}")
```

### トラック数確認:
```python
resolve = scriptapp("Resolve"); timeline = resolve.GetProjectManager().GetCurrentProject().GetCurrentTimeline(); print(f"V: {timeline.GetTrackCount('video')}本, A: {timeline.GetTrackCount('audio')}本")
```

### V1の最初のクリップを中央で分割:
```python
resolve = scriptapp("Resolve"); timeline = resolve.GetProjectManager().GetCurrentProject().GetCurrentTimeline(); clips = timeline.GetItemListInTrack('video', 1); clip = list(clips.values())[0] if clips else None; split_frame = (clip.GetStart() + clip.GetEnd()) // 2 if clip else None; print(f"分割フレーム: {split_frame}"); timeline.SetCurrentTimecode(int(split_frame)) if split_frame else None; result = timeline.SplitClip(clip, int(split_frame)) if clip and split_frame else None; print(f"分割結果: {result}")
```

### 現在位置にテストマーカー追加:
```python
resolve = scriptapp("Resolve"); timeline = resolve.GetProjectManager().GetCurrentProject().GetCurrentTimeline(); frame = timeline.GetCurrentTimecode(); result = timeline.AddMarker(int(frame), "Red", "テスト", "コンソールテスト", 30); print(f"マーカー追加: {result} @ {frame}")
```

## 📝 Note

DaVinci Resolveのコンソール内では `scriptapp("Resolve")` が直接使用可能な場合があります。
`DaVinciResolveScript` モジュールは外部Pythonスクリプト用で、内蔵コンソールでは不要な可能性があります。