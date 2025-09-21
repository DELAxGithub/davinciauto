from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field


router = APIRouter(prefix="/api/projects", tags=["projects"])


class ProjectSavePayload(BaseModel):
    project_dir: str = Field(..., description="Absolute path to the project directory")
    project: Dict[str, Any] = Field(..., description="Project manifest JSON object")
    filename: str = Field("project.json", description="Target filename inside project_dir")


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {path}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read JSON: {e}")


def _write_json(path: Path, obj: Dict[str, Any]) -> None:
    try:
        _ensure_dir(path.parent)
        with path.open("w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to write JSON: {e}")


@router.post("/save")
def save_project(payload: ProjectSavePayload):  # type: ignore
    """
    Save a project manifest JSON to the specified project folder.

    Accepts any JSON shape for forward-compatibility (legacy `{name,savedAt,data}` or full manifest).
    """
    base = Path(payload.project_dir).expanduser().resolve()
    if not str(base):
        raise HTTPException(status_code=400, detail="Invalid project_dir")
    if not base.exists():
        # Create directory if missing
        _ensure_dir(base)
    target = base / (payload.filename or "project.json")
    _write_json(target, payload.project)
    return {"ok": True, "path": str(target)}


@router.get("/load")
def load_project(project_dir: str = Query(..., description="Absolute path of project folder"),
                 filename: str = Query("project.json", description="Filename inside project folder")):
    """
    Load a project manifest JSON from the specified project folder.
    """
    base = Path(project_dir).expanduser().resolve()
    if not base.exists():
        raise HTTPException(status_code=404, detail=f"Directory not found: {base}")
    path = base / (filename or "project.json")
    data = _read_json(path)
    return {"ok": True, "project": data, "path": str(path)}

