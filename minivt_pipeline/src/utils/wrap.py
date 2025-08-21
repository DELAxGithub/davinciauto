from typing import List
import re

def split_two_lines(text: str, max_len: int = 22) -> List[str]:
    """
    Split Japanese text into two lines for subtitle display.
    
    Algorithm:
    1. Remove whitespace and check if text fits in one line
    2. Find optimal split point around halfway mark
    3. Prefer splitting at Japanese comma (、) for natural breaks
    4. Fallback to max_len cutoff if no comma found
    
    Args:
        text: Japanese text to split
        max_len: Maximum characters per line (default: 22)
        
    Returns:
        List of 1-2 strings for subtitle display
    """
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
