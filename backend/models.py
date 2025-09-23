from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal

class RowData(BaseModel):
    """
    テーブルの各行を表すデータモデル
    llm_workspace.htmlのJavaScriptオブジェクトに対応
    """
    sel: bool = True
    line: int
    role: str = "NA"
    character: str = "-"
    original: str
    follow: str = ""
    narr: str = ""
    storyText: str = ""
    storyKeywords: str = ""
    annot: str = ""
    bgm: str = ""
    se: str = ""
    rate: float = 1.0
    locked: bool = False
    notes: str = ""
    status: Dict[str, Any] = {}
    tDur: float = 0.0
    tStart: float = 0.0
    tEnd: float = 0.0

class LLMParams(BaseModel):
    """LLM生成時のパラメータ"""
    provider: str = "mock"
    model: str = "gpt-4o-mini"
    temperature: float = 0.7

class LLMGenerateRequest(BaseModel):
    """LLM生成リクエスト"""
    task: str
    row: RowData
    params: LLMParams

class TimelineRebuildRequest(BaseModel):
    """タイムライン再構築リクエスト"""
    rows: List[RowData]
    gap_ms: int = 200
    offset_ms: int = 0

class SrtExportRequest(BaseModel):
    """SRT書き出しリクエスト"""
    rows: List[RowData]
    source: str = "follow"
    offset_ms: int = 0

class TTSRequest(BaseModel):
    """音声合成リクエスト"""
    text: str
    provider: Literal["azure"] = "azure"
    voice_id: Optional[str] = None
    azure_style: Optional[str] = None
    azure_role: Optional[str] = None
    speaking_rate: Optional[float] = None
