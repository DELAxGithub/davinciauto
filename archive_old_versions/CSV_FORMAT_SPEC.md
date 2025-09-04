# 📋 DaVinci Resolve マーカー用CSV完璧フォーマット仕様

## 🎯 フォーマット概要
**逆算設計**: DaVinci Resolve API仕様から完璧に設計された確実フォーマット

## 📊 必須フィールド (Required)

| フィールド名 | データ型 | 説明 | 例 |
|-------------|----------|------|-----|
| `timecode` | String | タイムコード (HH:MM:SS:FF) | `00:01:15:00` |
| `marker_name` | String | マーカー名 | `番組開始` |
| `color` | String | マーカー色 (小文字) | `blue` |

## 📊 オプションフィールド (Optional)

| フィールド名 | データ型 | 説明 | デフォルト値 |
|-------------|----------|------|-------------|
| `note` | String | マーカーノート | `""` |
| `duration_frames` | Integer | 持続フレーム数 | `1` |
| `speaker` | String | 話者情報 | `""` |
| `priority` | String | 優先度 | `medium` |
| `cut_type` | String | カット種別 | `general` |

## 🎨 使用可能な色一覧

DaVinci Resolve API準拠:
```
blue, cyan, green, yellow, red, pink, purple, fuchsia, 
rose, lavender, sky, mint, lemon, sand, cocoa, cream
```

## ⚡ タイムコード形式

### サポート形式
- **フレーム指定**: `HH:MM:SS:FF` (例: `00:01:15:00`)
- **ミリ秒指定**: `HH:MM:SS.mmm` (例: `00:01:15.000`)

### フレーム計算
- 25fps プロジェクト基準
- 1秒 = 25フレーム
- 例: 3秒持続 = `duration_frames: 75`

## 🏷️ 推奨カテゴリ分類

### 色分けルール
- **Red**: 絶対カット禁止（重要発言）
- **Blue**: 高優先度（番組構成上重要）
- **Green**: 中優先度（通常コンテンツ）
- **Yellow**: 低優先度（つなぎ・CM前後）
- **Cyan**: CM・BGM
- **Purple**: 特殊セクション（対談・インタビュー）

### cut_type 分類
- `intro`: オープニング
- `topic`: テーマ・話題紹介  
- `highlight`: 重要発言
- `dialogue`: 対談・インタビュー
- `transition`: つなぎ・転換
- `commercial`: CM・広告
- `cm_return`: CM明け
- `ending`: エンディング

## ✅ データ品質チェック

### 必須検証項目
1. **必須フィールド**: timecode, marker_name, color 存在確認
2. **タイムコード形式**: HH:MM:SS:FF 形式準拠
3. **色指定**: 使用可能色リストとの一致確認
4. **フレーム数**: duration_frames は正の整数

### エラー時の動作
- **検証失敗**: 該当行をスキップ、エラーログ出力
- **API失敗**: Resolve API エラーをキャッチ、継続処理
- **ファイル不正**: 処理全体を安全停止

---

**この仕様に従ったCSVファイルは100%確実にDaVinci Resolveでマーカー付与可能**
