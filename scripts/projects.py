from __future__ import annotations

import uuid
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel

from backend.adapters import rows_to_lineitems, lineitems_to_rows
from core.schemas import Project, LineItem

router = APIRouter(
    prefix="/api/v2/projects",
    tags=["projects"],
)

PROJECTS_ROOT = Path("projects")


class ProjectMetadata(BaseModel):
    id: str
    title: str
    modified_at: float


@router.post("/", response_model=Project)
async def create_project(title: str = Body(..., embed=True)):
    """
    新しいプロジェクトを作成し、初期マニフェストを保存する
    """
    project_id = f"proj-{uuid.uuid4().hex[:12]}"
    project_dir = PROJECTS_ROOT / project_id
    try:
        project_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Failed to create project directory: {e}")

    project = Project(
        id=project_id,
        title=title,
        root_dir=str(project_dir.resolve()),
    )

    manifest_path = project_dir / "project.json"
    manifest_path.write_text(project.model_dump_json(indent=2), encoding="utf-8")

    return project


@router.get("/{project_id}", response_model=Project)
async def get_project(project_id: str):
    """
    指定されたプロジェクトIDのマニフェストを読み込む
    旧フォーマット(dataキー)からの変換もサポート
    """
    project_dir = PROJECTS_ROOT / project_id
    manifest_path = project_dir / "project.json"

    if not manifest_path.exists():
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")

    try:
        import json
        data = json.loads(manifest_path.read_text(encoding="utf-8"))

        # 旧フォーマットの互換性対応
        if "data" in data and "lines" not in data:
            # RowData[] 形式のデータを LineItem[] に変換
            from backend.models import RowData
            rows = [RowData(**r) for r in data["data"]]
            line_items = rows_to_lineitems(rows)
            data["lines"] = [item.model_dump() for item in line_items]
            del data["data"] # 古いキーは削除

        project = Project(**data)
        return project
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load or parse project: {e}")


@router.put("/{project_id}", response_model=Project)
async def save_project(project_id: str, project: Project):
    """
    プロジェクトの変更をマニフェストに保存する
    """
    project_dir = PROJECTS_ROOT / project_id
    manifest_path = project_dir / "project.json"

    if not project_dir.exists():
        raise HTTPException(status_code=404, detail=f"Project directory for '{project_id}' not found.")

    try:
        # 常に新しいスキーマで保存
        manifest_path.write_text(project.model_dump_json(indent=2), encoding="utf-8")
        return project
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save project: {e}")