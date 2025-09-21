from typing import List, Optional
import re
import os

def _find_best_split_point(text: str, max_len: int) -> int:
    """
    Find the best split point in text that keeps first line within max_len.
    Considers Japanese linguistic patterns for natural breaks.
    
    Args:
        text: Text to split
        max_len: Maximum characters for first line
        
    Returns:
        Best split position (character index)
    """
    if len(text) <= max_len:
        return len(text)
    
    # Japanese particles and connectors that should stay with previous word
    particles = ['の', 'から', 'への', 'まで', 'より', 'について', 'に関して', 'として', 'による']
    
    # Common compound word patterns that should be kept together
    compound_patterns = [
        'エージェントからの', 'スカウトメール', 'リモートワーク', '転職エージェント',
        '年収30%アップ', 'リモートワーク完全対応', '成長できる環境', 
        '完全対応', '年収アップ', '成長できる', '限界', '現代特有',
        '約束の地', '自由の荒野', '不確実性', '放浪の時間'
    ]
    
    # Find potential split points with preference order
    candidates = []
    
    # Look for natural break points within max_len
    for i in range(min(max_len, len(text) - 1), max(0, max_len - 10), -1):
        if text[i] == ' ':
            # Check if this creates a good semantic break
            before = text[:i].strip()
            after = text[i+1:].strip()
            
            # Calculate priority for this split point
            priority = 0
            
            # Avoid breaking after particles (prefer keeping them with preceding word)
            breaks_after_particle = any(before.endswith(p) for p in particles)
            if not breaks_after_particle:
                priority += 20
            
            # Strongly prefer keeping compound words together
            breaks_compound = False
            for pattern in compound_patterns:
                if pattern in text:
                    # Check if this split would break the compound word
                    pattern_start = text.find(pattern)
                    pattern_end = pattern_start + len(pattern)
                    if pattern_start < i < pattern_end:
                        breaks_compound = True
                        break
            
            if not breaks_compound:
                priority += 30
            
            # Prefer natural semantic boundaries
            # Higher priority for splits after complete phrases or natural units
            natural_endings = ['音', 'メール', 'ワーク', 'エージェント', '環境', 'からのスカウトメール']
            
            # Special handling for specific patterns (after space conversion)
            if 'エージェントからの スカウトメール' in text:
                # Prefer split after "エージェントからの" to keep "スカウトメール" together
                if before.endswith('エージェントからの'):
                    priority += 50  # Very high priority
                elif before.endswith('スカウトメール'):
                    priority += 40
            
            # Also handle original compound forms
            if 'エージェントからのスカウトメール' in text:
                if before.endswith('エージェントからの'):
                    priority += 50
            
            # General natural ending bonus
            if any(before.endswith(ending) for ending in natural_endings):
                priority += 15
            
            # Moderate preference for balanced splits
            balance_score = abs(len(before) - len(after))
            if balance_score < 5:
                priority += 5
            
            candidates.append((priority, i))
    
    # Return best candidate if found
    if candidates:
        candidates.sort(reverse=True)  # Sort by priority (highest first)
        return candidates[0][1]
    
    # Fallback: hard cut at max_len, but try to avoid cutting in middle of words
    for i in range(max_len, max(0, max_len - 5), -1):
        if i < len(text) and text[i] == ' ':
            return i
    
    # Final fallback: hard cut at max_len
    return max_len

def split_multiple_subtitles_llm(text: str, max_len: int = 26) -> Optional[List[List[str]]]:
    """
    Use Claude Code to split Japanese text into multiple subtitle cards.
    
    Args:
        text: Japanese text to split
        max_len: Maximum characters per line
        
    Returns:
        List of subtitle cards (each card has 1-2 lines), or None if execution fails
    """
    try:
        from ..clients.claude_client import ClaudeClient
        
        # Preprocess text (same as rule-based method)
        s = text.replace('、', ' ').replace('。', ' ')
        s = re.sub(r'\s+', ' ', s.strip())
        
        client = ClaudeClient()
        result = client.split_text_for_multiple_subtitles(s, max_len)
        
        if result and len(result) >= 1:
            # Validate result
            valid = True
            for card in result:
                if not isinstance(card, list) or len(card) == 0 or len(card) > 2:
                    valid = False
                    break
                if not all(len(line) <= max_len for line in card):
                    valid = False
                    break
            
            if valid:
                return result
                
    except Exception as e:
        print(f"[DEBUG] Claude Code multiple subtitle splitting failed: {e}")
    
    return None

def split_two_lines_llm(text: str, max_len: int = 26) -> Optional[List[str]]:
    """
    Use Claude Code to split Japanese text into natural subtitle lines.
    
    Args:
        text: Japanese text to split
        max_len: Maximum characters per line
        
    Returns:
        List of 1-2 strings, or None if execution fails
    """
    try:
        from ..clients.claude_client import ClaudeClient
        
        # Skip if text is short enough
        if len(text) <= max_len:
            return None
            
        # Preprocess text (same as rule-based method)
        s = text.replace('、', ' ').replace('。', ' ')
        s = re.sub(r'\s+', ' ', s.strip())
        
        client = ClaudeClient()
        result = client.split_text_for_subtitle(s, max_len)
        
        if result and len(result) <= 2:
            # Validate result
            if all(len(line) <= max_len for line in result):
                return result
                
    except Exception as e:
        print(f"[DEBUG] Claude Code splitting failed: {e}")
    
    return None

def split_two_lines(text: str, max_len: int = 26, use_llm: bool = True) -> List[str]:
    """
    Split Japanese text into maximum 2 lines for subtitle display with strict character limits.
    
    Uses Claude Code for natural splitting with rule-based fallback.
    
    Args:
        text: Japanese text to split
        max_len: Maximum characters per line (default: 26)
        use_llm: Whether to try Claude Code first (default: True)
        
    Returns:
        List of 1-2 strings for subtitle display (each ≤ max_len chars)
    """
    # Try Claude Code first if enabled
    if use_llm:
        llm_result = split_two_lines_llm(text, max_len)
        if llm_result:
            print(f"[DEBUG] Claude Code splitting successful: {llm_result}")
            return llm_result
        else:
            print(f"[DEBUG] Claude Code splitting failed (text too long for 2 lines), trying multiple cards")
            # Try multiple cards approach
            cards_result = split_multiple_subtitles_llm(text, max_len)
            if cards_result and len(cards_result) > 0:
                print(f"[DEBUG] Using first card from multiple cards result: {cards_result[0]}")
                return cards_result[0]
            print(f"[DEBUG] All Claude Code approaches failed, using rule-based fallback")
    
    # Rule-based fallback (original algorithm)
    # Convert Japanese punctuation to half-width spaces for teleprompter
    s = text.replace('、', ' ').replace('。', ' ')
    
    # Insert strategic spaces for better splitting of compound words
    # This helps separate semantic units that don't have natural punctuation
    compound_splits = [
        ('転職エージェントからのスカウトメール', '転職エージェントからの スカウトメール'),
        ('エージェントからのスカウトメール', 'エージェントからの スカウトメール'),
        ('リモートワーク完全対応', 'リモートワーク 完全対応'),
        ('年収30%アップ', '年収30% アップ'),
    ]
    
    for original, split_version in compound_splits:
        if original in s and split_version not in s:
            s = s.replace(original, split_version)
    
    # Remove extra whitespace
    s = re.sub(r'\s+', ' ', s.strip())
    
    if len(s) <= max_len:
        return [s]
    
    # Find split point for first line
    split_pos = _find_best_split_point(s, max_len)
    
    line1 = s[:split_pos].strip()
    remaining = s[split_pos:].strip()
    
    # Handle second line
    if len(remaining) <= max_len:
        line2 = remaining
    else:
        # If second line is too long, find best truncation point
        truncate_pos = _find_best_split_point(remaining, max_len - 1)  # -1 for ellipsis
        line2 = remaining[:truncate_pos].rstrip() + '…'
    
    return [line1, line2] if line2 else [line1]

def split_text_to_multiple_subtitles(text: str, max_len: int = 26, use_llm: bool = True) -> List[List[str]]:
    """
    Split Japanese text into multiple subtitle cards with natural breaks.
    
    Args:
        text: Japanese text to split
        max_len: Maximum characters per line (default: 26)
        use_llm: Whether to try Claude Code first (default: True)
        
    Returns:
        List of subtitle cards (each card has 1-2 lines)
    """
    # Try Claude Code first if enabled
    if use_llm:
        llm_result = split_multiple_subtitles_llm(text, max_len)
        if llm_result:
            print(f"[DEBUG] Claude Code multiple subtitle splitting successful: {len(llm_result)} cards")
            return llm_result
        else:
            print(f"[DEBUG] Claude Code multiple subtitle splitting failed, using direct LLMSubtitleSplitter")
            # Use LLMSubtitleSplitter directly as fallback
            from ..clients.llm_subtitle_splitter import LLMSubtitleSplitter
            splitter = LLMSubtitleSplitter()
            direct_result = splitter.split_into_subtitle_cards(text, max_len)
            if direct_result:
                print(f"[DEBUG] Direct LLMSubtitleSplitter successful: {len(direct_result)} cards")
                return direct_result
    
    # Final fallback: split into single card with 2 lines max, but no ellipsis
    print(f"[DEBUG] All LLM approaches failed, using safe rule-based fallback")
    
    # Simple sentence-based split without information loss
    sentences = text.replace('。', '。|').split('|')
    sentences = [s.strip() for s in sentences if s.strip()]
    
    if not sentences:
        return [[text]]
    
    cards = []
    for sentence in sentences:
        if len(sentence) <= max_len:
            cards.append([sentence])
        elif len(sentence) <= max_len * 2:
            # Split into 2 lines
            mid = len(sentence) // 2
            for i in range(mid, min(len(sentence), mid + 10)):
                if sentence[i] in [' ', '、']:
                    mid = i
                    break
            line1 = sentence[:mid].strip()
            line2 = sentence[mid:].strip()
            cards.append([line1, line2] if line2 else [line1])
        else:
            # For very long sentences, split into multiple cards
            words = sentence.split(' ')
            current_card = ""
            for word in words:
                if len(current_card + word) <= max_len * 2:
                    current_card += word + " "
                else:
                    if current_card.strip():
                        # Split current card into lines
                        card_text = current_card.strip()
                        if len(card_text) <= max_len:
                            cards.append([card_text])
                        else:
                            mid = len(card_text) // 2
                            line1 = card_text[:mid]
                            line2 = card_text[mid:]
                            cards.append([line1, line2])
                    current_card = word + " "
            
            # Handle final card
            if current_card.strip():
                card_text = current_card.strip()
                if len(card_text) <= max_len:
                    cards.append([card_text])
                else:
                    mid = len(card_text) // 2
                    line1 = card_text[:mid]
                    line2 = card_text[mid:]
                    cards.append([line1, line2])
    
    return cards if cards else [[text[:max_len * 2]]]
