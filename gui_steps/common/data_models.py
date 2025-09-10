"""
Data models for GUI workflow
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
import json
from pathlib import Path

@dataclass
class ScriptLine:
    """単一の脚本行"""
    role: str  # "NA" or "DL"
    text: str  # セリフ内容
    character: Optional[str] = None  # キャラクター名（DLの場合）
    voice_instruction: Optional[str] = None  # 音声指示（男声・疲れ切った声で）
    voice_id: Optional[str] = None  # 設定された音声ID
    voice_settings: Dict[str, Any] = field(default_factory=dict)  # 音声設定
    line_number: int = 0  # 行番号
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "text": self.text,
            "character": self.character,
            "voice_instruction": self.voice_instruction,
            "voice_id": self.voice_id,
            "voice_settings": self.voice_settings,
            "line_number": self.line_number
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScriptLine':
        return cls(**data)

@dataclass 
class Character:
    """キャラクター設定"""
    name: str
    voice_id: str
    gender: Optional[str] = None  # "male" or "female"
    description: str = ""
    voice_settings: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "voice_id": self.voice_id,
            "gender": self.gender,
            "description": self.description,
            "voice_settings": self.voice_settings
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Character':
        return cls(**data)

@dataclass
class Project:
    """プロジェクト管理"""
    name: str
    script_text: str = ""
    script_lines: List[ScriptLine] = field(default_factory=list)
    characters: List[Character] = field(default_factory=list)
    project_path: Optional[Path] = None
    
    # ステップ完了状態
    step1_completed: bool = False  # スクリプト編集
    step2_completed: bool = False  # TTS生成
    step3_completed: bool = False  # 字幕調整
    step4_completed: bool = False  # DaVinci出力
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "script_text": self.script_text,
            "script_lines": [line.to_dict() for line in self.script_lines],
            "characters": [char.to_dict() for char in self.characters],
            "project_path": str(self.project_path) if self.project_path else None,
            "step1_completed": self.step1_completed,
            "step2_completed": self.step2_completed,
            "step3_completed": self.step3_completed,
            "step4_completed": self.step4_completed
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Project':
        project = cls(
            name=data["name"],
            script_text=data.get("script_text", ""),
            project_path=Path(data["project_path"]) if data.get("project_path") else None,
            step1_completed=data.get("step1_completed", False),
            step2_completed=data.get("step2_completed", False),
            step3_completed=data.get("step3_completed", False),
            step4_completed=data.get("step4_completed", False)
        )
        
        # Convert script lines
        project.script_lines = [
            ScriptLine.from_dict(line_data) 
            for line_data in data.get("script_lines", [])
        ]
        
        # Convert characters
        project.characters = [
            Character.from_dict(char_data)
            for char_data in data.get("characters", [])
        ]
        
        return project
    
    def save_to_file(self, filepath: Path):
        """プロジェクトファイルに保存"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
    
    @classmethod
    def load_from_file(cls, filepath: Path) -> 'Project':
        """プロジェクトファイルから読み込み"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)

@dataclass
class TTSResult:
    """TTS生成結果"""
    line_number: int
    audio_file_path: Path
    duration: float
    success: bool
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "line_number": self.line_number,
            "audio_file_path": str(self.audio_file_path),
            "duration": self.duration,
            "success": self.success,
            "error_message": self.error_message
        }