#!/usr/bin/env python3
"""
Test script for ClaudeClient implementation.
Tests Japanese subtitle splitting functionality.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from clients.claude_client import ClaudeClient
from utils.wrap import split_two_lines, split_text_to_multiple_subtitles


def test_claude_client_direct():
    """Test ClaudeClient directly."""
    print("=== Testing ClaudeClient directly ===")
    
    client = ClaudeClient()
    
    # Test single subtitle splitting
    test_texts = [
        "転職エージェントからのスカウトメールがたくさん来るようになりました",
        "人はなぜ学ぶのか、忙しい日常の中で成長を求めるのでしょうか",
        "短いテスト",
        "AIと機械学習の技術革新により、私たちの働き方も大きく変わってきています"
    ]
    
    for i, text in enumerate(test_texts, 1):
        print(f"\nTest {i}: {text}")
        print(f"Length: {len(text)} chars")
        
        result = client.split_text_for_subtitle(text, max_len=26)
        if result:
            print(f"Result: {result}")
            for j, line in enumerate(result):
                print(f"  Line {j+1}: '{line}' ({len(line)} chars)")
        else:
            print("Result: None (fallback expected)")
    
    # Test multiple subtitle cards
    print("\n=== Testing Multiple Subtitle Cards ===")
    long_text = "転職エージェントからのスカウトメールがたくさん来るようになりました。リモートワーク完全対応の企業からの求人も増えており、年収30%アップの提案も珍しくありません。現代の働き方の変化を実感しています。"
    
    print(f"Long text: {long_text}")
    print(f"Length: {len(long_text)} chars")
    
    cards = client.split_text_for_multiple_subtitles(long_text, max_len=26)
    if cards:
        print(f"Cards result: {len(cards)} cards")
        for i, card in enumerate(cards, 1):
            print(f"  Card {i}: {card}")
            for j, line in enumerate(card):
                print(f"    Line {j+1}: '{line}' ({len(line)} chars)")
    else:
        print("Cards result: None (fallback expected)")


def test_utils_wrap():
    """Test utils.wrap functions with new implementation."""
    print("\n=== Testing utils.wrap functions ===")
    
    test_cases = [
        "転職エージェントからのスカウトメール",
        "人はなぜ学ぶのか、忙しい日常の中で",
        "AIと機械学習の技術革新により、私たちの働き方も変わってきています"
    ]
    
    for i, text in enumerate(test_cases, 1):
        print(f"\nTest case {i}: {text}")
        
        # Test split_two_lines
        result = split_two_lines(text, max_len=26, use_llm=True)
        print(f"split_two_lines: {result}")
        
        # Test split_text_to_multiple_subtitles
        cards = split_text_to_multiple_subtitles(text, max_len=26, use_llm=True)
        print(f"split_text_to_multiple_subtitles: {cards}")


def test_fallback_behavior():
    """Test fallback to rule-based behavior."""
    print("\n=== Testing Fallback Behavior ===")
    
    # Test with use_llm=False to ensure rule-based fallback works
    text = "転職エージェントからのスカウトメールがたくさん来るようになりました"
    
    print(f"Test text: {text}")
    
    # Force rule-based
    result_rule = split_two_lines(text, max_len=26, use_llm=False)
    print(f"Rule-based result: {result_rule}")
    
    # Try Claude Code (may fallback to rule-based)
    result_claude = split_two_lines(text, max_len=26, use_llm=True)
    print(f"Claude Code result: {result_claude}")


if __name__ == "__main__":
    print("Testing Claude Code integration for Japanese subtitle splitting")
    print("=" * 60)
    
    try:
        test_claude_client_direct()
        test_utils_wrap()
        test_fallback_behavior()
        
        print("\n" + "=" * 60)
        print("All tests completed!")
        
    except Exception as e:
        print(f"\nTest error: {e}")
        import traceback
        traceback.print_exc()