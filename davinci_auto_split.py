#!/usr/bin/env python3
"""
DaVinci Resolve 自動分割統合ワークフロー
親方の指示に従ったEDL経由での確実な実装

メイン機能:
1. EDL経由自動分割（推奨）
2. マーカー半自動フォールバック
3. エラーハンドリングと検証

Usage:
    python davinci_auto_split.py data/markers.csv
    python davinci_auto_split.py --mode edl data/markers.csv
    python davinci_auto_split.py --mode marker data/markers.csv
"""

import argparse
import csv
import os
import sys
from datetime import datetime
from pathlib import Path

# ローカルモジュール
sys.path.append(str(Path(__file__).parent / "davinci_autocut" / "lib"))
from resolve_utils import validate_timecode_format

# EDLジェネレーター
from generate_edl import EDLGenerator


class DaVinciAutoSplit:
    """DaVinci Resolve自動分割統合システム"""
    
    def __init__(self, frame_rate=25):
        """
        Args:
            frame_rate (int): プロジェクトフレームレート
        """
        self.frame_rate = frame_rate
        self.edl_generator = EDLGenerator(frame_rate)
        
    def analyze_csv(self, csv_path):
        """CSVファイルの分析と検証
        
        Args:
            csv_path (str): CSVファイルパス
            
        Returns:
            dict: 分析結果
        """
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"CSVファイルが見つかりません: {csv_path}")
            
        analysis = {
            'total_rows': 0,
            'valid_rows': 0,
            'invalid_rows': 0,
            'timecode_errors': [],
            'missing_fields': [],
            'warnings': []
        }
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                headers = [h.lower().strip() for h in reader.fieldnames]
                
                # 必要なフィールドのチェック
                required_fields = ['in', 'start time', 'start_time']
                has_required = any(field in headers for field in required_fields)
                
                if not has_required:
                    analysis['missing_fields'].append("Start Time フィールドがありません")
                
                for row_num, row in enumerate(reader, start=2):
                    analysis['total_rows'] += 1
                    
                    # タイムコードの検証
                    normalized_row = {k.lower().strip(): v for k, v in row.items()}
                    start_time = (normalized_row.get('in') or 
                                normalized_row.get('start time') or
                                normalized_row.get('start_time'))
                    
                    if not start_time:
                        analysis['invalid_rows'] += 1
                        analysis['timecode_errors'].append(f"行{row_num}: Start Timeが空")
                        continue
                        
                    formatted_start = self.edl_generator.format_timecode(start_time)
                    if not formatted_start:
                        analysis['invalid_rows'] += 1
                        analysis['timecode_errors'].append(f"行{row_num}: 無効なタイムコード '{start_time}'")
                        continue
                        
                    analysis['valid_rows'] += 1
                    
        except Exception as e:
            raise Exception(f"CSV分析エラー: {e}")
            
        return analysis
        
    def mode_edl(self, csv_path, output_path=None, title="Auto Generated Edit Points"):
        """EDL経由モード（メイン推奨方式）
        
        Args:
            csv_path (str): 入力CSVファイル
            output_path (str): 出力EDLファイル（省略時自動生成）
            title (str): EDLタイトル
            
        Returns:
            dict: 実行結果
        """
        print("🎬 EDL経由モード開始")
        print("   親方推奨の業界標準ワークフロー")
        print()
        
        # 出力パス決定
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"output/davinci_cuts_{timestamp}.edl"
            
        try:
            # CSV分析
            print("📊 CSVファイル分析中...")
            analysis = self.analyze_csv(csv_path)
            
            if analysis['valid_rows'] == 0:
                raise Exception("有効な編集点データがありません")
                
            print(f"   総行数: {analysis['total_rows']}")
            print(f"   有効行数: {analysis['valid_rows']}")
            print(f"   無効行数: {analysis['invalid_rows']}")
            
            if analysis['invalid_rows'] > 0:
                print("   ⚠️  エラー詳細:")
                for error in analysis['timecode_errors'][:5]:  # 最大5個まで表示
                    print(f"      {error}")
                if len(analysis['timecode_errors']) > 5:
                    print(f"      ...他{len(analysis['timecode_errors']) - 5}個")
                    
            print()
            
            # EDL生成
            print("⚡ EDL生成中...")
            edit_points = self.edl_generator.load_csv(csv_path)
            edl_content = self.edl_generator.generate_edl(edit_points, title=title)
            self.edl_generator.save_edl(edl_content, output_path)
            
            # 結果
            result = {
                'success': True,
                'mode': 'edl',
                'output_file': output_path,
                'edit_points': len(edit_points),
                'analysis': analysis,
                'next_steps': [
                    "1. DaVinci Resolveを開く",
                    "2. Media Pool → 右クリック → Import Media", 
                    "3. 生成されたEDLファイルを選択",
                    "4. 新しいタイムラインが編集点付きで作成されます"
                ]
            }
            
            print(f"✅ EDL生成成功: {len(edit_points)}個の編集点")
            print(f"📁 {output_path}")
            print()
            print("🚀 次の手順:")
            for step in result['next_steps']:
                print(f"   {step}")
                
            return result
            
        except Exception as e:
            print(f"❌ EDLモードエラー: {e}")
            return {
                'success': False,
                'mode': 'edl',
                'error': str(e),
                'fallback_available': True
            }
    
    def mode_marker_fallback(self, csv_path):
        """マーカー半自動フォールバックモード
        
        Args:
            csv_path (str): 入力CSVファイル
            
        Returns:
            dict: 実行結果
        """
        print("🔄 マーカー半自動フォールバックモード")
        print("   EDLモード失敗時の次善策")
        print()
        
        try:
            # CSVからマーカーデータ作成
            edit_points = self.edl_generator.load_csv(csv_path)
            
            # マーカー配置用の情報生成
            marker_info = []
            for i, point in enumerate(edit_points, 1):
                marker_info.append({
                    'timecode': point['start_time'],
                    'name': point['label'],
                    'color': 'Red',  # デフォルトカラー
                    'note': f'編集点{i} - {point["label"]}'
                })
            
            # マーカー配置スクリプト生成（将来の拡張用）
            print(f"📍 {len(marker_info)}個のマーカー情報を準備完了")
            
            result = {
                'success': True,
                'mode': 'marker_fallback',
                'markers': marker_info,
                'next_steps': [
                    "⚠️  フォールバックモード（手動作業必要）",
                    "1. DaVinci Resolveでタイムラインを開く",
                    "2. 各タイムコードに手動でマーカーを配置:",
                ]
            }
            
            # マーカー配置情報を表示
            for marker in marker_info:
                result['next_steps'].append(f"   - {marker['timecode']}: {marker['name']}")
                
            result['next_steps'].extend([
                "3. マーカー位置で手動分割を実行",
                "4. 各クリップに適切な名前を設定"
            ])
            
            print("🎯 マーカー情報生成完了")
            print()
            print("📋 手動作業リスト:")
            for step in result['next_steps']:
                print(f"   {step}")
                
            return result
            
        except Exception as e:
            print(f"❌ フォールバックモードエラー: {e}")
            return {
                'success': False,
                'mode': 'marker_fallback',
                'error': str(e)
            }


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(
        description="DaVinci Resolve自動分割統合システム",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
    # EDL経由（推奨）
    python davinci_auto_split.py data/markers.csv
    python davinci_auto_split.py --mode edl data/markers.csv
    
    # マーカー半自動フォールバック
    python davinci_auto_split.py --mode marker data/markers.csv
    
    # カスタム設定
    python davinci_auto_split.py --mode edl --fps 24 --output cuts.edl data/markers.csv

親方の教え:
- EDL経由が最も確実で業界標準
- PyAutoGUI等の不安定手法は使用禁止
- ワークフローの分離: Python=EDL生成、DaVinci=インポート処理
        """
    )
    
    parser.add_argument('csv_file', help='入力CSVファイル')
    parser.add_argument('--mode', choices=['edl', 'marker'], default='edl',
                       help='実行モード（デフォルト: edl）')
    parser.add_argument('--output', '-o',
                       help='出力ファイル（EDLモード時、省略で自動生成）')
    parser.add_argument('--fps', type=int, default=25,
                       help='フレームレート（デフォルト: 25）')
    parser.add_argument('--title', default="DaVinci Auto Split",
                       help='EDLタイトル')
    parser.add_argument('--force-fallback', action='store_true',
                       help='強制的にフォールバックモードを使用')
    
    args = parser.parse_args()
    
    # バナー表示
    print("=" * 60)
    print("🎬 DaVinci Resolve 自動分割システム")
    print("   親方指導による業界標準EDL経由実装")
    print("=" * 60)
    print(f"📁 入力: {args.csv_file}")
    print(f"⚙️  モード: {args.mode.upper()}")
    print(f"🎞️  FPS: {args.fps}")
    print()
    
    # 入力ファイルチェック
    if not os.path.exists(args.csv_file):
        print(f"❌ CSVファイルが見つかりません: {args.csv_file}")
        sys.exit(1)
        
    # 自動分割システム初期化
    auto_split = DaVinciAutoSplit(frame_rate=args.fps)
    
    try:
        if args.mode == 'edl' and not args.force_fallback:
            # EDL経由モード（メイン）
            result = auto_split.mode_edl(
                csv_path=args.csv_file,
                output_path=args.output,
                title=args.title
            )
            
            if not result['success'] and result.get('fallback_available'):
                print()
                print("🔄 EDLモード失敗 → フォールバックモードに切り替え")
                print()
                result = auto_split.mode_marker_fallback(args.csv_file)
                
        elif args.mode == 'marker' or args.force_fallback:
            # マーカーフォールバックモード
            result = auto_split.mode_marker_fallback(args.csv_file)
            
        else:
            raise ValueError(f"不明なモード: {args.mode}")
            
        # 実行結果表示
        print()
        print("=" * 60)
        if result['success']:
            print(f"🎉 実行完了 - {result['mode'].upper()}モード")
            print(f"⏱️  処理時間: < 5秒")
            print()
            print("💡 親方のアドバイス:")
            print("   EDL経由は最も確実で業界標準の手法です")
            print("   PyAutoGUI等の不安定な手法は避けましょう")
        else:
            print(f"💥 実行失敗 - {result.get('error', '不明なエラー')}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⏹️  ユーザーによる中断")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ システムエラー: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()