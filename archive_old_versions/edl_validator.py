#!/usr/bin/env python3
"""
EDL生成用データ検証モジュール
業務レベルの信頼性を実現するための厳密な検証システム

エンジニア提案に基づく実装:
- タイムコード整合（FPS/DF-NDF対応）
- In/Out妥当性チェック
- 重複・交差検出
- Reel/Tape名管理
"""

import re
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional, Any
from enum import Enum
import sys
from pathlib import Path

# ローカルモジュール
sys.path.append(str(Path(__file__).parent / "davinci_autocut" / "lib"))
from resolve_utils import validate_timecode_format, tc_to_frames, frames_to_tc


class ValidationLevel(Enum):
    """検証レベル"""
    CRITICAL = "critical"  # 処理停止レベル
    WARNING = "warning"    # 要確認レベル
    INFO = "info"         # 情報レベル


class TCFormat(Enum):
    """タイムコードフォーマット"""
    NON_DROP_FRAME = "NDF"
    DROP_FRAME = "DF"


@dataclass
class ValidationIssue:
    """検証問題"""
    level: ValidationLevel
    category: str
    row_number: int
    field: str
    message: str
    current_value: Any = None
    suggested_fix: str = None


@dataclass
class EditPoint:
    """編集点データ（拡張版）"""
    row_number: int
    reel: str
    clip_name: str
    src_tc_in: str
    src_tc_out: str
    rec_tc_in: Optional[str] = None
    proj_fps: float = 25.0
    tc_format: TCFormat = TCFormat.NON_DROP_FRAME
    uid: Optional[str] = None
    
    # メタデータ（Phase 2で使用）
    marker_name: Optional[str] = None
    marker_color: Optional[str] = None
    marker_note: Optional[str] = None
    marker_duration_frames: Optional[int] = None
    
    # 内部計算用
    src_in_frames: Optional[int] = None
    src_out_frames: Optional[int] = None
    duration_frames: Optional[int] = None


class EDLValidator:
    """EDL生成用データ検証クラス"""
    
    # サポートするフレームレート
    SUPPORTED_FPS = [23.976, 24, 25, 29.97, 30, 50, 59.94, 60]
    
    # タイムコード正規表現（厳密版）
    TC_PATTERN = re.compile(r'^(\d{2}):(\d{2}):(\d{2}):(\d{2})$')
    
    def __init__(self, default_fps=25.0, tc_format=TCFormat.NON_DROP_FRAME):
        """
        Args:
            default_fps (float): デフォルトフレームレート
            tc_format (TCFormat): タイムコードフォーマット
        """
        self.default_fps = default_fps
        self.default_tc_format = tc_format
        self.issues: List[ValidationIssue] = []
        
    def clear_issues(self):
        """検証結果をクリア"""
        self.issues.clear()
        
    def add_issue(self, level: ValidationLevel, category: str, row_number: int, 
                  field: str, message: str, current_value=None, suggested_fix=None):
        """検証問題を追加"""
        issue = ValidationIssue(
            level=level,
            category=category,
            row_number=row_number,
            field=field,
            message=message,
            current_value=current_value,
            suggested_fix=suggested_fix
        )
        self.issues.append(issue)
        
    def validate_timecode(self, tc_string: str, fps: float, row_number: int, field: str) -> Optional[str]:
        """厳密なタイムコード検証
        
        Args:
            tc_string (str): タイムコード文字列
            fps (float): フレームレート
            row_number (int): 行番号
            field (str): フィールド名
            
        Returns:
            Optional[str]: 正規化されたタイムコード、エラー時はNone
        """
        if not tc_string:
            self.add_issue(
                ValidationLevel.CRITICAL, "timecode", row_number, field,
                "タイムコードが空です", tc_string, "有効なタイムコード（HH:MM:SS:FF）を入力"
            )
            return None
            
        tc_str = str(tc_string).strip()
        
        # 正規表現チェック
        match = self.TC_PATTERN.match(tc_str)
        if not match:
            self.add_issue(
                ValidationLevel.CRITICAL, "timecode", row_number, field,
                f"タイムコード形式が無効です: {tc_str}", tc_str, 
                "HH:MM:SS:FF形式（例: 01:23:45:12）で入力"
            )
            return None
            
        # 各部分の値検証
        hours, minutes, seconds, frames = map(int, match.groups())
        
        # 時間範囲チェック
        if hours > 23:
            self.add_issue(
                ValidationLevel.CRITICAL, "timecode", row_number, field,
                f"時間が無効です（0-23）: {hours}", tc_str, f"00-23の範囲で入力"
            )
            return None
            
        if minutes > 59 or seconds > 59:
            self.add_issue(
                ValidationLevel.CRITICAL, "timecode", row_number, field,
                f"分・秒が無効です（0-59）: {minutes}:{seconds}", tc_str, "00-59の範囲で入力"
            )
            return None
            
        # フレーム数チェック（フレームレート依存）
        max_frames = int(fps) - 1
        if frames > max_frames:
            self.add_issue(
                ValidationLevel.CRITICAL, "timecode", row_number, field,
                f"フレーム数が無効です（0-{max_frames} for {fps}fps）: {frames}", 
                tc_str, f"00-{max_frames:02d}の範囲で入力"
            )
            return None
            
        # ドロップフレーム対応チェック（29.97fps時）
        if abs(fps - 29.97) < 0.01:  # 29.97fps
            # ドロップフレームの禁止フレーム（00:XX:00:00-01, 00:XX:01:00-01は除く）
            if frames < 2 and seconds == 0 and minutes % 10 != 0:
                self.add_issue(
                    ValidationLevel.WARNING, "timecode", row_number, field,
                    f"ドロップフレームで存在しないフレーム: {tc_str}", tc_str,
                    "ドロップフレーム規則に従ったフレーム番号を使用"
                )
                
        return tc_str
        
    def validate_fps(self, fps_value: Any, row_number: int) -> float:
        """フレームレート検証
        
        Args:
            fps_value: フレームレート値
            row_number (int): 行番号
            
        Returns:
            float: 検証済みフレームレート
        """
        if not fps_value:
            self.add_issue(
                ValidationLevel.WARNING, "fps", row_number, "fps",
                "フレームレートが未設定", fps_value, f"デフォルト{self.default_fps}を使用"
            )
            return self.default_fps
            
        try:
            fps = float(fps_value)
        except (ValueError, TypeError):
            self.add_issue(
                ValidationLevel.CRITICAL, "fps", row_number, "fps",
                f"フレームレートが数値ではありません: {fps_value}", fps_value,
                f"数値で入力（例: 25, 29.97）"
            )
            return self.default_fps
            
        # サポートされるフレームレートチェック
        fps_matched = False
        for supported_fps in self.SUPPORTED_FPS:
            if abs(fps - supported_fps) < 0.01:
                fps_matched = True
                break
                
        if not fps_matched:
            self.add_issue(
                ValidationLevel.WARNING, "fps", row_number, "fps",
                f"一般的でないフレームレート: {fps}", fps,
                f"推奨: {', '.join(map(str, self.SUPPORTED_FPS))}"
            )
            
        return fps
        
    def validate_in_out_relationship(self, edit_point: EditPoint) -> bool:
        """In/Out関係の妥当性検証
        
        Args:
            edit_point (EditPoint): 編集点データ
            
        Returns:
            bool: 妥当性（True=有効）
        """
        if not edit_point.src_in_frames or not edit_point.src_out_frames:
            return False
            
        # In < Out チェック
        if edit_point.src_in_frames >= edit_point.src_out_frames:
            self.add_issue(
                ValidationLevel.CRITICAL, "timing", edit_point.row_number, "src_tc_out",
                f"OutがIn以前またはInと同じです: In={edit_point.src_tc_in}, Out={edit_point.src_tc_out}",
                edit_point.src_tc_out, "OutをInより後のタイムコードに設定"
            )
            return False
            
        # 最小デュレーションチェック（1フレーム以上）
        duration = edit_point.src_out_frames - edit_point.src_in_frames
        if duration < 1:
            self.add_issue(
                ValidationLevel.WARNING, "timing", edit_point.row_number, "duration",
                f"デュレーションが短すぎます: {duration}フレーム", duration,
                "最低1フレーム以上のデュレーションを設定"
            )
            return False
            
        # 異常に長いデュレーションチェック（24時間以上）
        max_frames = int(edit_point.proj_fps * 24 * 3600)  # 24時間
        if duration > max_frames:
            self.add_issue(
                ValidationLevel.WARNING, "timing", edit_point.row_number, "duration",
                f"デュレーションが異常に長いです: {duration}フレーム ({duration/edit_point.proj_fps/3600:.1f}時間)",
                duration, "デュレーションを確認"
            )
            
        edit_point.duration_frames = duration
        return True
        
    def detect_overlaps_and_duplicates(self, edit_points: List[EditPoint]) -> List[Tuple[int, int]]:
        """重複・交差検出
        
        Args:
            edit_points (List[EditPoint]): 編集点リスト
            
        Returns:
            List[Tuple[int, int]]: 問題のある組み合わせ（行番号のペア）
        """
        problems = []
        
        # Reel毎にグループ化
        reel_groups = {}
        for ep in edit_points:
            if ep.reel not in reel_groups:
                reel_groups[ep.reel] = []
            reel_groups[ep.reel].append(ep)
            
        # 各Reel内で重複・交差チェック
        for reel, points in reel_groups.items():
            points.sort(key=lambda p: p.src_in_frames or 0)
            
            for i, point_a in enumerate(points):
                if not point_a.src_in_frames or not point_a.src_out_frames:
                    continue
                    
                for j, point_b in enumerate(points[i+1:], i+1):
                    if not point_b.src_in_frames or not point_b.src_out_frames:
                        continue
                        
                    # 重複チェック（完全一致）
                    if (point_a.src_in_frames == point_b.src_in_frames and 
                        point_a.src_out_frames == point_b.src_out_frames):
                        self.add_issue(
                            ValidationLevel.CRITICAL, "duplicate", point_b.row_number, "range",
                            f"Reel '{reel}' で完全重複: 行{point_a.row_number}と同一範囲",
                            f"{point_b.src_tc_in}-{point_b.src_tc_out}",
                            "重複する範囲を削除または修正"
                        )
                        problems.append((point_a.row_number, point_b.row_number))
                        
                    # 交差チェック
                    elif (point_a.src_in_frames < point_b.src_out_frames and 
                          point_b.src_in_frames < point_a.src_out_frames):
                        overlap_start = max(point_a.src_in_frames, point_b.src_in_frames)
                        overlap_end = min(point_a.src_out_frames, point_b.src_out_frames)
                        overlap_duration = overlap_end - overlap_start
                        
                        self.add_issue(
                            ValidationLevel.WARNING, "overlap", point_b.row_number, "range",
                            f"Reel '{reel}' で交差: 行{point_a.row_number}と{overlap_duration}フレーム重複",
                            f"{point_b.src_tc_in}-{point_b.src_tc_out}",
                            "重複部分を調整または意図的な場合は確認済みとしてマーク"
                        )
                        problems.append((point_a.row_number, point_b.row_number))
                        
        return problems
        
    def validate_reel_names(self, edit_points: List[EditPoint]):
        """Reel/Tape名検証
        
        Args:
            edit_points (List[EditPoint]): 編集点リスト
        """
        for ep in edit_points:
            # 必須チェック
            if not ep.reel or not ep.reel.strip():
                self.add_issue(
                    ValidationLevel.CRITICAL, "reel", ep.row_number, "reel",
                    "Reel/Tape名が空です", ep.reel,
                    "DaVinciのClip Attributes > Reel/Tapeと一致する名前を設定"
                )
                continue
                
            # 命名規則チェック（基本的な文字制限）
            reel_clean = ep.reel.strip()
            if len(reel_clean) > 32:  # EDL仕様での一般的な制限
                self.add_issue(
                    ValidationLevel.WARNING, "reel", ep.row_number, "reel",
                    f"Reel名が長すぎます（{len(reel_clean)}文字）", reel_clean,
                    "32文字以内に短縮"
                )
                
            # 特殊文字チェック
            if re.search(r'[<>:"/\\|?*]', reel_clean):
                self.add_issue(
                    ValidationLevel.WARNING, "reel", ep.row_number, "reel",
                    "Reel名に特殊文字が含まれています", reel_clean,
                    "英数字、ハイフン、アンダースコアのみ使用を推奨"
                )
                
    def run_preflight_validation(self, edit_points: List[EditPoint]) -> Dict[str, Any]:
        """プリフライト検証実行
        
        Args:
            edit_points (List[EditPoint]): 編集点リスト
            
        Returns:
            Dict[str, Any]: 検証結果サマリ
        """
        self.clear_issues()
        
        # 1. 基本データ検証
        valid_points = []
        for ep in edit_points:
            # フレーム数計算
            if ep.src_tc_in:
                ep.src_in_frames = tc_to_frames(ep.src_tc_in, ep.proj_fps)
            if ep.src_tc_out:
                ep.src_out_frames = tc_to_frames(ep.src_tc_out, ep.proj_fps)
                
            # In/Out関係検証
            if self.validate_in_out_relationship(ep):
                valid_points.append(ep)
                
        # 2. Reel名検証
        self.validate_reel_names(edit_points)
        
        # 3. 重複・交差検出
        overlap_problems = self.detect_overlaps_and_duplicates(valid_points)
        
        # 4. 統計集計
        total_points = len(edit_points)
        critical_issues = [i for i in self.issues if i.level == ValidationLevel.CRITICAL]
        warning_issues = [i for i in self.issues if i.level == ValidationLevel.WARNING]
        info_issues = [i for i in self.issues if i.level == ValidationLevel.INFO]
        
        summary = {
            'total_points': total_points,
            'valid_points': len(valid_points),
            'issues': {
                'critical': len(critical_issues),
                'warning': len(warning_issues), 
                'info': len(info_issues),
                'total': len(self.issues)
            },
            'overlap_problems': len(overlap_problems),
            'can_proceed': len(critical_issues) == 0,
            'recommendation': self._get_recommendation(critical_issues, warning_issues)
        }
        
        return summary
        
    def _get_recommendation(self, critical_issues: List[ValidationIssue], 
                          warning_issues: List[ValidationIssue]) -> str:
        """推奨アクションを取得"""
        if critical_issues:
            return f"❌ 処理停止: {len(critical_issues)}個のクリティカル問題を修正してください"
        elif warning_issues:
            return f"⚠️ 要確認: {len(warning_issues)}個の警告がありますが処理可能です"
        else:
            return "✅ 検証完了: 問題なし"
            
    def get_issues_by_category(self) -> Dict[str, List[ValidationIssue]]:
        """カテゴリ別問題リストを取得"""
        categories = {}
        for issue in self.issues:
            if issue.category not in categories:
                categories[issue.category] = []
            categories[issue.category].append(issue)
        return categories
        
    def generate_validation_report(self) -> str:
        """検証レポート生成"""
        if not self.issues:
            return "✅ 検証完了: 問題はありませんでした。"
            
        lines = ["📊 プリフライト検証レポート", "=" * 50]
        
        # カテゴリ別の集計
        categories = self.get_issues_by_category()
        
        for category, issues in categories.items():
            lines.append(f"\n📁 {category.upper()} ({len(issues)}件)")
            lines.append("-" * 30)
            
            for issue in issues:
                icon = {"critical": "❌", "warning": "⚠️", "info": "ℹ️"}[issue.level.value]
                lines.append(f"{icon} 行{issue.row_number:03d} [{issue.field}]: {issue.message}")
                if issue.suggested_fix:
                    lines.append(f"   💡 解決方法: {issue.suggested_fix}")
                    
        return "\n".join(lines)