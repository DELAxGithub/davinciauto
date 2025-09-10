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
            
        prompt = f"""あなたは日本語字幕の専門家です。以下のテキストを自然で読みやすい字幕に分割してください。

テキスト: {text}

分割要件:
• 各行: 最大{max_len}文字
• 最大2行まで
• 意味のまとまりを重視
• 「」内や数値+単位は分割禁止
• 自然な読みリズムを保持
• 文脈を失わない分割

出力形式（JSON）:
{{"lines": ["1行目", "2行目"]}}

単一行の場合:
{{"lines": ["単一行"]}}

例:
- 入力: "人工知能の発展により私たちの生活は大きく変化しています"
- 出力: {{"lines": ["人工知能の発展により", "私たちの生活は大きく変化しています"]}}"""

        try:
            response = openai.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "日本語字幕の専門家として、読みやすさと意味の保持を両立した自然な分割を行ってください。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.2
            )
            
            content = response.choices[0].message.content.strip()
            result = json.loads(content)
            
            if "lines" in result and isinstance(result["lines"], list):
                # Validate line lengths
                lines = result["lines"]
                if all(len(line) <= max_len for line in lines) and len(lines) <= 2:
                    return lines
                    
        except json.JSONDecodeError as e:
            print(f"[WARN] LLM response JSON parsing failed: {e}")
            print(f"[DEBUG] Raw response: {content if 'content' in locals() else 'No response'}")
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
            
        prompt = f"""日本語字幕の専門家として、長いテキストを複数の字幕カードに分割してください。

テキスト: {text}

分割要件:
• 1カード = 最大2行、各行{max_len}文字以内
• 意味の完結性を重視（文脈を保持）
• 情報の省略・要約禁止（全内容を保持）
• 「」内、数値+単位、固有名詞は分割禁止
• 自然な読みリズムと理解しやすさ

出力形式（JSON）:
{{"cards": [
  ["カード1行1", "カード1行2"],
  ["カード2行1"],
  ["カード3行1", "カード3行2"]
]}}

例:
- 短文: {{"cards": [["短いテキスト"]]}}
- 長文: {{"cards": [["前半の意味", "まとまり"], ["後半の意味", "まとまり"]]}}

重要: 全ての情報を保持し、読みやすく分割してください。"""

        try:
            response = openai.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "日本語字幕の専門家として、全ての情報を保持しながら自然で理解しやすい分割を行ってください。省略は一切しないでください。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.2
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
                    
        except json.JSONDecodeError as e:
            print(f"[WARN] LLM multiple subtitle response JSON parsing failed: {e}")
            print(f"[DEBUG] Raw response: {content if 'content' in locals() else 'No response'}")
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
