#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SRTマージツール（完全自動版 v2）
- timecodeの長い字幕を検出し、複数のep8字幕とマッチング
- 文字数比率でタイムコードを自動分割
"""

import re
from dataclasses import dataclass
from typing import List


@dataclass
class Subtitle:
    index: int
    start_time: str
    end_time: str
    text: str
    
    def duration_ms(self) -> int:
        return self._time_to_ms(self.end_time) - self._time_to_ms(self.start_time)
    
    def start_ms(self) -> int:
        return self._time_to_ms(self.start_time)
    
    def end_ms(self) -> int:
        return self._time_to_ms(self.end_time)
    
    def char_count(self) -> int:
        """文字数をカウント（空白・改行除く）"""
        return len(re.sub(r'\s', '', self.text))
    
    @staticmethod
    def _time_to_ms(time_str: str) -> int:
        match = re.match(r'(\d+):(\d+):(\d+),(\d+)', time_str)
        if match:
            h, m, s, ms = map(int, match.groups())
            return h * 3600000 + m * 60000 + s * 1000 + ms
        return 0
    
    @staticmethod
    def _ms_to_time(ms: int) -> str:
        hours = ms // 3600000
        ms %= 3600000
        minutes = ms // 60000
        ms %= 60000
        seconds = ms // 1000
        milliseconds = ms % 1000
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def parse_srt(content: str) -> List[Subtitle]:
    """SRTファイルをパース"""
    subtitles = []
    content = re.sub(r'```srt\s*', '', content)
    content = re.sub(r'```\s*$', '', content)
    
    blocks = re.split(r'\n\s*\n', content.strip())
    
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) >= 3:
            try:
                index = int(lines[0])
                time_match = re.match(r'(\d+:\d+:\d+,\d+)\s*-->\s*(\d+:\d+:\d+,\d+)', lines[1])
                if time_match:
                    start_time = time_match.group(1)
                    end_time = time_match.group(2)
                    text = '\n'.join(lines[2:])
                    subtitles.append(Subtitle(index, start_time, end_time, text))
            except (ValueError, IndexError):
                continue
    
    return subtitles


def normalize_text(text: str) -> str:
    """テキストを正規化（比較用）"""
    text = re.sub(r'[、。，．,.！？!?\s\n「」『』""''（）()【】——…・※★]', '', text)
    return text.lower()


def calculate_text_overlap(text1: str, text2: str) -> float:
    """2つのテキストの重なり度を計算（0.0-1.0）"""
    norm1 = normalize_text(text1)
    norm2 = normalize_text(text2)
    
    if not norm1 or not norm2:
        return 0.0
    
    # 共通文字の割合
    common = sum(1 for c in norm1 if c in norm2)
    return common / max(len(norm1), len(norm2))


def find_best_ep8_group(tc_sub: Subtitle, ep8_subs: List[Subtitle], 
                        start_idx: int) -> List[Subtitle]:
    """
    timecode字幕に最もマッチするep8字幕グループを探す
    """
    tc_text_norm = normalize_text(tc_sub.text)
    tc_char_count = len(tc_text_norm)
    
    best_group = [ep8_subs[start_idx]] if start_idx < len(ep8_subs) else []
    best_score = 0.0
    
    # 最大10個まで試す
    for group_size in range(1, min(11, len(ep8_subs) - start_idx + 1)):
        ep8_group = ep8_subs[start_idx:start_idx + group_size]
        combined_text = ''.join(normalize_text(sub.text) for sub in ep8_group)
        combined_char_count = len(combined_text)
        
        # スコア計算：テキストの重なり + 文字数の近さ
        overlap = calculate_text_overlap(tc_sub.text, ''.join(sub.text for sub in ep8_group))
        char_ratio = min(tc_char_count, combined_char_count) / max(tc_char_count, combined_char_count, 1)
        
        score = overlap * 0.7 + char_ratio * 0.3
        
        if score > best_score:
            best_score = score
            best_group = ep8_group
        
        # 文字数が多すぎたら打ち切り
        if combined_char_count > tc_char_count * 1.5:
            break
    
    return best_group


def redistribute_by_chars(tc_sub: Subtitle, ep8_group: List[Subtitle]) -> List[Subtitle]:
    """
    文字数比率でタイムコードを再分配
    """
    result = []
    
    # 各字幕の文字数
    char_counts = [sub.char_count() for sub in ep8_group]
    total_chars = sum(char_counts)
    
    if total_chars == 0:
        char_counts = [1] * len(ep8_group)
        total_chars = len(ep8_group)
    
    # タイムコード分配
    start_ms = tc_sub.start_ms()
    total_duration = tc_sub.duration_ms()
    
    accumulated_ms = 0
    for i, (ep8_sub, char_count) in enumerate(zip(ep8_group, char_counts)):
        duration = int(total_duration * char_count / total_chars)
        
        # 最後は端数調整
        if i == len(ep8_group) - 1:
            duration = total_duration - accumulated_ms
        
        new_start_ms = start_ms + accumulated_ms
        new_end_ms = new_start_ms + duration
        
        new_sub = Subtitle(
            index=0,
            start_time=Subtitle._ms_to_time(new_start_ms),
            end_time=Subtitle._ms_to_time(new_end_ms),
            text=ep8_sub.text
        )
        result.append(new_sub)
        
        accumulated_ms += duration
    
    return result


def merge_auto(ep8_subs: List[Subtitle], timecode_subs: List[Subtitle]) -> List[Subtitle]:
    """
    完全自動マージ
    """
    merged = []
    ep8_idx = 0
    
    for tc_sub in timecode_subs:
        if ep8_idx >= len(ep8_subs):
            break
        
        # 最適なep8グループを探す
        ep8_group = find_best_ep8_group(tc_sub, ep8_subs, ep8_idx)
        
        # 文字数比率でタイムコード再分配
        redistributed = redistribute_by_chars(tc_sub, ep8_group)
        merged.extend(redistributed)
        
        ep8_idx += len(ep8_group)
    
    # 残りがあれば追加
    while ep8_idx < len(ep8_subs):
        sub = ep8_subs[ep8_idx]
        merged.append(Subtitle(0, sub.start_time, sub.end_time, sub.text))
        ep8_idx += 1
    
    # インデックス振り直し
    for i, sub in enumerate(merged):
        sub.index = i + 1
    
    return merged


def write_srt(subtitles: List[Subtitle], output_path: str):
    """SRTファイル出力"""
    with open(output_path, 'w', encoding='utf-8') as f:
        for sub in subtitles:
            f.write(f"{sub.index}\n")
            f.write(f"{sub.start_time} --> {sub.end_time}\n")
            f.write(f"{sub.text}\n\n")


def main():
    # ファイル読み込み
    with open('/mnt/user-data/uploads/ep8.srt', 'r', encoding='utf-8') as f:
        ep8_content = f.read()
    
    with open('/mnt/user-data/uploads/orion_ep8_timecode.srt', 'r', encoding='utf-8') as f:
        timecode_content = f.read()
    
    # パース
    print("📖 ep8.srtをパース中...")
    ep8_subs = parse_srt(ep8_content)
    print(f"   {len(ep8_subs)}個の字幕を検出")
    
    print("\n📖 orion_ep8_timecode.srtをパース中...")
    timecode_subs = parse_srt(timecode_content)
    print(f"   {len(timecode_subs)}個の字幕を検出")
    
    # マージ
    print("\n🔄 完全自動マージ処理中（文字数ベース分割）...")
    merged_subs = merge_auto(ep8_subs, timecode_subs)
    print(f"   {len(merged_subs)}個の字幕を生成")
    
    # 出力
    output_path = '/mnt/user-data/outputs/ep8_merged.srt'
    write_srt(merged_subs, output_path)
    print(f"\n✅ 完了！\n   出力: {output_path}")
    
    # サンプル表示
    print("\n=== サンプル（5-10番）===")
    for sub in merged_subs[4:10]:
        duration_sec = (sub.end_ms() - sub.start_ms()) / 1000.0
        char_count = sub.char_count()
        print(f"\n{sub.index}")
        print(f"{sub.start_time} --> {sub.end_time}  ({duration_sec:.1f}秒, {char_count}文字)")
        print(sub.text)


if __name__ == '__main__':
    main()
