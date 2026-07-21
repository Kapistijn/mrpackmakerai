"""Project CRUD routes."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.enums import ProjectStatus
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectListItem, ProjectResponse, ProjectUpdate

router = APIRouter()


def _project_to_response(project: Project) -> ProjectResponse:
    mods: list[dict[str, Any]] = json.loads(project.mods_json or "[]")
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        minecraft_version=project.minecraft_version,
        loader=project.loader_enum(),
        theme=project.theme_enum(),
        theme_custom=project.theme_custom,
        difficulty=project.difficulty,
        performance_preference=project.performance_preference,
        generation_prompt=project.generation_prompt,
        status=project.status_enum(),
        mods=mods,
        resolved_loader_version=project.resolved_loader_version,
        ai_summary=project.ai_summary,
        mrpack_path=project.mrpack_path,
        settings_locked=project.settings_locked,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.get("", response_model=list[ProjectListItem])
async def list_projects(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).order_by(Project.updated_at.desc()))
    projects = result.scalars().all()
    return [
        ProjectListItem(
            id=p.id,
            name=p.name,
            minecraft_version=p.minecraft_version,
            loader=p.loader_enum(),
            status=p.status_enum(),
            created_at=p.created_at,
            updated_at=p.updated_at,
        )
        for p in projects
    ]


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(body: ProjectCreate, db: AsyncSession = Depends(get_db)):
    project = Project(
        name=body.name,
        description=body.description,
        minecraft_version=body.minecraft_version,
        loader=body.loader.value,
        theme=body.theme.value,
        theme_custom=body.theme_custom,
        difficulty=body.difficulty.value,
        performance_preference=body.performance_preference.value,
        generation_prompt=body.generation_prompt or body.description,
        status=ProjectStatus.DRAFT.value,
        mods_json="[]",
        settings_locked=True,
    )
    db.add(project)
    await db.flush()
    await db.refresh(project)
    return _project_to_response(project)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: int, db: AsyncSession = Depends(get_db)):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found", headers={"X-Error-Code": "not_found"})
    return _project_to_response(project)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    body: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if body.generation_prompt is not None:
        project.generation_prompt = body.generation_prompt
        project.mrpack_path = None
    if body.mods is not None:
        project.mods_json = json.dumps([mod.model_dump(mode="json") for mod in body.mods])
        project.mrpack_path = None
        project.status = ProjectStatus.REVIEW.value

    await db.flush()
    await db.refresh(project)
    return _project_to_response(project)


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: int, db: AsyncSession = Depends(get_db)):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    await db.delete(project)
