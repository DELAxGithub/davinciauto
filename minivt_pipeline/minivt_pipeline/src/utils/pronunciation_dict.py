"""
発音辞書システム

固有名詞・外来語・専門用語の正確な読み方を管理し、TTS生成時に発音を制御
オリオンEP1の哲学用語・人名・地名に対応
"""

import json
import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path

@dataclass
class PronunciationEntry:
    """発音辞書エントリー"""
    word: str                    # 対象単語
    reading: str                 # 読み方（ひらがな）
    phoneme: str = ""           # 音素表記（SSML用）
    category: str = "general"   # カテゴリ（人名、地名、専門用語等）
    confidence: float = 1.0     # 確信度（0.0-1.0）
    notes: str = ""             # 備考

class PronunciationDictionary:
    """発音辞書管理システム"""
    
    def __init__(self, dict_file: str = "pronunciation_dict.json"):
        """
        Args:
            dict_file: 辞書ファイルのパス
        """
        self.dict_file = dict_file
        self.entries: Dict[str, PronunciationEntry] = {}
        self._load_dictionary()
        self._initialize_default_entries()
    
    def _load_dictionary(self):
        """辞書ファイルから読み込み"""
        if not Path(self.dict_file).exists():
            return
        
        try:
            with open(self.dict_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for word, entry_data in data.items():
                self.entries[word] = PronunciationEntry(
                    word=entry_data['word'],
                    reading=entry_data['reading'],
                    phoneme=entry_data.get('phoneme', ''),
                    category=entry_data.get('category', 'general'),
                    confidence=entry_data.get('confidence', 1.0),
                    notes=entry_data.get('notes', '')
                )
                
        except Exception as e:
            print(f"⚠️ 発音辞書読み込みエラー: {e}")
    
    def _save_dictionary(self):
        """辞書ファイルに保存"""
        data = {}
        for word, entry in self.entries.items():
            data[word] = {
                'word': entry.word,
                'reading': entry.reading,
                'phoneme': entry.phoneme,
                'category': entry.category,
                'confidence': entry.confidence,
                'notes': entry.notes
            }
        
        with open(self.dict_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _initialize_default_entries(self):
        """オリオンEP1用のデフォルト辞書エントリーを初期化"""
        default_entries = {
            # 哲学者・歴史人物
            "ニーチェ": PronunciationEntry(
                word="ニーチェ", reading="にーちぇ", 
                category="philosopher", confidence=1.0,
                notes="ドイツの哲学者 Friedrich Nietzsche"
            ),
            "フリードリヒ・ニーチェ": PronunciationEntry(
                word="フリードリヒ・ニーチェ", reading="ふりーどりひ・にーちぇ",
                category="philosopher", confidence=1.0
            ),
            "モーセ": PronunciationEntry(
                word="モーセ", reading="もーせ",
                category="historical", confidence=1.0,
                notes="旧約聖書の預言者"
            ),
            "カフカ": PronunciationEntry(
                word="カフカ", reading="かふか",
                category="writer", confidence=1.0,
                notes="フランツ・カフカ"
            ),
            
            # 地名・民族
            "エジプト": PronunciationEntry(
                word="エジプト", reading="えじぷと",
                category="place", confidence=1.0
            ),
            "イスラエル": PronunciationEntry(
                word="イスラエル", reading="いすらえる",
                category="place", confidence=1.0
            ),
            
            # 専門用語・学術用語
            "fMRI": PronunciationEntry(
                word="fMRI", reading="えふえむあーるあい",
                phoneme="ɛf ɛm ɑɹ aɪ",
                category="scientific", confidence=0.9,
                notes="functional Magnetic Resonance Imaging"
            ),
            "扁桃体": PronunciationEntry(
                word="扁桃体", reading="へんとうたい",
                category="scientific", confidence=1.0,
                notes="脳の一部"
            ),
            "コルチゾール": PronunciationEntry(
                word="コルチゾール", reading="こるちぞーる",
                category="scientific", confidence=1.0,
                notes="ストレスホルモン"
            ),
            
            # 書籍・作品名
            "出エジプト記": PronunciationEntry(
                word="出エジプト記", reading="しゅつえじぷとき",
                category="book", confidence=1.0
            ),
            "民数記": PronunciationEntry(
                word="民数記", reading="みんすうき",
                category="book", confidence=1.0
            ),
            "悦ばしき知識": PronunciationEntry(
                word="悦ばしき知識", reading="よろこばしきちしき",
                category="book", confidence=1.0
            ),
            "道徳の系譜": PronunciationEntry(
                word="道徳の系譜", reading="どうとくのけいふ",
                category="book", confidence=1.0
            ),
            
            # 学者・研究者
            "デニス・ルソー": PronunciationEntry(
                word="デニス・ルソー", reading="でにす・るそー",
                category="academic", confidence=0.9
            ),
            "アルベール・O・ハーシュマン": PronunciationEntry(
                word="アルベール・O・ハーシュマン", reading="あるべーる・おー・はーしゅまん",
                category="academic", confidence=0.8
            ),
            
            # 概念・専門用語
            "心理的契約": PronunciationEntry(
                word="心理的契約", reading="しんりてきけいやく",
                category="concept", confidence=1.0
            ),
            "奴隷道徳": PronunciationEntry(
                word="奴隷道徳", reading="どれいどうとく",
                category="concept", confidence=1.0
            ),
            "エクソダス": PronunciationEntry(
                word="エクソダス", reading="えくそだす",
                category="concept", confidence=1.0,
                notes="出エジプト、脱出"
            )
        }
        
        # 既存エントリーがない場合のみ追加
        for word, entry in default_entries.items():
            if word not in self.entries:
                self.entries[word] = entry
        
        # 初期化後に保存
        self._save_dictionary()
    
    def add_entry(self, word: str, reading: str, phoneme: str = "", 
                  category: str = "general", confidence: float = 1.0, notes: str = ""):
        """辞書エントリーを追加"""
        self.entries[word] = PronunciationEntry(
            word=word, reading=reading, phoneme=phoneme,
            category=category, confidence=confidence, notes=notes
        )
        self._save_dictionary()
    
    def get_reading(self, word: str) -> Optional[str]:
        """単語の読み方を取得"""
        entry = self.entries.get(word)
        return entry.reading if entry else None
    
    def get_phoneme(self, word: str) -> Optional[str]:
        """単語の音素表記を取得"""
        entry = self.entries.get(word)
        return entry.phoneme if entry and entry.phoneme else None
    
    def find_matches_in_text(self, text: str) -> List[Tuple[str, PronunciationEntry]]:
        """
        テキスト内の辞書対象単語を検出
        
        Args:
            text: 検索対象テキスト
            
        Returns:
            (単語, 辞書エントリー) のリスト
        """
        matches = []
        
        # 長い単語から順にチェック（部分一致を避けるため）
        sorted_words = sorted(self.entries.keys(), key=len, reverse=True)
        
        for word in sorted_words:
            if word in text:
                matches.append((word, self.entries[word]))
        
        return matches
    
    def apply_pronunciation_to_text(self, text: str, format_type: str = "ssml") -> str:
        """
        テキストに発音情報を適用
        
        Args:
            text: 対象テキスト
            format_type: 出力形式 ("ssml", "phoneme", "reading")
            
        Returns:
            発音情報が適用されたテキスト
        """
        matches = self.find_matches_in_text(text)
        result_text = text
        
        # 長い単語から処理（重複置換回避）
        for word, entry in sorted(matches, key=lambda x: len(x[0]), reverse=True):
            if format_type == "ssml" and entry.phoneme:
                # SSML形式での発音指定
                ssml_phoneme = f'<phoneme alphabet="ipa" ph="{entry.phoneme}">{word}</phoneme>'
                result_text = result_text.replace(word, ssml_phoneme)
            elif format_type == "reading":
                # ひらがな読みで置換
                result_text = result_text.replace(word, entry.reading)
            elif format_type == "phoneme" and entry.phoneme:
                # 音素表記で置換
                result_text = result_text.replace(word, entry.phoneme)
        
        return result_text
    
    def get_category_stats(self) -> Dict[str, int]:
        """カテゴリ別統計を取得"""
        stats = {}
        for entry in self.entries.values():
            category = entry.category
            stats[category] = stats.get(category, 0) + 1
        return stats
    
    def generate_report(self) -> str:
        """発音辞書レポートを生成"""
        report = ["📚 発音辞書レポート"]
        report.append("=" * 40)
        
        # 基本統計
        report.append(f"総エントリー数: {len(self.entries)}")
        
        # カテゴリ別統計
        stats = self.get_category_stats()
        report.append(f"\nカテゴリ別統計:")
        for category, count in sorted(stats.items()):
            report.append(f"  {category}: {count}語")
        
        # 各カテゴリの内容例示
        report.append(f"\n📖 登録単語例:")
        for category in sorted(stats.keys()):
            category_words = [entry.word for entry in self.entries.values() 
                            if entry.category == category][:3]
            report.append(f"  {category}: {', '.join(category_words)}")
        
        return "\n".join(report)

def create_orion_dictionary() -> PronunciationDictionary:
    """オリオンEP1用の発音辞書を作成"""
    return PronunciationDictionary("orion_pronunciation_dict.json")

# テスト・使用例
if __name__ == "__main__":
    print("📚 発音辞書システムテスト")
    
    # オリオンEP1用辞書を作成
    dictionary = create_orion_dictionary()
    
    # レポート表示
    print(dictionary.generate_report())
    
    # テストテキスト（オリオンEP1から抜粋）
    test_text = "19世紀のドイツ。哲学者フリードリヒ・ニーチェは、現代人の精神状態を鋭く分析しました。"
    
    print(f"\n🧪 テストテキスト:")
    print(f"原文: {test_text}")
    
    # マッチする単語を検出
    matches = dictionary.find_matches_in_text(test_text)
    print(f"\n🎯 検出された単語: {len(matches)}語")
    for word, entry in matches:
        print(f"  {word} → {entry.reading} ({entry.category})")
    
    # 発音適用例
    print(f"\n🔊 発音適用結果:")
    reading_text = dictionary.apply_pronunciation_to_text(test_text, "reading")
    print(f"読み: {reading_text}")
    
    # SSML形式（ElevenLabs用）
    ssml_text = dictionary.apply_pronunciation_to_text(test_text, "ssml")
    print(f"SSML: {ssml_text}")