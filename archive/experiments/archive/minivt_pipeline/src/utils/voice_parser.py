import re
import os
from typing import Dict, Tuple, Optional
from dataclasses import dataclass

@dataclass
class VoiceInstruction:
    """
    音声指示情報を格納するデータクラス
    """
    gender: Optional[str] = None  # "male" or "female"
    emotion: Optional[str] = None  # "tired", "whisper", "excited", etc.
    original_text: str = ""
    clean_text: str = ""

class VoiceInstructionParser:
    """
    スクリプト内の音声指示を解析して適切な音声設定を決定するパーサー
    
    対応パターン:
    - （男声・疲れ切った声で）: 男性・疲労
    - （女声・つぶやくように）: 女性・つぶやき
    - 同僚A（女声・つぶやくように）: キャラクター+音声指示
    """
    
    # 音声指示パターン（日本語）
    VOICE_PATTERN = re.compile(r'（([男女])声[・、]?([^）]+)?）')
    CHARACTER_PATTERN = re.compile(r'^([^（]+)（([男女])声[・、]?([^）]+)?）[:：](.+)$')
    
    # 感情と音声設定のマッピング
    EMOTION_SETTINGS = {
        "疲れ切った": {"stability": 0.3, "similarity_boost": 0.7, "style": 0.2},
        "疲れた": {"stability": 0.3, "similarity_boost": 0.7, "style": 0.2},
        "つぶやく": {"stability": 0.4, "similarity_boost": 0.9, "style": 0.1},
        "つぶやき": {"stability": 0.4, "similarity_boost": 0.9, "style": 0.1},
        "興奮": {"stability": 0.2, "similarity_boost": 0.6, "style": 0.7},
        "興奮した": {"stability": 0.2, "similarity_boost": 0.6, "style": 0.7},
        "怒り": {"stability": 0.1, "similarity_boost": 0.5, "style": 0.8},
        "怒った": {"stability": 0.1, "similarity_boost": 0.5, "style": 0.8},
        "悲しい": {"stability": 0.6, "similarity_boost": 0.8, "style": 0.2},
        "悲しみ": {"stability": 0.6, "similarity_boost": 0.8, "style": 0.2},
        "驚き": {"stability": 0.2, "similarity_boost": 0.7, "style": 0.6},
        "驚いた": {"stability": 0.2, "similarity_boost": 0.7, "style": 0.6},
        "落ち着いた": {"stability": 0.8, "similarity_boost": 0.9, "style": 0.1},
        "冷静": {"stability": 0.8, "similarity_boost": 0.9, "style": 0.1},
        "優しい": {"stability": 0.7, "similarity_boost": 0.9, "style": 0.3},
        "優しく": {"stability": 0.7, "similarity_boost": 0.9, "style": 0.3},
    }
    
    def __init__(self):
        """
        VoiceInstructionParser初期化
        環境変数から音声IDを読み込み
        """
        # 環境変数から音声ID取得
        self.default_voice = os.getenv("ELEVENLABS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")
        self.narration_voice = os.getenv("ELEVENLABS_VOICE_ID_NARRATION", self.default_voice)
        self.dialogue_voice = os.getenv("ELEVENLABS_VOICE_ID_DIALOGUE", self.default_voice)
        self.male_voice = os.getenv("ELEVENLABS_VOICE_ID_MALE", self.dialogue_voice)
        self.female_voice = os.getenv("ELEVENLABS_VOICE_ID_FEMALE", self.dialogue_voice)
        
    def parse_voice_instruction(self, text: str) -> VoiceInstruction:
        """
        テキストから音声指示を解析
        
        Args:
            text: 解析対象のテキスト
            
        Returns:
            VoiceInstruction: 解析結果
        """
        instruction = VoiceInstruction(original_text=text)
        
        # キャラクター指定パターンをチェック
        char_match = self.CHARACTER_PATTERN.match(text.strip())
        if char_match:
            character_name = char_match.group(1).strip()
            gender = char_match.group(2)
            emotion_text = char_match.group(3) or ""
            actual_text = char_match.group(4).strip()
            
            instruction.gender = "male" if gender == "男" else "female"
            instruction.emotion = self._extract_emotion(emotion_text)
            instruction.clean_text = actual_text
            return instruction
        
        # 通常の音声指示パターンをチェック
        voice_match = self.VOICE_PATTERN.search(text)
        if voice_match:
            gender = voice_match.group(1)
            emotion_text = voice_match.group(2) or ""
            
            instruction.gender = "male" if gender == "男" else "female"
            instruction.emotion = self._extract_emotion(emotion_text)
            instruction.clean_text = self.VOICE_PATTERN.sub("", text).strip()
            
            # コロンで始まる場合は除去
            if instruction.clean_text.startswith((":", "：")):
                instruction.clean_text = instruction.clean_text[1:].strip()
        else:
            # 音声指示なしの場合
            instruction.clean_text = text.strip()
            
        return instruction
        
    def _extract_emotion(self, emotion_text: str) -> Optional[str]:
        """
        感情表現テキストから感情キーワードを抽出
        
        Args:
            emotion_text: 感情表現テキスト（例: "疲れ切った声で"）
            
        Returns:
            str: 感情キーワード（例: "疲れ切った"）
        """
        if not emotion_text:
            return None
            
        # 「〜で」「〜ように」「〜声」などの語尾を除去
        clean_emotion = emotion_text.replace("声で", "").replace("ように", "").replace("で", "").strip()
        
        # 感情設定に存在するキーワードを検索
        for emotion_key in self.EMOTION_SETTINGS.keys():
            if emotion_key in clean_emotion:
                return emotion_key
                
        # マッチしない場合は元のテキストを返す
        return clean_emotion if clean_emotion else None
        
    def get_voice_id(self, instruction: VoiceInstruction, role: str = "DL") -> str:
        """
        音声指示に基づいて適切な音声IDを取得
        
        Args:
            instruction: 音声指示情報
            role: 基本ロール（"NA" or "DL"）
            
        Returns:
            str: ElevenLabs音声ID
        """
        # 性別指定がある場合
        if instruction.gender == "male":
            return self.male_voice
        elif instruction.gender == "female":
            return self.female_voice
        
        # 性別指定がない場合はロールベース
        if role == "NA":
            return self.narration_voice
        else:
            return self.dialogue_voice
            
    def get_voice_settings(self, instruction: VoiceInstruction) -> Dict[str, float]:
        """
        音声指示に基づいて音声設定を取得
        
        Args:
            instruction: 音声指示情報
            
        Returns:
            Dict: ElevenLabs音声設定
        """
        # デフォルト設定
        default_settings = {
            "stability": 0.5,
            "similarity_boost": 0.8,
            "style": 0.3,
            "use_speaker_boost": True
        }
        
        # 感情に基づく設定調整
        if instruction.emotion and instruction.emotion in self.EMOTION_SETTINGS:
            emotion_settings = self.EMOTION_SETTINGS[instruction.emotion]
            default_settings.update(emotion_settings)
            
        return default_settings
        
    def process_script_line(self, text: str, role: str) -> Tuple[str, str, Dict[str, float]]:
        """
        スクリプト行を処理して音声生成に必要な情報を取得
        
        Args:
            text: スクリプトテキスト
            role: 基本ロール（"NA" or "DL"）
            
        Returns:
            Tuple[str, str, Dict]: (clean_text, voice_id, voice_settings)
        """
        instruction = self.parse_voice_instruction(text)
        voice_id = self.get_voice_id(instruction, role)
        voice_settings = self.get_voice_settings(instruction)
        
        return instruction.clean_text, voice_id, voice_settings