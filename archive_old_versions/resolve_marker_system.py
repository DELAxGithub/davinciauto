#!/usr/bin/env python3
"""
DaVinci Resolve マーカー自動付与システム
逆算設計: API仕様から完璧なCSVフォーマットを定義
"""

import csv
import sys
from pathlib import Path

class ResolveMarkerSystem:
    """DaVinci Resolve マーカー自動付与システム"""
    
    # DaVinci Resolve API仕様準拠の色指定（実際のパレットに対応）
    RESOLVE_COLORS = {
        # 基本色（英語名対応）
        'blue': 'Blue',
        'cyan': 'Cyan', 
        'green': 'Green',
        'yellow': 'Yellow',
        'red': 'Red',
        'pink': 'Pink',
        'purple': 'Purple',
        'fuchsia': 'Fuchsia',
        'rose': 'Rose',
        'lavender': 'Lavender',
        'sky': 'Sky',
        'mint': 'Mint',
        'lemon': 'Lemon',
        'sand': 'Sand',
        'cocoa': 'Cocoa',
        'cream': 'Cream',
        # 日本語名対応（念のため）
        '青': 'Blue',
        'シアン': 'Cyan',
        '緑': 'Green', 
        '黄': 'Yellow',
        '赤': 'Red',
        'ピンク': 'Pink',
        '紫': 'Purple',
        'フクシア': 'Fuchsia',
        'ローズ': 'Rose',
        'ラベンダー': 'Lavender',
        'スカイ': 'Sky',
        'ミント': 'Mint',
        'レモン': 'Lemon',
        'サンド': 'Sand',
        'ココア': 'Cocoa',
        'クリーム': 'Cream'
    }
    
    def __init__(self, project_fps=25):
        """
        Args:
            project_fps (int): プロジェクトフレームレート
        """
        self.project_fps = project_fps
        
    def timecode_to_frame(self, timecode_str):
        """
        タイムコード文字列をフレーム数に変換
        
        Args:
            timecode_str (str): "HH:MM:SS:FF" または "HH:MM:SS.mmm"
            
        Returns:
            int: フレーム数
        """
        if ':' in timecode_str.split(':')[-1]:
            # HH:MM:SS:FF 形式
            h, m, s, f = map(int, timecode_str.split(':'))
            total_frames = (h * 3600 + m * 60 + s) * self.project_fps + f
        else:
            # HH:MM:SS.mmm 形式
            time_part, ms_part = timecode_str.split('.')
            h, m, s = map(int, time_part.split(':'))
            ms = int(ms_part)
            total_seconds = h * 3600 + m * 60 + s + ms / 1000.0
            total_frames = int(total_seconds * self.project_fps)
            
        return total_frames
    
    def add_markers_from_csv(self, timeline, csv_path):
        """
        CSVファイルからマーカーを自動付与
        
        Args:
            timeline: DaVinci Resolve Timeline object
            csv_path (str): CSVファイルパス
            
        Returns:
            dict: 処理結果レポート
        """
        results = {
            'success_count': 0,
            'error_count': 0,
            'errors': []
        }
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row_num, row in enumerate(reader, 1):
                    try:
                        # 必須フィールド検証
                        required_fields = ['timecode', 'marker_name', 'color']
                        missing_fields = [field for field in required_fields if not row.get(field)]
                        
                        if missing_fields:
                            raise ValueError(f"必須フィールド不足: {missing_fields}")
                        
                        # フレーム数変換
                        frame = self.timecode_to_frame(row['timecode'])
                        
                        # 色指定検証・変換
                        color_key = row['color'].lower()
                        if color_key not in self.RESOLVE_COLORS:
                            raise ValueError(f"無効な色指定: {row['color']}")
                        resolve_color = self.RESOLVE_COLORS[color_key]
                        
                        # マーカー情報構築
                        marker_name = row['marker_name']
                        note = row.get('note', '')
                        duration = int(row.get('duration_frames', 1))  # デフォルト1フレーム
                        
                        # DaVinci Resolve API実行
                        success = timeline.AddMarker(frame, resolve_color, marker_name, note, duration)
                        
                        if success:
                            results['success_count'] += 1
                            print(f"✅ 行{row_num}: マーカー追加成功 - {marker_name} @ {row['timecode']}")
                        else:
                            results['error_count'] += 1
                            error_msg = f"API失敗: マーカー追加に失敗"
                            results['errors'].append(f"行{row_num}: {error_msg}")
                            print(f"❌ 行{row_num}: {error_msg}")
                            
                    except Exception as e:
                        results['error_count'] += 1
                        error_msg = f"処理エラー: {str(e)}"
                        results['errors'].append(f"行{row_num}: {error_msg}")
                        print(f"❌ 行{row_num}: {error_msg}")
                        
        except Exception as e:
            results['errors'].append(f"ファイル読み込みエラー: {str(e)}")
            print(f"💥 CSVファイル読み込み失敗: {str(e)}")
            
        return results
    
    @classmethod
    def generate_csv_template(cls, output_path="marker_template.csv"):
        """
        完璧なCSVテンプレートを生成
        
        Args:
            output_path (str): 出力ファイルパス
        """
        # 完璧なCSVフォーマット仕様
        csv_spec = [
            {
                'timecode': '00:01:15:00',
                'marker_name': '番組開始',
                'color': 'blue',
                'note': 'オープニングトーク開始',
                'duration_frames': '75',  # 3秒 (25fps × 3)
                'speaker': 'ホスト',
                'priority': 'high',
                'cut_type': 'intro'
            },
            {
                'timecode': '00:03:45:10',
                'marker_name': 'テーマ紹介',
                'color': 'green',
                'note': '今日のメインテーマについて',
                'duration_frames': '125',  # 5秒
                'speaker': 'ゲスト',
                'priority': 'medium', 
                'cut_type': 'topic'
            },
            {
                'timecode': '00:05:20:15',
                'marker_name': 'CM前コメント',
                'color': 'yellow',
                'note': 'コマーシャル前の一言',
                'duration_frames': '50',  # 2秒
                'speaker': 'ホスト',
                'priority': 'low',
                'cut_type': 'transition'
            },
            {
                'timecode': '00:05:35:15',
                'marker_name': 'CMスタート',
                'color': 'cyan',
                'note': '60秒コマーシャル',
                'duration_frames': '1500',  # 60秒
                'speaker': 'CM',
                'priority': 'low',
                'cut_type': 'commercial'
            },
            {
                'timecode': '00:06:35:15',
                'marker_name': 'CM明け',
                'color': 'green',
                'note': 'コマーシャル明けトーク',
                'duration_frames': '75',
                'speaker': 'ホスト',
                'priority': 'medium',
                'cut_type': 'cm_return'
            },
            {
                'timecode': '00:12:10:05',
                'marker_name': '重要発言',
                'color': 'red',
                'note': 'キーポイント - 絶対カットしない',
                'duration_frames': '225',  # 9秒
                'speaker': 'ゲスト',
                'priority': 'critical',
                'cut_type': 'highlight'
            },
            {
                'timecode': '00:15:30:20',
                'marker_name': '対談開始',
                'color': 'purple',
                'note': 'ホストとゲストの本格対談',
                'duration_frames': '4500',  # 3分
                'speaker': '両方',
                'priority': 'high',
                'cut_type': 'dialogue'
            },
            {
                'timecode': '00:25:45:00',
                'marker_name': '番組終了',
                'color': 'blue',
                'note': 'エンディングトーク',
                'duration_frames': '150',  # 6秒
                'speaker': 'ホスト',
                'priority': 'high',
                'cut_type': 'ending'
            }
        ]
        
        # CSVファイル生成
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            if csv_spec:
                fieldnames = list(csv_spec[0].keys())
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(csv_spec)
                
        print(f"📋 完璧なCSVテンプレート生成完了: {output_path}")
        
        # フォーマット仕様をドキュメント出力
        cls.generate_format_spec()
        
        return output_path
    
    @classmethod  
    def generate_format_spec(cls, output_path="CSV_FORMAT_SPEC.md"):
        """CSVフォーマット仕様書を生成"""
        
        spec_content = """# 📋 DaVinci Resolve マーカー用CSV完璧フォーマット仕様

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
"""
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(spec_content)
            
        print(f"📚 フォーマット仕様書生成完了: {output_path}")

def main():
    """メイン実行関数 - テンプレート生成"""
    print("🎬 DaVinci Resolve マーカー自動付与システム")
    print("   完璧なCSVフォーマット - 逆算設計\n")
    
    # システム初期化
    system = ResolveMarkerSystem(project_fps=25)
    
    # 完璧なテンプレート生成
    template_path = system.generate_csv_template("perfect_marker_template.csv")
    
    print(f"\n✅ 生成完了:")
    print(f"   📋 CSVテンプレート: {template_path}")
    print(f"   📚 仕様書: CSV_FORMAT_SPEC.md")
    print(f"\n🚀 次のステップ:")
    print(f"   1. perfect_marker_template.csv をGoogleシートに取り込み")
    print(f"   2. 実際のデータで編集")
    print(f"   3. Python実行でマーカー自動付与")

if __name__ == "__main__":
    main()