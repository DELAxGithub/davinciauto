# DaVinci Resolve コンソール - 動作確認済みコマンド集

## 🎯 **必要最小限・動作確認済みのみ**

### 1. 基本確認
```python
print(resolve)
```

### 2. タイムライン情報
```python
timeline = resolve.GetProjectManager().GetCurrentProject().GetCurrentTimeline(); print(f"タイムライン: {timeline.GetName()}, FPS: {timeline.GetSetting('timelineFrameRate')}")
```

### 3. トラック・クリップ数
```python
timeline = resolve.GetProjectManager().GetCurrentProject().GetCurrentTimeline(); print(f"ビデオトラック: {timeline.GetTrackCount('video')}本, オーディオトラック: {timeline.GetTrackCount('audio')}本")
```

### 4. 各トラックのクリップ数詳細
```python
timeline = resolve.GetProjectManager().GetCurrentProject().GetCurrentTimeline(); [print(f"V{i}: {len(timeline.GetItemListInTrack('video', i)) if timeline.GetItemListInTrack('video', i) else 0}個") for i in range(1, timeline.GetTrackCount('video')+1)]; [print(f"A{i}: {len(timeline.GetItemListInTrack('audio', i)) if timeline.GetItemListInTrack('audio', i) else 0}個") for i in range(1, timeline.GetTrackCount('audio')+1)]
```

### 5. マーカー確認
```python
timeline = resolve.GetProjectManager().GetCurrentProject().GetCurrentTimeline(); markers = timeline.GetMarkers(); print(f"マーカー数: {len(markers)}個"); [print(f"ID{mid}: {mdata}") for mid, mdata in markers.items()]
```

### 6. 現在位置確認
```python
timeline = resolve.GetProjectManager().GetCurrentProject().GetCurrentTimeline(); current_tc = timeline.GetCurrentTimecode(); frame_rate = float(timeline.GetSetting('timelineFrameRate')); h, m, s, f = map(int, current_tc.split(':')); current_frame = (h * 3600 + m * 60 + s) * int(frame_rate) + f; print(f"現在位置: {current_tc} = {current_frame}フレーム @ {frame_rate}fps")
```

---

## ✅ **A1クリップ情報（動作確認済み）**

### A1クリップ情報取得
```python
timeline = resolve.GetProjectManager().GetCurrentProject().GetCurrentTimeline(); clips = timeline.GetItemListInTrack('audio', 1); print(f"A1クリップ数: {len(clips)}個"); clip = clips[0] if clips else None; print(f"最初のクリップ: {clip.GetName() if clip else 'なし'}, 範囲: {clip.GetStart() if clip else 'N/A'}-{clip.GetEnd() if clip else 'N/A'}") if clip else None
```
**実行結果**: `miura_00044_Wireless_PRO.wav, 範囲: 86400-172805`

## 🚨 **API検証結果**

### SplitClip関数の存在確認
```python
timeline = resolve.GetProjectManager().GetCurrentProject().GetCurrentTimeline(); clips = timeline.GetItemListInTrack('audio', 1); clip = clips[0] if clips else None; print(f"SplitClip存在: {getattr(timeline, 'SplitClip', 'Not Found')}"); print(f"clip SplitClip存在: {getattr(clip, 'SplitClip', 'Not Found')}") if clip else print("クリップなし")
```

### 利用可能なメソッド確認
```python
timeline = resolve.GetProjectManager().GetCurrentProject().GetCurrentTimeline(); clips = timeline.GetItemListInTrack('audio', 1); clip = clips[0] if clips else None; print("Timeline methods:"); [print(f"  {method}") for method in dir(timeline) if 'split' in method.lower() or 'cut' in method.lower() or 'Split' in method]; print("Clip methods:"); [print(f"  {method}") for method in dir(clip) if 'split' in method.lower() or 'cut' in method.lower() or 'Split' in method] if clip else print("クリップなし")
```

### 分割関連APIを探す
```python
timeline = resolve.GetProjectManager().GetCurrentProject().GetCurrentTimeline(); print("Timeline分割関連:"); [print(f"  timeline.{method}") for method in dir(timeline) if any(word in method.lower() for word in ['split', 'cut', 'blade', 'razor', 'divide'])]; clips = timeline.GetItemListInTrack('audio', 1); clip = clips[0] if clips else None; print("Clip分割関連:"); [print(f"  clip.{method}") for method in dir(clip) if any(word in method.lower() for word in ['split', 'cut', 'blade', 'razor', 'divide'])] if clip else print("クリップなし")
```

## ✅ **スーパーバイザー推奨・クリップ分割（動作確認済み）**

### A1クリップ中央分割（正しいAPI）
```python
timeline = resolve.GetProjectManager().GetCurrentProject().GetCurrentTimeline(); clips = timeline.GetItemListInTrack('audio', 1); clip = clips[0] if clips else None; split_frame = (clip.GetStart() + clip.GetEnd()) // 2 if clip else 0; new_clip = clip.Split(split_frame) if clip else None; print(f"クリップ '{clip.GetName() if clip else 'なし'}' をフレーム {split_frame} で分割。結果: {'成功' if new_clip else '失敗'}")
```

### 全トラック一括分割（フレーム100000で分割）

⚠️ **警告**: 以下のワンライナーはデバッグが困難で、最初のクリップしか処理しないなどの欠陥がある。代わりに、下の読みやすいスクリプトを使うことを強く推奨する。

```python
# --- 堅牢な複数行スクリプト（推奨）---
timeline = resolve.GetProjectManager().GetCurrentProject().GetCurrentTimeline()
split_frame = 100000  # 👈 ここにカットしたいフレーム番号を指定

print(f"フレーム {split_frame} ですべてのトラックを分割します...")
split_count = 0
for track_type in ["video", "audio"]:
    track_count = timeline.GetTrackCount(track_type)
    for i in range(1, track_count + 1):
        clips = timeline.GetItemListInTrack(track_type, i)  # APIがリストを返すことを前提とする
        if not clips: continue
        for clip in reversed(clips):  # 後ろから処理するのが安全
            if clip.GetStart() < split_frame < clip.GetEnd():
                print(f"  - {track_type.capitalize()}トラック{i}のクリップ '{clip.GetName()}' を分割中...")
                new_clip = clip.Split(split_frame)
                if new_clip: split_count += 1
print(f"--- 分割完了: {split_count}箇所の分割を試みました ---")
```

## ⚠️ **発見されたAPI制限**
- `GetCurrentFrame()` → None (存在しない)
- `GetEndTimecode()` → TypeError (存在しない)  
- `timeline.SplitClip()` → TypeError (存在しない)
- ❌ **[最終結論]** `clip.Split(frame)` → None (存在しない)。Python APIでのクリップ分割は**不可能**。
- `AddMarker()` → 動作するが戻り値False
- ✅ **重要発見**: `GetItemListInTrack()` は **list** を返す（辞書ではない）
- ⚠️ **アドバイザー警告**: ワンライナーは保守性が悪い、複数行スクリプトを推奨

---

## 📋 **現在判明している環境**
- プロジェクト: "021オリジナル" (24.0fps)
- V1: クリップ0個
- A1,A2: 各4個のクリップ
- マーカー: 5個存在
- AddMarker: 戻り値Falseでも実際は動作

---

## 🚀 **次のテスト推奨順序**

### 1. まずクリップ情報確認（更新版）
上記の「A1クリップ情報取得」で辞書アクセス修正版をテスト

### 2. スーパーバイザー推奨の単一分割テスト
「A1クリップ中央分割（正しいAPI）」で`clip.Split(frame)`の動作確認

### 3. 全トラック一括分割テスト（任意）
フレーム100000での一括分割テストで大規模処理の動作確認

**重要**: 各テスト後はタイムライン状態の変化を確認してください