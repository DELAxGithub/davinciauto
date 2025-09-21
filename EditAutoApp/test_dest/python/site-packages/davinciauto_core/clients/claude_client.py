import os
import json
from typing import List, Optional
from .llm_subtitle_splitter import LLMSubtitleSplitter


class ClaudeClient:
    """
    Simplified Claude client using LLMSubtitleSplitter for Japanese text processing.
    Provides compatibility with existing GPTClient interface.
    """
    
    def __init__(self):
        """Initialize Claude client with LLM subtitle splitter."""
        self.splitter = LLMSubtitleSplitter()

    def split_text_for_subtitle(self, text: str, max_len: int = 26) -> Optional[List[str]]:
        """
        Split Japanese text into natural subtitle lines using LLM intelligence.
        
        Args:
            text: Japanese text to split
            max_len: Maximum characters per line
            
        Returns:
            List of 1-2 strings, or None if text is too long for single card
        """
        return self.splitter.split_for_single_card(text, max_len)

    def split_text_for_multiple_subtitles(self, text: str, max_len: int = 26) -> Optional[List[List[str]]]:
        """
        Split Japanese text into multiple subtitle cards using LLM intelligence.
        
        Args:
            text: Japanese text to split
            max_len: Maximum characters per line
            
        Returns:
            List of subtitle cards (each card has 1-2 lines), or None if analysis fails
        """
        cards = self.splitter.split_into_subtitle_cards(text, max_len)
        return cards if cards else None

    def generate(self, prompt: str, script_text: str):
        """
        Placeholder for future JSON generation features.
        Currently returns stub data like original GPTClient.
        """
        return {
            "narration": [{"id": "NA-001", "text": "人はなぜ学ぶのか。"}],
            "dialogues": [{"id": "DL-001", "speaker": "人物A", "text": "きっかけは写真でした。"}],
            "subtitles": [{"id": "SB-001", "text_2line": ["人はなぜ学ぶのか、", "忙しい日常の中で。"]}]
        }