"""Modpack generation and download routes."""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.enums import ProjectStatus
from app.models.project import Project
from app.services.mrpack import MrpackGenerator
from app.services.mrpack_validation import MrpackValidationError
from app.config import config

router = APIRouter()


@router.post("/{project_id}/generate")
async def generate_modpack(project_id: int, db: AsyncSession = Depends(get_db)):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        output_path = MrpackGenerator().generate(project)
    except MrpackValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail={"message": "Modpack cannot be exported until validation errors are fixed.", "errors": [issue.message for issue in exc.issues]},
        ) from exc

    project.mrpack_path = str(output_path)
    project.status = ProjectStatus.EXPORTED.value
    await db.flush()

    return {
        "status": "generated",
        "path": str(output_path),
        "filename": output_path.name,
    }


@router.get("/{project_id}/download")
async def download_modpack(project_id: int, db: AsyncSession = Depends(get_db)):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if not project.mrpack_path:
        raise HTTPException(status_code=404, detail="No modpack generated yet. Run generate first.")

    path = Path(project.mrpack_path).resolve()
    output_dir = config.output_dir.resolve()
    if output_dir not in path.parents:
        raise HTTPException(status_code=404, detail="Modpack file is outside the output directory")
    if not path.exists():
        raise HTTPException(status_code=404, detail="Modpack file not found on disk")

    return FileResponse(
        path=str(path),
        filename=path.name,
        media_type="application/zip",
    )
