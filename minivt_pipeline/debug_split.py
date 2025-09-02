#!/usr/bin/env python3
# デバッグ用: LLM統合分割ロジックをテスト

import re
import os
from src.utils.wrap import split_two_lines

test_text = "スマホの通知音。また転職エージェントからのスカウトメール。「年収30%アップ」「リモートワーク完全対応」「成長できる環境」—— 甘い言葉が並んでいます。"

print("=== LLM統合テキスト分割テスト ===")
print("Original text:")
print(f"'{test_text}'")
print(f"Length: {len(test_text)} characters")
print()

# Check if API key is available
api_key = os.getenv("OPENAI_API_KEY")
print(f"OpenAI API Key available: {'Yes' if api_key else 'No'}")
print()

# Test with LLM disabled (rule-based fallback)
print("--- Rule-based splitting (LLM disabled) ---")
result_rules = split_two_lines(test_text, 26, use_llm=False)
print("Rule-based result:")
for i, line in enumerate(result_rules, 1):
    print(f"Line {i}: '{line}' ({len(line)} chars)")
print()

# Test with LLM enabled (will fallback to rules if no API key)
print("--- LLM-first splitting ---")
result_llm = split_two_lines(test_text, 26, use_llm=True)
print("LLM-first result:")
for i, line in enumerate(result_llm, 1):
    print(f"Line {i}: '{line}' ({len(line)} chars)")
print()

print("Expected ideal split:")
print("Line 1: 'スマホの通知音 また転職エージェントからの'")
print("Line 2: 'スカウトメール 「年収30%アップ」「リモートワーク完全対応」「成長できる環境」'")
print("(but 2nd line may need truncation to fit 26 chars)")