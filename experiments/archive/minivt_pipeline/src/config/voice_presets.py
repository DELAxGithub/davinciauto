"""
音声品質プリセット設定

ElevenLabs V3モデル用の用途別最適化設定
"""

# 音声プリセット定義
VOICE_PRESETS = {
    "narration": {
        "name": "ナレーション用",
        "description": "明瞭性重視、教養番組向け",
        "settings": {
            "stability": 0.7,
            "similarity_boost": 0.9,
            "style": 0.2,
            "use_speaker_boost": True
        }
    },
    "dialogue": {
        "name": "対話用",
        "description": "自然性重視、キャラクター会話向け",
        "settings": {
            "stability": 0.5,
            "similarity_boost": 0.8,
            "style": 0.4,
            "use_speaker_boost": True
        }
    },
    "emotional": {
        "name": "感情表現用",
        "description": "表現力重視、ドラマティック演出向け",
        "settings": {
            "stability": 0.3,
            "similarity_boost": 0.7,
            "style": 0.6,
            "use_speaker_boost": True
        }
    },
    "documentary": {
        "name": "ドキュメンタリー用",
        "description": "権威性重視、落ち着いた解説向け",
        "settings": {
            "stability": 0.8,
            "similarity_boost": 0.9,
            "style": 0.1,
            "use_speaker_boost": True
        }
    },
    "commercial": {
        "name": "CM用",
        "description": "親しみやすさ重視、商品紹介向け",
        "settings": {
            "stability": 0.6,
            "similarity_boost": 0.8,
            "style": 0.5,
            "use_speaker_boost": True
        }
    }
}

class VoicePresetManager:
    """
    音声プリセット管理クラス
    """
    
    def __init__(self):
        self.presets = VOICE_PRESETS
        
    def get_preset(self, preset_name: str) -> dict:
        """
        プリセット設定を取得
        
        Args:
            preset_name: プリセット名
            
        Returns:
            dict: 音声設定辞書
            
        Raises:
            KeyError: 存在しないプリセット名の場合
        """
        if preset_name not in self.presets:
            available = ", ".join(self.presets.keys())
            raise KeyError(f"プリセット '{preset_name}' が見つかりません。利用可能: {available}")
            
        return self.presets[preset_name]["settings"].copy()
        
    def list_presets(self) -> dict:
        """
        利用可能なプリセット一覧を取得
        
        Returns:
            dict: プリセット名とその説明
        """
        return {
            name: {
                "name": preset["name"], 
                "description": preset["description"]
            }
            for name, preset in self.presets.items()
        }
        
    def get_preset_info(self, preset_name: str) -> dict:
        """
        プリセットの詳細情報を取得
        
        Args:
            preset_name: プリセット名
            
        Returns:
            dict: プリセット詳細情報
        """
        if preset_name not in self.presets:
            available = ", ".join(self.presets.keys())
            raise KeyError(f"プリセット '{preset_name}' が見つかりません。利用可能: {available}")
            
        return self.presets[preset_name].copy()
        
    def create_custom_preset(self, name: str, description: str, settings: dict) -> None:
        """
        カスタムプリセットを追加
        
        Args:
            name: プリセット名
            description: プリセット説明
            settings: 音声設定
        """
        required_keys = {"stability", "similarity_boost", "style", "use_speaker_boost"}
        if not required_keys.issubset(settings.keys()):
            missing = required_keys - settings.keys()
            raise ValueError(f"必須パラメータが不足: {missing}")
            
        self.presets[name] = {
            "name": description,
            "description": description,
            "settings": settings.copy()
        }
        
    def apply_preset_to_role(self, preset_name: str, role: str) -> dict:
        """
        ロール別にプリセットを適用
        
        Args:
            preset_name: プリセット名
            role: ロール ("NA" or "DL")
            
        Returns:
            dict: 調整された音声設定
        """
        base_settings = self.get_preset(preset_name)
        
        # ロール別微調整
        if role == "NA":
            # ナレーションは安定性を少し上げる
            base_settings["stability"] = min(1.0, base_settings["stability"] + 0.1)
        elif role == "DL":
            # 対話は表現力を少し上げる
            base_settings["style"] = min(1.0, base_settings["style"] + 0.1)
            
        return base_settings