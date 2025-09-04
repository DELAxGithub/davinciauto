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
from typing import List, Dict, Optional, Any

# ローカルモジュール
sys.path.append(str(Path(__file__).parent / "davinci_autocut" / "lib"))
from resolve_utils import validate_timecode_format, tc_to_frames, frames_to_tc

# 新しい検証モジュール
from edl_validator import EDLValidator, EditPoint, TCFormat, ValidationLevel


class EDLGenerator:
    """EDL（Edit Decision List）生成クラス（拡張版）"""
    
    def __init__(self, frame_rate=25, enable_validation=True):
        """
        Args:
            frame_rate (int): フレームレート（デフォルト: 25fps）
            enable_validation (bool): 検証機能有効化（デフォルト: True）
        """
        self.frame_rate = frame_rate
        self.enable_validation = enable_validation
        self.validator = EDLValidator(default_fps=frame_rate) if enable_validation else None
        self.validation_summary = None
        
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
        
    def load_csv(self, csv_path) -> List[EditPoint]:
        """CSVファイルを読み込んで編集点データを抽出（拡張版）
        
        Args:
            csv_path (str): CSVファイルパス
            
        Returns:
            List[EditPoint]: 編集点データのリスト
        """
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"CSVファイルが見つかりません: {csv_path}")
            
        edit_points = []
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                
                for row_num, row in enumerate(reader, start=2):
                    # カラム名の正規化（大文字小文字、空白を無視）
                    normalized_row = {k.lower().strip().replace(' ', '_'): v for k, v in row.items()}
                    
                    # 基本フィールド取得
                    start_time = (normalized_row.get('in') or 
                                normalized_row.get('start_time') or
                                normalized_row.get('src_tc_in'))
                    end_time = (normalized_row.get('out') or 
                              normalized_row.get('end_time') or
                              normalized_row.get('src_tc_out'))
                    label = (normalized_row.get('name') or 
                           normalized_row.get('label') or
                           normalized_row.get('clip_name') or
                           f"Clip{len(edit_points) + 1}")
                    
                    # 拡張フィールド取得
                    reel = (normalized_row.get('reel') or 
                          normalized_row.get('tape') or 
                          normalized_row.get('clip_name') or
                          f"REEL{len(edit_points) + 1:03d}")
                    
                    proj_fps = normalized_row.get('proj_fps') or normalized_row.get('fps') or self.frame_rate
                    tc_format_str = normalized_row.get('tc_format', 'NDF')
                    tc_format = TCFormat.DROP_FRAME if tc_format_str.upper() == 'DF' else TCFormat.NON_DROP_FRAME
                    
                    # EditPointオブジェクト作成
                    edit_point = EditPoint(
                        row_number=row_num,
                        reel=str(reel).strip(),
                        clip_name=str(label).strip(),
                        src_tc_in=str(start_time).strip() if start_time else '',
                        src_tc_out=str(end_time).strip() if end_time else '',
                        rec_tc_in=normalized_row.get('rec_tc_in'),
                        proj_fps=self.validator.validate_fps(proj_fps, row_num) if self.validator else float(proj_fps or self.frame_rate),
                        tc_format=tc_format,
                        uid=normalized_row.get('uid') or f"ep{row_num:03d}",
                        
                        # マーカー情報（Phase 2用）
                        marker_name=normalized_row.get('marker_name'),
                        marker_color=normalized_row.get('marker_color'),
                        marker_note=normalized_row.get('marker_note'),
                        marker_duration_frames=int(normalized_row.get('marker_duration_frames', 0)) or None
                    )
                    
                    # 基本検証（検証モードでない場合も実行）
                    if not edit_point.src_tc_in:
                        print(f"⚠️  行{row_num}: Start Timeが空です - スキップ")
                        continue
                        
                    # タイムコード正規化
                    if self.validator:
                        edit_point.src_tc_in = self.validator.validate_timecode(
                            edit_point.src_tc_in, edit_point.proj_fps, row_num, 'src_tc_in'
                        )
                        if edit_point.src_tc_out:
                            edit_point.src_tc_out = self.validator.validate_timecode(
                                edit_point.src_tc_out, edit_point.proj_fps, row_num, 'src_tc_out'
                            )
                    else:
                        edit_point.src_tc_in = self.format_timecode(edit_point.src_tc_in)
                        if edit_point.src_tc_out:
                            edit_point.src_tc_out = self.format_timecode(edit_point.src_tc_out)
                    
                    # タイムコードが無効な場合はスキップ
                    if not edit_point.src_tc_in:
                        print(f"⚠️  行{row_num}: 無効なStart Time - スキップ")
                        continue
                        
                    # End Timeが無い場合は1フレーム追加
                    if not edit_point.src_tc_out:
                        edit_point.src_tc_out = self.add_frames(edit_point.src_tc_in, 1)
                        
                    edit_points.append(edit_point)
                    
        except Exception as e:
            raise Exception(f"CSVファイル読み込みエラー: {e}")
            
        if not edit_points:
            raise Exception("有効な編集点データが見つかりませんでした")
            
        # 検証実行
        if self.validator and self.enable_validation:
            print("🔍 プリフライト検証実行中...")
            self.validation_summary = self.validator.run_preflight_validation(edit_points)
            
            # 検証結果表示
            if not self.validation_summary['can_proceed']:
                print("\n" + self.validator.generate_validation_report())
                raise Exception(f"クリティカル問題により処理停止: {self.validation_summary['issues']['critical']}件")
            elif self.validation_summary['issues']['warning'] > 0:
                print(f"\n⚠️  {self.validation_summary['issues']['warning']}個の警告がありますが処理を続行します")
                if self.validation_summary['issues']['warning'] <= 5:  # 5個以下なら詳細表示
                    print(self.validator.generate_validation_report())
            
        print(f"✅ {len(edit_points)}個の編集点を読み込み完了")
        return edit_points
        
    def generate_edl(self, edit_points: List[EditPoint], title="Auto Generated Edit Points") -> str:
        """編集点データからEDL文字列を生成（拡張版）
        
        Args:
            edit_points (List[EditPoint]): 編集点データのリスト
            title (str): EDLタイトル
            
        Returns:
            str: EDL文字列
        """
        edl_lines = []
        
        # EDLヘッダー（DF/NDF対応）
        # 全体のフレームフォーマットを決定（最初のポイントから）
        fc_mode = "DROP FRAME" if edit_points and edit_points[0].tc_format == TCFormat.DROP_FRAME else "NON-DROP FRAME"
        edl_lines.append(f"TITLE: {title}")
        edl_lines.append(f"FCM: {fc_mode}")
        edl_lines.append("")
        
        for i, point in enumerate(edit_points, start=1):
            # クリップ番号（3桁ゼロパディング）
            clip_number = f"{i:03d}"
            
            # レコードタイムコード計算（カスタム指定があれば優先）
            if point.rec_tc_in:
                record_in = point.rec_tc_in
                # record_outを計算（デュレーション基準）
                if point.duration_frames:
                    rec_in_frames = tc_to_frames(record_in, point.proj_fps)
                    record_out = frames_to_tc(rec_in_frames + point.duration_frames, point.proj_fps)
                else:
                    record_out = frames_to_tc(tc_to_frames(record_in, point.proj_fps) + 1, point.proj_fps)
            else:
                # 連続配置（デフォルト）
                record_in = frames_to_tc((i - 1), self.frame_rate)
                record_out = frames_to_tc(i, self.frame_rate)
            
            # EDLエントリ生成（Reel名対応）
            # Format: 001  REEL001  V     C        01:00:15:23 01:00:15:24 00:00:00:00 00:00:00:01
            reel_name = point.reel[:8] if len(point.reel) > 8 else point.reel  # EDL制限対応
            
            edl_entry = (f"{clip_number}  {reel_name:<8} V     C        "
                        f"{point.src_tc_in} {point.src_tc_out} "
                        f"{record_in} {record_out}")
            
            edl_lines.append(edl_entry)
            edl_lines.append(f"* FROM CLIP NAME: {point.clip_name}")
            
            # 追加情報（コメントとして）
            if point.marker_name:
                edl_lines.append(f"* MARKER: {point.marker_name}")
            if point.uid:
                edl_lines.append(f"* UID: {point.uid}")
                
            edl_lines.append("")
            
        return "\n".join(edl_lines)
        
    def save_edl(self, edl_content: str, output_path: str) -> Dict[str, Any]:
        """EDLファイルを保存（拡張版）
        
        Args:
            edl_content (str): EDL文字列
            output_path (str): 出力ファイルパス
            
        Returns:
            Dict[str, Any]: 保存結果情報
        """
        # ディレクトリが存在しない場合は作成
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        try:
            with open(output_path, 'w', encoding='utf-8') as file:
                file.write(edl_content)
                
            # ファイル情報取得
            file_size = os.path.getsize(output_path)
            line_count = edl_content.count('\n') + 1
            
            result = {
                'file_path': output_path,
                'file_size': file_size,
                'line_count': line_count,
                'edl_entries': edl_content.count('* FROM CLIP NAME:'),
                'validation_summary': self.validation_summary
            }
            
            print(f"✅ EDLファイル生成完了: {output_path} ({file_size} bytes, {result['edl_entries']} entries)")
            
            return result
            
        except Exception as e:
            raise Exception(f"EDLファイル保存エラー: {e}")


def main():
    """メイン処理（拡張版）"""
    parser = argparse.ArgumentParser(
        description="CSV → EDL変換（DaVinci Resolve用）- 業務レベル検証付き",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
    python generate_edl.py data/markers.csv
    python generate_edl.py --input data/markers.csv --output output/cuts.edl --fps 24
    python generate_edl.py --no-validation data/markers.csv  # 検証無効化
    
CSVフォーマット（拡張版）:
    必須列: In, Out(optional), Name/Reel
    推奨列: reel, proj_fps, tc_format, uid
    
    例:
    In,Out,Name,Reel,proj_fps,tc_format
    01:00:15:23,01:00:15:24,Scene1,TAPE001,25,NDF
    01:07:03:23,,Scene2,TAPE001,25,NDF  # OutがEmptyの場合は1フレーム追加
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
    parser.add_argument('--no-validation', action='store_true',
                       help='データ検証を無効化（高速処理）')
    parser.add_argument('--validation-report', 
                       help='検証レポート出力先（JSONファイル）')
    
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
        # EDLジェネレーター初期化（検証機能付き）
        generator = EDLGenerator(frame_rate=args.fps, enable_validation=not args.no_validation)
        
        print(f"🔧 設定: FPS={args.fps}, 検証={'有効' if not args.no_validation else '無効'}")
        
        # CSVファイル読み込み（拡張検証付き）
        edit_points = generator.load_csv(input_path)
        
        # EDL生成
        edl_content = generator.generate_edl(edit_points, title=args.title)
        
        # EDLファイル保存
        save_result = generator.save_edl(edl_content, output_path)
        
        # 検証レポート保存（必要に応じて）
        if args.validation_report and generator.validation_summary:
            import json
            with open(args.validation_report, 'w', encoding='utf-8') as f:
                json.dump({
                    'validation_summary': generator.validation_summary,
                    'issues': [{
                        'level': issue.level.value,
                        'category': issue.category,
                        'row_number': issue.row_number,
                        'field': issue.field,
                        'message': issue.message,
                        'current_value': str(issue.current_value) if issue.current_value else None,
                        'suggested_fix': issue.suggested_fix
                    } for issue in generator.validator.issues] if generator.validator else []
                }, f, ensure_ascii=False, indent=2)
            print(f"📊 検証レポート保存: {args.validation_report}")
        
        print()
        print(f"🎯 成功: {len(edit_points)}個の編集点を含むEDLファイルを生成しました")
        print(f"📁 {output_path} ({save_result['file_size']} bytes)")
        
        if generator.validation_summary:
            print(f"📊 検証結果: {generator.validation_summary['recommendation']}")
            if generator.validation_summary['issues']['warning'] > 0:
                print(f"   警告: {generator.validation_summary['issues']['warning']}件")
        
        print()
        print("🚀 次の手順:")
        print("1. DaVinci Resolveを開く")
        print("2. Media Pool → 右クリック → Import Media")
        print("3. 生成されたEDLファイルを選択")
        print("4. 新しいタイムラインが編集点付きで作成されます")
        print("5. Reel名とClip名が正しく設定されていることを確認")
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        
        # 検証エラーの場合は詳細レポート表示
        if generator and generator.validator and generator.validator.issues:
            print("\n📋 検証エラー詳細:")
            print(generator.validator.generate_validation_report())
            
        sys.exit(1)


if __name__ == "__main__":
    main()