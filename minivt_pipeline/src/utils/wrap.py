from typing import List
import re

def split_two_lines(text: str, max_len: int = 22) -> List[str]:
    s = re.sub(r'\s+', '', text.strip())
    if len(s) <= max_len:
        return [s]
    target = min(max_len, max(8, len(s)//2))
    cut = s.find('、', target)
    if cut == -1:
        cut = max_len
    line1 = s[:cut+1]
    line2 = s[cut+1:]
    return [line1, line2]
