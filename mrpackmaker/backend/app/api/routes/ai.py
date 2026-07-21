"""AI generation routes with SSE progress."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.db.session import get_db
from app.models.enums import ProjectStatus
from app.models.project import Project
from app.services.ai_orchestrator import orchestrator
from app.services.ai_provider import create_ai_provider

router = APIRouter()


@router.post("/generate/{project_id}")
async def start_generation(project_id: int, db: AsyncSession = Depends(get_db)):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.status == ProjectStatus.GENERATING.value or orchestrator.is_active(project_id):
        raise HTTPException(status_code=409, detail="Generation already in progress")

    provider = create_ai_provider()
    try:
        connection = await provider.connection_status()
    finally:
        await provider.close()
    if not connection.reachable:
        raise HTTPException(
            status_code=503,
            detail=connection.detail or "Configured AI provider is unavailable",
        )

    project.status = ProjectStatus.GENERATING.value
    await db.commit()
    orchestrator.start_generation(project_id)

    return {"status": "started", "project_id": project_id}


@router.get("/generate/{project_id}/stream")
async def stream_generation(project_id: int):
    async def event_generator():
        async for event in orchestrator.stream_events(project_id):
            yield {
                "event": "progress",
                "data": json.dumps(event.model_dump()),
            }
        yield {"event": "end", "data": "{}"}

    return EventSourceResponse(event_generator())


@router.post("/generate/{project_id}/cancel")
async def cancel_generation(project_id: int, db: AsyncSession = Depends(get_db)):
    cancelled = orchestrator.cancel(project_id)
    if cancelled:
        project = await db.get(Project, project_id)
        if project:
            project.status = ProjectStatus.DRAFT.value
            await db.flush()
    return {"cancelled": cancelled}
