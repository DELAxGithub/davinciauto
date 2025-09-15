#!/usr/bin/env python3
"""
日本語TTS精度向上ツール
Google AI Studio手打ち品質を目指すための前処理・最適化
"""
import re
import unicodedata
from typing import Dict, List, Tuple

class JapaneseTTSOptimizer:
    """日本語音声合成最適化クラス"""

    def __init__(self):
        # 読み方辞書（カスタマイズ可能）
        self.reading_dict = {
            # 英語・カタカナ
            "AI": "エーアイ",
            "API": "エーピーアイ",
            "TTS": "ティーティーエス",
            "SNS": "エスエヌエス",
            "CEO": "シーイーオー",

            # 略語・固有名詞
            "オリオン": "オリオン座",
            "約束の地": "やくそくのち",

            # 数字・時間
            "0時": "れいじ",
            "12時": "じゅうにじ",
            "40年": "よんじゅうねん",
            "3000年": "さんぜんねん",
            "8分間": "はっぷんかん",

            # 感情表現強化
            "ざわつく": "ざわめく",
            "ポツポツ": "ぽつりぽつり",
        }

        # 感情マーカー
        self.emotion_markers = {
            "焦り": "あせり",
            "葛藤": "かっとう",
            "不安": "ふあん",
            "希望": "きぼう",
            "決意": "けつい"
        }

    def optimize_text(self, text: str) -> str:
        """日本語テキストをTTS最適化"""

        # 1. Unicode正規化
        text = unicodedata.normalize('NFKC', text)

        # 2. 読み方辞書適用
        for word, reading in self.reading_dict.items():
            text = text.replace(word, reading)

        # 3. 句読点最適化（音声の間を調整）
        text = self._optimize_punctuation(text)

        # 4. 数字読み上げ最適化
        text = self._optimize_numbers(text)

        # 5. 感情表現強化
        text = self._enhance_emotions(text)

        # 6. 改行・スペース整理
        text = self._clean_formatting(text)

        return text

    def _optimize_punctuation(self, text: str) -> str:
        """句読点を音声向けに最適化"""

        # 長い間を作る
        text = re.sub(r'。\s*', '。　', text)  # 全角スペースで間を作る
        text = re.sub(r'？\s*', '？　', text)
        text = re.sub(r'！\s*', '！　', text)

        # 短い間
        text = re.sub(r'、\s*', '、', text)

        # 強調のための間
        text = re.sub(r'——', '　——　', text)
        text = re.sub(r'『(.+?)』', '『\\1』', text)  # 強調記号はそのまま

        return text

    def _optimize_numbers(self, text: str) -> str:
        """数字の読み上げを最適化"""

        # 時刻
        text = re.sub(r'(\d{1,2})時', lambda m: f"{self._number_to_japanese(int(m.group(1)))}じ", text)
        text = re.sub(r'(\d{1,2})分', lambda m: f"{self._number_to_japanese(int(m.group(1)))}ふん", text)

        # 年数
        text = re.sub(r'(\d+)年', lambda m: f"{self._number_to_japanese(int(m.group(1)))}ねん", text)

        return text

    def _number_to_japanese(self, num: int) -> str:
        """数字を日本語読みに変換（基本版）"""
        if num == 0: return "れい"
        if num == 1: return "いち"
        if num == 2: return "に"
        if num == 3: return "さん"
        if num == 4: return "よん"
        if num == 5: return "ご"
        if num == 8: return "はち"
        if num == 10: return "じゅう"
        if num == 12: return "じゅうに"
        if num == 40: return "よんじゅう"
        return str(num)  # フォールバック

    def _enhance_emotions(self, text: str) -> str:
        """感情表現を強化"""

        # 感情マーカー適用
        for emotion, reading in self.emotion_markers.items():
            text = text.replace(emotion, reading)

        # 強調表現
        text = re.sub(r'また一人、(.+?)。', r'また一人、　\\1。', text)  # 間を入れる

        return text

    def _clean_formatting(self, text: str) -> str:
        """フォーマット整理"""

        # 改行を適切なスペースに変換
        text = re.sub(r'\n+', '　', text)

        # 連続スペース整理
        text = re.sub(r'　+', '　', text)
        text = re.sub(r'\s+', ' ', text)

        # 前後空白除去
        text = text.strip()

        return text

    def create_voice_settings(self, content_type: str = "narration") -> Dict:
        """コンテンツタイプ別音声設定"""

        settings = {
            "narration": {
                "stability": 0.7,      # 安定した読み上げ
                "similarity_boost": 0.8,
                "style": 0.2,          # 感情控えめ
                "use_speaker_boost": True
            },
            "dialogue": {
                "stability": 0.5,      # 感情豊か
                "similarity_boost": 0.9,
                "style": 0.4,          # 感情強調
                "use_speaker_boost": True
            },
            "emotional": {
                "stability": 0.3,      # 大きく変化
                "similarity_boost": 0.9,
                "style": 0.6,          # 最大感情
                "use_speaker_boost": True
            }
        }

        return settings.get(content_type, settings["narration"])

    def generate_multiple_variations(self, text: str, count: int = 3) -> List[Dict]:
        """異なる設定で複数バリエーション生成"""

        variations = []

        for i in range(count):
            # 微妙に設定を変える
            variation = {
                "text": self.optimize_text(text),
                "settings": {
                    "stability": 0.5 + (i * 0.1),
                    "similarity_boost": 0.8 + (i * 0.05),
                    "style": 0.2 + (i * 0.15),
                    "use_speaker_boost": True
                },
                "variation_id": f"var_{i+1}"
            }
            variations.append(variation)

        return variations


def test_optimizer():
    """最適化テスト"""

    optimizer = JapaneseTTSOptimizer()

    # テスト用テキスト
    test_text = """転職した同期の投稿を見て、焦りを感じたことはありませんか？
深夜0時。オフィスビルの窓に、まだポツポツと明かりが灯っています。
また一人、脱出に成功した。
ようこそ、オリオンの会議室へ。"""

    print("🔧 日本語TTS最適化テスト")
    print("=" * 50)

    print("📝 元テキスト:")
    print(test_text)
    print()

    optimized = optimizer.optimize_text(test_text)
    print("✨ 最適化後:")
    print(optimized)
    print()

    print("🎵 推奨音声設定:")
    settings = optimizer.create_voice_settings("narration")
    for key, value in settings.items():
        print(f"  {key}: {value}")
    print()

    print("🔄 バリエーション生成:")
    variations = optimizer.generate_multiple_variations(test_text, 3)
    for i, var in enumerate(variations, 1):
        print(f"  バリエーション{i}: stability={var['settings']['stability']}")


if __name__ == "__main__":
    test_optimizer()