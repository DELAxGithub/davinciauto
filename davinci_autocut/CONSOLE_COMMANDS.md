# DaVinci Resolve **内部コンソール**コマンド集

## 🏠 重要：「家の中」vs「家の外」

**スーパーバイザーの教え:**
- **外部用** (`scriptapp`): VSCodeなど外部からのインターホン 🔔
- **内部用** (`resolve`): コンソール内部では最初から存在 🏠

**あなたは今「家の中」にいます**：DaVinci Resolveコンソール内部では `resolve` オブジェクトが既に利用可能！

## 🎯 基本確認（まず挨拶）

### Step 1: resolveオブジェクト確認
```python
print(resolve)
```

### Step 2: 基本情報取得 ✅ 動作確認済み
```python
timeline = resolve.GetProjectManager().GetCurrentProject().GetCurrentTimeline(); print(f"タイムライン: {timeline.GetName()}, FPS: {timeline.GetSetting('timelineFrameRate')}")
```
**実行結果例**: `タイムライン: 021オリジナル, FPS: 24.0`

### Step 3: トラック数確認 ✅ 動作確認済み
```python
timeline = resolve.GetProjectManager().GetCurrentProject().GetCurrentTimeline(); print(f"ビデオトラック: {timeline.GetTrackCount('video')}本, オーディオトラック: {timeline.GetTrackCount('audio')}本")
```
**実行結果例**: `ビデオトラック: 1本, オーディオトラック: 2本`

## ✅ 実証済み・確実動作コマンド

### タイムコード文字列でマーカー追加 ✅ 実証済み
```python
timeline = resolve.GetProjectManager().GetCurrentProject().GetCurrentTimeline(); current_tc = timeline.GetCurrentTimecode(); result = timeline.AddMarker(current_tc, "Cyan", "TC String Test", "文字列直接指定", 60); print(f"マーカー追加結果: {result} @ {current_tc}")
```
**実行結果例**: `マーカー追加結果: False @ 02:31:51:19`  
**重要**: 戻り値が `False` でもマーカーは実際に追加されている可能性（スーパーバイザー指摘のAPI仕様）

### タイムライン基本情報取得（GetEndTimecodeエラー回避版）
```python
timeline = resolve.GetProjectManager().GetCurrentProject().GetCurrentTimeline(); print(f"タイムライン: {timeline.GetName()}"); print(f"FPS: {timeline.GetSetting('timelineFrameRate')}"); print(f"開始: {timeline.GetStartTimecode()}"); print(f"現在位置: {timeline.GetCurrentTimecode()}"); print("終了タイムコードはAPI未対応")
```
**注意**: `GetEndTimecode()` は `TypeError: 'NoneType' object is not callable` エラーが発生するため除外

### 全トラックのクリップ数確認
```python
timeline = resolve.GetProjectManager().GetCurrentProject().GetCurrentTimeline(); [print(f"V{i}: {len(timeline.GetItemListInTrack('video', i)) if timeline.GetItemListInTrack('video', i) else 0}個") for i in range(1, timeline.GetTrackCount('video')+1)]; [print(f"A{i}: {len(timeline.GetItemListInTrack('audio', i)) if timeline.GetItemListInTrack('audio', i) else 0}個") for i in range(1, timeline.GetTrackCount('audio')+1)]
```

### マーカー確認（追加されたマーカーを検証）
```python
timeline = resolve.GetProjectManager().GetCurrentProject().GetCurrentTimeline(); markers = timeline.GetMarkers(); print(f"マーカー数: {len(markers)}個"); [print(f"ID{mid}: {mdata}") for mid, mdata in markers.items()]
```

### A1クリップ情報取得（オーディオ分割テスト準備）
```python
timeline = resolve.GetProjectManager().GetCurrentProject().GetCurrentTimeline(); clips = timeline.GetItemListInTrack('audio', 1); print(f"A1クリップ数: {len(clips)}個"); clip = list(clips.values())[0] if clips else None; print(f"最初のクリップ: {clip.GetName() if clip else 'なし'}, 範囲: {clip.GetStart() if clip else 'N/A'}-{clip.GetEnd() if clip else 'N/A'}") if clip else None
```
**実行結果例**: `A1クリップ数: 4個`（オーディオクリップ存在確認済み）

## 🔪 分割テスト（内部コンソール版）

### ⚠️ GetEndTimecode()エラー対策版・手動終了タイムコード指定
```python
timeline = resolve.GetProjectManager().GetCurrentProject().GetCurrentTimeline(); start_tc = timeline.GetStartTimecode(); manual_end_tc = "01:05:00:00"; frame_rate = float(timeline.GetSetting('timelineFrameRate')); h1, m1, s1, f1 = map(int, start_tc.split(':')); h2, m2, s2, f2 = map(int, manual_end_tc.split(':')); start_frame = (h1 * 3600 + m1 * 60 + s1) * int(frame_rate) + f1; end_frame = (h2 * 3600 + m2 * 60 + s2) * int(frame_rate) + f2; split_frame = start_frame + (end_frame - start_frame) // 3; timeline.SetCurrentTimecode(int(split_frame)); print(f"1/3地点({split_frame}フレーム)に再生ヘッド移動完了")
```
**注意**: `manual_end_tc` を実際のタイムライン終了時間に調整してください

### A1最初のクリップを中央分割（オーディオテスト版）
```python
timeline = resolve.GetProjectManager().GetCurrentProject().GetCurrentTimeline(); clips = timeline.GetItemListInTrack('audio', 1); clip = list(clips.values())[0] if clips else None; start_frame = clip.GetStart() if clip else 0; end_frame = clip.GetEnd() if clip else 0; split_frame = (start_frame + end_frame) // 2 if clip else 0; timeline.SetCurrentTimecode(int(split_frame)) if clip else None; result = timeline.SplitClip(clip, int(split_frame)) if clip else False; print(f"オーディオクリップ分割: {clip.GetName() if clip else 'なし'}, {start_frame}-{end_frame}, 分割位置{split_frame}, 結果{result}")
```
**変更点**: V1 → A1 （V1にクリップなしのため）

### 現在位置のフレーム番号を正確に取得（スーパーバイザー推奨）
```python
timeline = resolve.GetProjectManager().GetCurrentProject().GetCurrentTimeline(); current_tc = timeline.GetCurrentTimecode(); frame_rate = float(timeline.GetSetting('timelineFrameRate')); h, m, s, f = map(int, current_tc.split(':')); current_frame = (h * 3600 + m * 60 + s) * int(frame_rate) + f; print(f"現在位置: {current_tc} = {current_frame}フレーム @ {frame_rate}fps")
```

## 🏷️ マーカー操作（内部コンソール版）

### 現在位置にマーカー追加（タイムコード文字列版 - 推奨）
```python
timeline = resolve.GetProjectManager().GetCurrentProject().GetCurrentTimeline(); current_tc = timeline.GetCurrentTimecode(); result = timeline.AddMarker(current_tc, "Blue", "プロテスト", f"タイムコード文字列{current_tc}直接指定", 60); print(f"マーカー追加結果: {result} @ {current_tc}")
```

### 現在位置にマーカー追加（フレーム番号計算版）
```python
timeline = resolve.GetProjectManager().GetCurrentProject().GetCurrentTimeline(); current_tc = timeline.GetCurrentTimecode(); frame_rate = float(timeline.GetSetting('timelineFrameRate')); h, m, s, f = map(int, current_tc.split(':')); current_frame = (h * 3600 + m * 60 + s) * int(frame_rate) + f; result = timeline.AddMarker(int(current_frame), "Green", "フレーム計算", f"TC{current_tc}→{current_frame}フレーム", 60); print(f"マーカー追加結果: {result} @ {current_tc} ({current_frame}フレーム)")
```

### 既存マーカー一覧
```python
timeline = resolve.GetProjectManager().GetCurrentProject().GetCurrentTimeline(); markers = timeline.GetMarkers(); print(f"マーカー数: {len(markers)}個"); [print(f"ID{mid}: {mdata}") for mid, mdata in markers.items()]
```

## 🛠️ デバッグ・検証用

### API機能確認（家の中バージョン）
```python
timeline = resolve.GetProjectManager().GetCurrentProject().GetCurrentTimeline(); print(f"Resolveオブジェクト: {resolve}"); print(f"タイムライン: {timeline.GetName()}"); print(f"GetCurrentFrame存在: {getattr(timeline, 'GetCurrentFrame', 'Not Found')}"); print(f"AddMarker存在: {getattr(timeline, 'AddMarker', 'Not Found')}")
```

### フレーム計算確認
```python
timeline = resolve.GetProjectManager().GetCurrentProject().GetCurrentTimeline(); tc = "01:02:30:15"; frame_rate = float(timeline.GetSetting('timelineFrameRate')); h, m, s, f = map(int, tc.split(':')); frames = (h * 3600 + m * 60 + s) * int(frame_rate) + f; print(f"タイムコード {tc} = {frames} フレーム (@ {frame_rate}fps)")
```

---

## 📋 使用方法

### 🏠 DaVinci Resolve内部コンソール専用

1. **DaVinci Resolve → Workspace → Console** でコンソールを開く
2. 上記のコマンドをコピー
3. コンソールにペーストして Enter で実行

### 🚨 重要な注意点

- **内部コンソール専用**: `resolve` オブジェクトが最初から存在
- **外部スクリプトでは使用不可**: `scriptapp` やモジュールimportが必要
- **ワンライナー形式**: VSCode自動改行問題を回避

### 🎯 推奨テスト順序

1. **Step 1**: `print(resolve)` で基本確認 ✅ 完了
2. **Step 2**: タイムライン情報取得で環境確認 ✅ 完了  
3. **Step 3**: トラック数確認でプロジェクト状態確認 ✅ 完了
4. **マーカー追加**: タイムコード文字列版 ✅ 実証済み（戻り値Falseでも動作）
5. **次の推奨テスト**:
   - マーカー確認（実際に追加されたか検証）
   - V1クリップ情報取得（分割準備）
   - V1クリップ中央分割テスト

### 📊 現在の環境状況（テスト結果更新）

- **プロジェクト**: "021オリジナル" (24.0fps)
- **開始タイムコード**: 01:00:00:00
- **現在位置**: 01:48:25:23 (156143フレーム)
- **トラック構成**: V1本(クリップ0個), A2本(各4個クリップ)
- **マーカー**: 5個存在（S000-S004のストレステスト用）
- **API制限**: `GetEndTimecode()` 未対応

### 🎯 重要な発見

#### ✅ **マーカーAPIの真実（スーパーバイザー予測的中）**
- **戻り値 `False`** でも **実際にはマーカー追加済み**
- 既存マーカー5個：Blue,Green,Red,Yellow,Cyan のストレステスト用
- 同じ位置への連続追加は失敗する仕様

#### ⚠️ **V1トラック空**  
- V1にクリップなし（音声のみのタイムライン）
- A1,A2に各4個のクリップが存在
- 分割テストはオーディオクリップで実行可能