from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class Cue:
    idx: int
    start: float
    end: float
    lines: List[str]

def to_timestamp(sec: float) -> str:
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    ms = int((sec - int(sec)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def distribute_by_audio_length(n_items: int, audio_length_sec: float, min_sec: float = 1.5) -> List[Tuple[float, float]]:
    dur = max(audio_length_sec / max(n_items,1), min_sec)
    times, t = [], 0.0
    for _ in range(n_items):
        start, end = t, min(audio_length_sec, t+dur)
        times.append((start,end))
        t = end
    return times

def build_srt(cues: List[Cue]) -> str:
    out = []
    for c in cues:
        out.append(str(c.idx))
        out.append(f"{to_timestamp(c.start)} --> {to_timestamp(c.end)}")
        out.append("\n".join(c.lines))
        out.append("")
    return "\n".join(out)
