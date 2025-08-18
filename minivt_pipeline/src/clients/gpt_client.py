import os, json
class GPTClient:
    def __init__(self, model: str = "gpt-4.1-mini"):
        self.model = model
        self.api_key = os.getenv("OPENAI_API_KEY")

    def generate(self, prompt: str, script_text: str):
        # 実際はOpenAI/Claude API呼び出しに差し替え
        return {
            "narration": [{"id":"NA-001","text":"人はなぜ学ぶのか。"}],
            "dialogues": [{"id":"DL-001","speaker":"人物A","text":"きっかけは写真でした。"}],
            "subtitles": [{"id":"SB-001","text_2line":["人はなぜ学ぶのか、","忙しい日常の中で。"]}]
        }
