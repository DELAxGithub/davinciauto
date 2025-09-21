# timecode_utils.py
# タイムコード変換ユーティリティ
# HH:MM:SS:FF形式からフレーム数への変換とバリデーション

import re
from typing import Optional, Tuple

def parse_timecode(timecode_str: str) -> Optional[Tuple[int, int, int, int]]:
    """
    タイムコード文字列を解析して時:分:秒:フレームに分解
    
    Args:
        timecode_str: "HH:MM:SS:FF" 形式のタイムコード文字列
        
    Returns:
        (hours, minutes, seconds, frames) のタプル、失敗時はNone
        
    Examples:
        >>> parse_timecode("01:00:15:23")
        (1, 0, 15, 23)
        >>> parse_timecode("00:02:30:12") 
        (0, 2, 30, 12)
    """
    pattern = r'^(\d{2}):(\d{2}):(\d{2}):(\d{2})$'
    match = re.match(pattern, timecode_str.strip())
    
    if not match:
        return None
        
    try:
        hours = int(match.group(1))
        minutes = int(match.group(2))
        seconds = int(match.group(3))
        frames = int(match.group(4))
        
        # バリデーション
        if minutes >= 60 or seconds >= 60:
            return None
            
        return (hours, minutes, seconds, frames)
    except ValueError:
        return None

def timecode_to_frames(timecode_str: str, fps: float = 25.0) -> Optional[int]:
    """
    タイムコード文字列をフレーム数に変換
    
    Args:
        timecode_str: "HH:MM:SS:FF" 形式のタイムコード文字列
        fps: フレームレート (デフォルト: 25.0)
        
    Returns:
        フレーム数（整数）、失敗時はNone
        
    Examples:
        >>> timecode_to_frames("00:00:01:00", 25.0)
        25
        >>> timecode_to_frames("01:00:15:23", 25.0)
        90398
    """
    parsed = parse_timecode(timecode_str)
    if not parsed:
        return None
        
    hours, minutes, seconds, frames = parsed
    
    # フレーム数計算
    total_frames = (
        hours * 3600 * fps +       # 時間をフレーム数に
        minutes * 60 * fps +       # 分をフレーム数に
        seconds * fps +            # 秒をフレーム数に
        frames                     # フレーム数をそのまま
    )
    
    return int(total_frames)

def frames_to_timecode(frame_number: int, fps: float = 25.0) -> str:
    """
    フレーム数をタイムコード文字列に変換
    
    Args:
        frame_number: フレーム数
        fps: フレームレート (デフォルト: 25.0)
        
    Returns:
        "HH:MM:SS:FF" 形式のタイムコード文字列
        
    Examples:
        >>> frames_to_timecode(25, 25.0)
        "00:00:01:00"
        >>> frames_to_timecode(90398, 25.0) 
        "01:00:15:23"
    """
    if frame_number < 0:
        return "00:00:00:00"
    
    # 各単位への変換
    frames = int(frame_number % fps)
    total_seconds = int(frame_number // fps)
    
    seconds = total_seconds % 60
    total_minutes = total_seconds // 60
    
    minutes = total_minutes % 60
    hours = total_minutes // 60
    
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}"

def validate_timecode_range(start_tc: str, end_tc: str, fps: float = 25.0) -> bool:
    """
    タイムコード範囲の妥当性をチェック（開始 < 終了）
    
    Args:
        start_tc: 開始タイムコード
        end_tc: 終了タイムコード
        fps: フレームレート
        
    Returns:
        妥当性（True: 有効, False: 無効）
    """
    start_frames = timecode_to_frames(start_tc, fps)
    end_frames = timecode_to_frames(end_tc, fps)
    
    if start_frames is None or end_frames is None:
        return False
        
    return start_frames < end_frames

def get_duration_frames(start_tc: str, end_tc: str, fps: float = 25.0) -> Optional[int]:
    """
    タイムコード範囲の継続時間をフレーム数で取得
    
    Args:
        start_tc: 開始タイムコード
        end_tc: 終了タイムコード  
        fps: フレームレート
        
    Returns:
        継続時間（フレーム数）、失敗時はNone
    """
    start_frames = timecode_to_frames(start_tc, fps)
    end_frames = timecode_to_frames(end_tc, fps)
    
    if start_frames is None or end_frames is None:
        return None
        
    if start_frames >= end_frames:
        return None
        
    return end_frames - start_frames

def detect_fps_from_timecode(timecode_str: str) -> Optional[float]:
    """
    タイムコードから推定フレームレートを取得
    フレーム部分の最大値からfpsを推定
    
    Args:
        timecode_str: タイムコード文字列
        
    Returns:
        推定fps、推定不可の場合はNone
    """
    parsed = parse_timecode(timecode_str)
    if not parsed:
        return None
        
    _, _, _, frames = parsed
    
    # フレーム値からfps推定
    if frames < 24:
        return 25.0      # PAL
    elif frames < 25:
        return 24.0      # Film
    elif frames < 30:
        return 30.0      # NTSC
    elif frames < 50:
        return 50.0      # PAL Progressive
    elif frames < 60:
        return 60.0      # High frame rate
    else:
        return None      # 不明

# 一般的なフレームレート定数
COMMON_FPS = {
    'film': 24.0,
    'pal': 25.0,
    'ntsc': 29.97,
    'ntsc_drop': 29.97,
    'ntsc_non_drop': 30.0,
    'pal_progressive': 50.0,
    'high_fps': 60.0
}

if __name__ == "__main__":
    # テスト実行
    test_timecodes = [
        "01:00:15:23",
        "00:02:30:12", 
        "01:07:03:23",
        "02:31:51:12"
    ]
    
    print("Timecode conversion test:")
    for tc in test_timecodes:
        frames = timecode_to_frames(tc, 25.0)
        back_to_tc = frames_to_timecode(frames, 25.0)
        print(f"{tc} → {frames} frames → {back_to_tc}")
    
    print("\nRange validation test:")
    print(f"01:00:15:23 to 01:06:53:18: {validate_timecode_range('01:00:15:23', '01:06:53:18')}")
    print(f"Duration: {get_duration_frames('01:00:15:23', '01:06:53:18')} frames")