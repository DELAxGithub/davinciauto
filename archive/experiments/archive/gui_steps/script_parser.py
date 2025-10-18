"""
台本解析・セクション分割・CPS警告システム

オリオンEP1のような時系列台本を解析し、セクション分割・CPS計算・警告機能を提供
"""

import re
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict
from enum import Enum

class SpeakerType(Enum):
    """話者タイプ"""
    NARRATOR = "NA"  # ナレーター
    DIALOGUE = "DL"  # セリフ・対話
    QUOTE = "QT"     # 引用

@dataclass
class ScriptSegment:
    """台本セグメント"""
    text: str
    speaker_type: SpeakerType
    speaker_detail: str = ""  # 具体的な話者情報（例：「同僚A（女声・つぶやくように）」）
    timecode_start: Optional[str] = None  # [00:00-00:30] の開始部分
    timecode_end: Optional[str] = None    # [00:00-00:30] の終了部分
    section_title: str = ""               # セクションタイトル（例：「アバン」）

@dataclass 
class SubtitleCue:
    """字幕キュー（CPS計算付き）"""
    text: str
    duration_sec: float
    cps: float
    is_too_fast: bool = False
    speaker_type: SpeakerType = SpeakerType.NARRATOR

class CPSAnalyzer:
    """CPS（Characters Per Second）分析・警告システム"""
    
    def __init__(self, 
                 warning_threshold: float = 14.0,
                 safe_threshold: float = 6.0,
                 min_duration: float = 1.2):
        """
        Args:
            warning_threshold: 警告を出すCPS閾値（デフォルト: 14.0）
            safe_threshold: 安全とみなすCPS閾値（デフォルト: 6.0）
            min_duration: 最小表示時間（秒）
        """
        self.warning_threshold = warning_threshold
        self.safe_threshold = safe_threshold
        self.min_duration = min_duration
    
    def count_characters(self, text: str) -> int:
        """
        日本語文字数をカウント（全角・半角を適切に処理）
        
        Args:
            text: 対象テキスト
            
        Returns:
            文字数（全角基準）
        """
        # 改行・記号・スペースを除去
        clean_text = re.sub(r'[\n\r\s]', '', text)
        
        # 全角文字は1、半角文字は0.5でカウント
        char_count = 0
        for char in clean_text:
            if ord(char) > 127:  # 全角文字
                char_count += 1
            else:  # 半角文字
                char_count += 0.5
                
        return int(char_count)
    
    def calculate_cps(self, text: str, duration_sec: float) -> float:
        """
        CPS（Characters Per Second）を計算
        
        Args:
            text: 字幕テキスト
            duration_sec: 表示時間（秒）
            
        Returns:
            CPS値
        """
        char_count = self.count_characters(text)
        return char_count / max(duration_sec, 0.1)  # ゼロ除算回避
    
    def analyze_subtitle(self, text: str, duration_sec: float) -> SubtitleCue:
        """
        字幕の CPS 分析を実行
        
        Args:
            text: 字幕テキスト
            duration_sec: 表示時間（秒）
            
        Returns:
            分析結果付きSubtitleCue
        """
        cps = self.calculate_cps(text, duration_sec)
        is_too_fast = cps > self.warning_threshold
        
        return SubtitleCue(
            text=text,
            duration_sec=duration_sec,
            cps=cps,
            is_too_fast=is_too_fast
        )
    
    def generate_warnings(self, cues: List[SubtitleCue]) -> List[str]:
        """
        CPS警告レポートを生成
        
        Args:
            cues: 字幕キューリスト
            
        Returns:
            警告メッセージリスト
        """
        warnings = []
        
        for i, cue in enumerate(cues, 1):
            if cue.is_too_fast:
                warnings.append(
                    f"⚠️ #{i}: CPS {cue.cps:.1f} (>{self.warning_threshold}) "
                    f"「{cue.text[:20]}...」"
                )
        
        if not warnings:
            warnings.append("✅ CPS警告はありません")
            
        return warnings

class ScriptParser:
    """台本解析システム"""
    
    def __init__(self):
        """台本パーサーを初期化"""
        # タイムコード検出パターン [00:00-00:30]
        self.timecode_pattern = re.compile(r'\[(\d{2}:\d{2})-(\d{2}:\d{2})\]\s*(.*)')
        
        # 話者指定検出パターン
        self.speaker_patterns = {
            SpeakerType.DIALOGUE: re.compile(r'^([^（]*?)（([^）]*)）：\s*(.*)$'),
            SpeakerType.QUOTE: re.compile(r'^([^（]*?)（([^）]*)）：\s*「(.*)」$'),
        }
    
    def parse_timecode(self, timecode_str: str) -> Tuple[float, float]:
        """
        タイムコード文字列を秒に変換
        
        Args:
            timecode_str: "00:30" 形式のタイムコード
            
        Returns:
            タイムコード（秒）
        """
        minutes, seconds = map(int, timecode_str.split(':'))
        return minutes * 60 + seconds
    
    def detect_speaker(self, line: str) -> Tuple[SpeakerType, str, str]:
        """
        話者タイプを検出
        
        Args:
            line: 台本の行
            
        Returns:
            (話者タイプ, 話者詳細, クリーンアップされたテキスト)
        """
        # 対話・引用パターンをチェック
        for speaker_type, pattern in self.speaker_patterns.items():
            match = pattern.match(line)
            if match:
                speaker_name = match.group(1).strip()
                speaker_detail = match.group(2).strip()
                text = match.group(3).strip()
                full_detail = f"{speaker_name}（{speaker_detail}）"
                
                return speaker_type, full_detail, text
        
        # デフォルトはナレーター
        return SpeakerType.NARRATOR, "", line
    
    def parse_script(self, script_content: str) -> List[ScriptSegment]:
        """
        台本を解析してセグメントに分割
        
        Args:
            script_content: 台本テキスト
            
        Returns:
            セグメントリスト
        """
        lines = script_content.strip().split('\n')
        segments = []
        current_section = ""
        current_timecode_start = None
        current_timecode_end = None
        
        for line in lines:
            line = line.strip()
            
            # 空行・コメント・校正チェックリストをスキップ
            if not line or line.startswith('【') or line.startswith('必須確認事項'):
                continue
            
            # タイトル行をスキップ
            if '第1話' in line and 'オリオン' in line:
                continue
                
            # タイムコード行の処理
            timecode_match = self.timecode_pattern.match(line)
            if timecode_match:
                current_timecode_start = timecode_match.group(1)
                current_timecode_end = timecode_match.group(2)
                current_section = timecode_match.group(3).strip()
                continue
            
            # 通常のテキスト行の処理
            speaker_type, speaker_detail, clean_text = self.detect_speaker(line)
            
            # セグメント作成
            segment = ScriptSegment(
                text=clean_text,
                speaker_type=speaker_type,
                speaker_detail=speaker_detail,
                timecode_start=current_timecode_start,
                timecode_end=current_timecode_end,
                section_title=current_section
            )
            
            segments.append(segment)
        
        return segments

def create_test_analyzer() -> CPSAnalyzer:
    """テスト用のCPSアナライザーを作成"""
    return CPSAnalyzer(
        warning_threshold=14.0,
        safe_threshold=6.0,
        min_duration=1.2
    )

# テスト用のサンプル実行
if __name__ == "__main__":
    # デモンストレーション用
    sample_text = "転職した同期の投稿を見て、焦りを感じたことはありませんか？"
    
    analyzer = create_test_analyzer()
    cue = analyzer.analyze_subtitle(sample_text, 3.0)
    
    print(f"テキスト: {sample_text}")
    print(f"文字数: {analyzer.count_characters(sample_text)}")
    print(f"表示時間: {cue.duration_sec}秒")
    print(f"CPS: {cue.cps:.2f}")
    print(f"警告: {'⚠️ 速すぎます' if cue.is_too_fast else '✅ 適切な速度'}")