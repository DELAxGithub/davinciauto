from dataclasses import dataclass
from typing import List, Tuple, Optional

@dataclass
class Cue:
    idx: int
    start: float
    end: float
    lines: List[str]
    role: str = ""  # Role identifier (NA, DL) for DaVinci Resolve styling
    uid: Optional[str] = None  # Human-readable unique ID (e.g., <title>-S001C01)

def to_timestamp(sec: float) -> str:
    """
    Convert seconds to SRT timestamp format (HH:MM:SS,mmm).
    
    Args:
        sec: Time in seconds (float)
        
    Returns:
        SRT-formatted timestamp string
    """
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    ms = int((sec - int(sec)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def distribute_by_audio_length(n_items: int, audio_length_sec: float, min_sec: float = 1.5) -> List[Tuple[float, float]]:
    """
    Distribute subtitle timing evenly across audio duration.
    
    Each subtitle gets equal time allocation, with minimum display duration.
    Ensures subtitles don't exceed audio length.
    
    Args:
        n_items: Number of subtitle segments
        audio_length_sec: Total audio duration in seconds
        min_sec: Minimum display time per subtitle (default: 1.5s)
        
    Returns:
        List of (start_time, end_time) tuples for each subtitle
    """
    dur = max(audio_length_sec / max(n_items,1), min_sec)
    times, t = [], 0.0
    for _ in range(n_items):
        start, end = t, min(audio_length_sec, t+dur)
        times.append((start,end))
        t = end
    return times

def build_srt(cues: List[Cue]) -> str:
    """
    Build SRT subtitle file content from cue objects with role identification.
    
    Format:
    1
    00:00:00,000 --> 00:00:02,500
    # ROLE:NA
    Subtitle line 1
    Subtitle line 2
    
    Args:
        cues: List of Cue objects with timing, text, and role information
        
    Returns:
        Complete SRT file content as string with role metadata
    """
    out = []
    for c in cues:
        out.append(str(c.idx))
        out.append(f"{to_timestamp(c.start)} --> {to_timestamp(c.end)}")
        
        # Add identification comments
        if c.role:
            out.append(f"# ROLE:{c.role}")
        if c.uid:
            out.append(f"# ID:{c.uid}")
        
        out.append("\n".join(c.lines))
        out.append("")
    return "\n".join(out)
