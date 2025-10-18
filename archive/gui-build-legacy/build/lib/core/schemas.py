from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Script(BaseModel):
    raw_text: str = ""
    version: int = 1
    # Optional: segmented structure produced by LLM decomposition
    segments: Optional[List[Dict[str, Any]]] = None


class Timing(BaseModel):
    tStart: float = 0.0
    tEnd: float = 0.0
    tDur: float = 0.0


class LineItem(BaseModel):
    id: str
    index: int
    role: str = "NA"  # NA, DL, Q, etc
    character: str = "-"
    text: str
    tags: List[str] = Field(default_factory=list)
    locked: bool = False
    timing: Timing = Field(default_factory=Timing)
    # Arbitrary status/notes to retain UI compatibility
    status: Dict[str, Any] = Field(default_factory=dict)
    notes: str = ""


class Project(BaseModel):
    id: str
    title: str
    root_dir: str
    fps: int = 30
    language: str = "ja"
    script: Script = Field(default_factory=Script)
    # Flattened lines for downstream workers
    lines: List[LineItem] = Field(default_factory=list)


class Task(BaseModel):
    id: str
    type: str  # narration|telop|storyboard|bgm|se|cg|assemble|script_decompose
    input_refs: List[str] = Field(default_factory=list)  # LineItem/Artifact ids
    status: str = "pending"  # pending|in_progress|needs_review|done|error
    assignee: Optional[str] = None
    params: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


class Artifact(BaseModel):
    id: str
    type: str  # audio_narr|telop_csv|storyboard_json|bgm_track|se_track|timeline_xml|...
    path: str
    meta: Dict[str, Any] = Field(default_factory=dict)
    source_task_id: Optional[str] = None


# NOTE: RowData (backend.models) <-> LineItem 変換は、
# 依存関係を避けるためアダプタ層で実装してください。
# 例:
# def rowdata_to_lineitem(row: RowData) -> LineItem: ...
# def lineitem_to_rowdata(item: LineItem) -> RowData: ...

