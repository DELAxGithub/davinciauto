import os, json
from typing import List, Optional
import openai

class GPTClient:
    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model
        self.api_key = os.getenv("OPENAI_API_KEY")
        if self.api_key:
            openai.api_key = self.api_key

    def split_text_for_subtitle(self, text: str, max_len: int = 26) -> Optional[List[str]]:
        """
        Use LLM to split Japanese text into natural subtitle lines.
        
        Args:
            text: Japanese text to split
            max_len: Maximum characters per line
            
        Returns:
            List of 1-2 strings, or None if API fails
        """
        if not self.api_key:
            return None
            
        prompt = f"""以下の日本語テキストを{max_len}文字以内の最大2行に自然に分割してください。

分割ルール:
1. 各行は{max_len}文字以内
2. 「」内は分割しない（引用符の途中で改行しない）
3. 意味のある単語境界で分割
4. 自然で読みやすい分割
5. 句読点は半角スペースに変換済みです

テキスト: {text}

回答は以下のJSON形式で返してください:
{{"lines": ["1行目のテキスト", "2行目のテキスト"]}}

1行に収まる場合は:
{{"lines": ["1行目のテキストのみ"]}}"""

        try:
            response = openai.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "あなたは日本語テロップの専門家です。自然で読みやすい分割を心がけてください。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.3
            )
            
            content = response.choices[0].message.content.strip()
            result = json.loads(content)
            
            if "lines" in result and isinstance(result["lines"], list):
                # Validate line lengths
                lines = result["lines"]
                if all(len(line) <= max_len for line in lines) and len(lines) <= 2:
                    return lines
                    
        except Exception as e:
            print(f"[WARN] LLM text splitting failed: {e}")
            
        return None

    def split_text_for_multiple_subtitles(self, text: str, max_len: int = 26) -> Optional[List[List[str]]]:
        """
        Use LLM to split Japanese text into multiple subtitle cards.
        
        Args:
            text: Japanese text to split
            max_len: Maximum characters per line
            
        Returns:
            List of subtitle cards (each card has 1-2 lines), or None if API fails
        """
        if not self.api_key:
            return None
            
        prompt = f"""以下の日本語テキストを、テロップ用に分割してください。

分割ルール:
1. 1枚のテロップ = 最大2行、各行{max_len}文字以内
2. 長い文章は複数枚に自然に分割
3. 「」内は分割しない（引用符の途中で改行しない）
4. 意味のある区切りで分割
5. 情報を省略しない（「…」禁止）
6. 句読点は半角スペースに変換済みです

テキスト: {text}

回答は以下のJSON形式で返してください:
{{"cards": [
  ["1枚目1行目", "1枚目2行目"],
  ["2枚目1行目", "2枚目2行目"],
  ["3枚目1行目"]
]}}

例:
- 短い場合: {{"cards": [["短いテキスト"]]}}
- 2行の場合: {{"cards": [["1行目", "2行目"]]}}
- 複数枚の場合: {{"cards": [["1枚目1行目", "1枚目2行目"], ["2枚目1行目", "2枚目2行目"]]}}"""

        try:
            response = openai.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "あなたは日本語テロップの専門家です。情報を失わず、自然で読みやすい分割を心がけてください。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.3
            )
            
            content = response.choices[0].message.content.strip()
            result = json.loads(content)
            
            if "cards" in result and isinstance(result["cards"], list):
                cards = result["cards"]
                # Validate each card
                valid_cards = []
                for card in cards:
                    if isinstance(card, list) and len(card) <= 2:
                        if all(isinstance(line, str) and len(line) <= max_len for line in card):
                            valid_cards.append(card)
                
                if valid_cards:
                    return valid_cards
                    
        except Exception as e:
            print(f"[WARN] LLM multiple subtitle splitting failed: {e}")
            
        return None

    def generate(self, prompt: str, script_text: str):
        # 実際はOpenAI/Claude API呼び出しに差し替え
        return {
            "narration": [{"id":"NA-001","text":"人はなぜ学ぶのか。"}],
            "dialogues": [{"id":"DL-001","speaker":"人物A","text":"きっかけは写真でした。"}],
            "subtitles": [{"id":"SB-001","text_2line":["人はなぜ学ぶのか、","忙しい日常の中で。"]}]
        }
