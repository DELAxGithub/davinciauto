#!/usr/bin/env python3
"""
CSV → EDL変換 Python実装
DaVinci Resolve用EDL（Edit Decision List）ファイル生成

Usage:
    python generate_edl.py data/markers.csv
    python generate_edl.py --input data/markers.csv --output output/cuts.edl
"""

import argparse
import csv
import os
import sys
from datetime import datetime
from pathlib import Path

# ローカルモジュール
sys.path.append(str(Path(__file__).parent / "davinci_autocut" / "lib"))
from resolve_utils import validate_timecode_format, tc_to_frames, frames_to_tc


class EDLGenerator:
    """EDL（Edit Decision List）生成クラス"""
    
    def __init__(self, frame_rate=25):
        """
        Args:
            frame_rate (int): フレームレート（デフォルト: 25fps）
        """
        self.frame_rate = frame_rate
        
    def format_timecode(self, timecode_str):
        """タイムコードを標準形式（HH:MM:SS:FF）に変換
        
        Args:
            timecode_str (str): 入力タイムコード文字列
            
        Returns:
            str: 正規化されたタイムコード、失敗時はNone
        """
        if not timecode_str:
            return None
            
        tc_str = str(timecode_str).strip()
        
        # 既に正しい形式かチェック
        if validate_timecode_format(tc_str):
            return tc_str
            
        # HH:MM:SS:FF 形式への変換を試行
        if ':' in tc_str:
            parts = tc_str.split(':')
            if len(parts) == 4:
                try:
                    h, m, s, f = map(int, parts)
                    return f"{h:02d}:{m:02d}:{s:02d}:{f:02d}"
                except ValueError:
                    pass
                    
        print(f"⚠️  無効なタイムコード形式: {tc_str}")
        return None
        
    def add_frames(self, timecode_str, frame_count=1):
        """タイムコードにフレーム数を加算
        
        Args:
            timecode_str (str): ベースタイムコード
            frame_count (int): 加算するフレーム数
            
        Returns:
            str: 加算後のタイムコード
        """
        total_frames = tc_to_frames(timecode_str, self.frame_rate)
        return frames_to_tc(total_frames + frame_count, self.frame_rate)
        
    def load_csv(self, csv_path):
        """CSVファイルを読み込んで編集点データを抽出
        
        Args:
            csv_path (str): CSVファイルパス
            
        Returns:
            list: 編集点データのリスト
        """
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"CSVファイルが見つかりません: {csv_path}")
            
        edit_points = []
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                
                for row_num, row in enumerate(reader, start=2):
                    # カラム名の正規化（大文字小文字、空白を無視）
                    normalized_row = {k.lower().strip(): v for k, v in row.items()}
                    
                    # 必須フィールドの取得
                    start_time = (normalized_row.get('in') or 
                                normalized_row.get('start time') or
                                normalized_row.get('start_time'))
                    end_time = (normalized_row.get('out') or 
                              normalized_row.get('end time') or
                              normalized_row.get('end_time'))
                    label = (normalized_row.get('name') or 
                           normalized_row.get('label') or
                           f"Clip{len(edit_points) + 1}")
                    
                    if not start_time:
                        print(f"⚠️  行{row_num}: Start Timeが空です - スキップ")
                        continue
                        
                    # タイムコード変換
                    formatted_start = self.format_timecode(start_time)
                    if not formatted_start:
                        print(f"⚠️  行{row_num}: 無効なStart Time '{start_time}' - スキップ")
                        continue
                        
                    # End Timeが無い場合は1フレーム追加
                    if end_time:
                        formatted_end = self.format_timecode(end_time)
                        if not formatted_end:
                            print(f"⚠️  行{row_num}: 無効なEnd Time '{end_time}' - 1フレーム追加を使用")
                            formatted_end = self.add_frames(formatted_start, 1)
                    else:
                        formatted_end = self.add_frames(formatted_start, 1)
                    
                    edit_points.append({
                        'start_time': formatted_start,
                        'end_time': formatted_end,
                        'label': str(label).strip()
                    })
                    
        except Exception as e:
            raise Exception(f"CSVファイル読み込みエラー: {e}")
            
        if not edit_points:
            raise Exception("有効な編集点データが見つかりませんでした")
            
        print(f"✅ {len(edit_points)}個の編集点を読み込みました")
        return edit_points
        
    def generate_edl(self, edit_points, title="Auto Generated Edit Points"):
        """編集点データからEDL文字列を生成
        
        Args:
            edit_points (list): 編集点データのリスト
            title (str): EDLタイトル
            
        Returns:
            str: EDL文字列
        """
        edl_lines = []
        
        # EDLヘッダー
        edl_lines.append(f"TITLE: {title}")
        edl_lines.append("FCM: NON-DROP FRAME")
        edl_lines.append("")
        
        for i, point in enumerate(edit_points, start=1):
            # クリップ番号（3桁ゼロパディング）
            clip_number = f"{i:03d}"
            
            # レコードタイムコード計算
            record_in = frames_to_tc((i - 1), self.frame_rate)
            record_out = frames_to_tc(i, self.frame_rate)
            
            # EDLエントリ生成
            # Format: 001  V     C        01:00:15:23 01:00:15:24 00:00:00:00 00:00:00:01
            edl_entry = (f"{clip_number}  V     C        "
                        f"{point['start_time']} {point['end_time']} "
                        f"{record_in} {record_out}")
            
            edl_lines.append(edl_entry)
            edl_lines.append(f"* FROM CLIP NAME: {point['label']}")
            edl_lines.append("")
            
        return "\n".join(edl_lines)
        
    def save_edl(self, edl_content, output_path):
        """EDLファイルを保存
        
        Args:
            edl_content (str): EDL文字列
            output_path (str): 出力ファイルパス
        """
        # ディレクトリが存在しない場合は作成
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        try:
            with open(output_path, 'w', encoding='utf-8') as file:
                file.write(edl_content)
            print(f"✅ EDLファイル生成完了: {output_path}")
            
        except Exception as e:
            raise Exception(f"EDLファイル保存エラー: {e}")


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(
        description="CSV → EDL変換（DaVinci Resolve用）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
    python generate_edl.py data/markers.csv
    python generate_edl.py --input data/markers.csv --output output/cuts.edl --fps 24
    
CSVフォーマット（ヘッダー行必須）:
    In,Out,Name
    01:00:15:23,01:00:15:24,Scene1
    01:07:03:23,,Scene2  # OutがEmpty の場合は1フレーム追加
        """
    )
    
    parser.add_argument('input_csv', nargs='?', 
                       help='入力CSVファイル（未指定時は data/markers.csv）')
    parser.add_argument('--input', '-i', 
                       help='入力CSVファイル')
    parser.add_argument('--output', '-o', 
                       help='出力EDLファイル（未指定時は自動生成）')
    parser.add_argument('--fps', type=int, default=25,
                       help='フレームレート（デフォルト: 25）')
    parser.add_argument('--title', 
                       default="Auto Generated Edit Points",
                       help='EDLタイトル')
    
    args = parser.parse_args()
    
    # 入力ファイル決定
    input_path = args.input or args.input_csv or "davinci_autocut/data/markers.csv"
    
    # 出力ファイル決定
    if args.output:
        output_path = args.output
    else:
        # 自動生成: output/cuts_yyyymmdd_hhmmss.edl
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"output/cuts_{timestamp}.edl"
    
    print(f"🎬 EDL生成開始")
    print(f"   入力: {input_path}")
    print(f"   出力: {output_path}")
    print(f"   FPS: {args.fps}")
    print()
    
    try:
        # EDLジェネレーター初期化
        generator = EDLGenerator(frame_rate=args.fps)
        
        # CSVファイル読み込み
        edit_points = generator.load_csv(input_path)
        
        # EDL生成
        edl_content = generator.generate_edl(edit_points, title=args.title)
        
        # EDLファイル保存
        generator.save_edl(edl_content, output_path)
        
        print()
        print(f"🎯 成功: {len(edit_points)}個の編集点を含むEDLファイルを生成しました")
        print(f"📁 {output_path}")
        print()
        print("次の手順:")
        print("1. DaVinci Resolveを開く")
        print("2. Media Pool → 右クリック → Import Media")
        print("3. 生成されたEDLファイルを選択")
        print("4. 新しいタイムラインが編集点付きで作成されます")
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()