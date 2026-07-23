"""Project CRUD routes and loader metadata."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import config
from app.db.session import get_db
from app.models.enums import LoaderType, ProjectStatus
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectListItem, ProjectResponse, ProjectUpdate
from app.services.loader_metadata import LoaderMetadataError, OfficialLoaderResolver

router = APIRouter()


def _project_to_response(project: Project) -> ProjectResponse:
    mods: list[dict[str, Any]] = json.loads(project.mods_json or "[]")
    return ProjectResponse(
        id=project.id, name=project.name, description=project.description,
        minecraft_version=project.minecraft_version, loader=project.loader_enum(),
        loader_version=project.loader_version, theme=project.theme_enum(),
        theme_custom=project.theme_custom, difficulty=project.difficulty,
        performance_preference=project.performance_preference,
        generation_prompt=project.generation_prompt, minimum_mods=project.minimum_mods,
        maximum_mods=project.maximum_mods, minimum_downloads=project.minimum_downloads,
        status=project.status_enum(), mods=mods,
        resolved_loader_version=project.resolved_loader_version,
        ai_summary=project.ai_summary, mrpack_path=project.mrpack_path,
        settings_locked=project.settings_locked, created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.get("/loader-versions")
async def loader_versions(mc: str = Query(..., min_length=3, max_length=32), loader: LoaderType = Query(...)):
    try:
        versions = await OfficialLoaderResolver().list_versions(loader, mc)
    except LoaderMetadataError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {
        "minecraft_version": mc,
        "loader": loader.value,
        "source": versions[0].source if versions else None,
        "versions": [{"id": f"{loader.value}:{item.version}", "version": item.version, "type": "release" if item.stable else "beta", "stable": item.stable} for item in versions],
    }


@router.get("", response_model=list[ProjectListItem])
async def list_projects(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).order_by(Project.updated_at.desc()))
    return [ProjectListItem(id=p.id, name=p.name, minecraft_version=p.minecraft_version, loader=p.loader_enum(), status=p.status_enum(), created_at=p.created_at, updated_at=p.updated_at) for p in result.scalars().all()]


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(body: ProjectCreate, db: AsyncSession = Depends(get_db)):
    project = Project(name=body.name, description=body.description, minecraft_version=body.minecraft_version, loader=body.loader.value, loader_version=body.loader_version, theme=body.theme.value, theme_custom=body.theme_custom, difficulty=body.difficulty.value, performance_preference=body.performance_preference.value, generation_prompt=body.generation_prompt or body.description, minimum_mods=body.minimum_mods, maximum_mods=body.maximum_mods, minimum_downloads=body.minimum_downloads, status=ProjectStatus.DRAFT.value, mods_json="[]", settings_locked=True)
    db.add(project)
    await db.flush(); await db.refresh(project)
    return _project_to_response(project)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: int, db: AsyncSession = Depends(get_db)):
    project = await db.get(Project, project_id)
    if not project: raise HTTPException(status_code=404, detail="Project not found", headers={"X-Error-Code": "not_found"})
    return _project_to_response(project)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: int, body: ProjectUpdate, db: AsyncSession = Depends(get_db)):
    project = await db.get(Project, project_id)
    if not project: raise HTTPException(status_code=404, detail="Project not found")
    if body.generation_prompt is not None: project.generation_prompt = body.generation_prompt; project.mrpack_path = None
    if body.loader_version is not None: project.loader_version = body.loader_version.strip() or None; project.resolved_loader_version = None; project.mrpack_path = None
    if body.minimum_mods is not None: project.minimum_mods = body.minimum_mods; project.mrpack_path = None
    if body.maximum_mods is not None: project.maximum_mods = body.maximum_mods; project.mrpack_path = None
    if body.minimum_downloads is not None: project.minimum_downloads = body.minimum_downloads; project.mrpack_path = None
    if project.minimum_mods and project.maximum_mods and project.minimum_mods > project.maximum_mods:
        raise HTTPException(status_code=422, detail="minimum_mods cannot exceed maximum_mods")
    if body.mods is not None: project.mods_json = json.dumps([mod.model_dump(mode="json") for mod in body.mods]); project.mrpack_path = None; project.status = ProjectStatus.REVIEW.value
    await db.flush(); await db.refresh(project)
    return _project_to_response(project)


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: int, db: AsyncSession = Depends(get_db)):
    project = await db.get(Project, project_id)
    if not project: raise HTTPException(status_code=404, detail="Project not found")
    if project.mrpack_path:
        path = Path(project.mrpack_path).resolve(); output_dir = config.output_dir.resolve()
        if output_dir in path.parents and path.exists(): path.unlink(missing_ok=True)
    await db.delete(project)
