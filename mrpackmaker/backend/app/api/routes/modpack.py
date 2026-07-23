"""Modpack generation, dependency repair, and download routes."""
import json
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import config
from app.db.session import get_db
from app.models.enums import LoaderType, ProjectStatus
from app.models.project import Project
from app.schemas.mod import ModEntry
from app.services.dependency_resolver import DependencyResolver
from app.services.mod_resolver import ModResolver
from app.services.mrpack import MrpackGenerator
from app.services.mrpack_validation import MrpackValidationError
from app.services.source_registry import create_default_registry
router = APIRouter()

async def repair_project_dependencies(project: Project, db: AsyncSession) -> dict[str, int]:
    selected = [ModEntry.model_validate(raw) for raw in json.loads(project.mods_json or "[]")]
    registry = create_default_registry(); resolver = ModResolver(registry=registry)
    try:
        refreshed = []
        for item in selected:
            try: detail = await resolver.resolve_mod(item.source, item.id, project.minecraft_version, LoaderType(project.loader))
            except Exception: detail = None
            refreshed.append(detail or item)
        result = await DependencyResolver(resolver).resolve_pack(refreshed, project.minecraft_version, LoaderType(project.loader))
        if result.failures:
            raise HTTPException(status_code=422, detail={"message": "Dependency repair failed after 5 passes.", "errors": [failure.message() for failure in result.failures]})
        repaired = list(result.mods)
        if len(repaired) != len(selected) or any(a.model_dump() != b.model_dump() for a, b in zip(repaired, selected)):
            project.mods_json = json.dumps([mod.model_dump(mode="json") for mod in repaired]); project.mrpack_path = None; project.status = ProjectStatus.REVIEW.value; await db.flush()
        return {"mods": len(repaired), "optional_added": result.optional_added, "passes": result.passes}
    finally: await resolver.close()

@router.post("/{project_id}/generate")
async def generate_modpack(project_id: int, db: AsyncSession = Depends(get_db)):
    project = await db.get(Project, project_id)
    if not project: raise HTTPException(status_code=404, detail="Project not found")
    dependency_status = await repair_project_dependencies(project, db)
    try: output_path = MrpackGenerator().generate(project)
    except MrpackValidationError as exc: raise HTTPException(status_code=422, detail={"message": "Modpack cannot be exported until validation errors are fixed.", "errors": [issue.message for issue in exc.issues]}) from exc
    project.mrpack_path = str(output_path); project.status = ProjectStatus.EXPORTED.value; await db.flush()
    return {"status": "generated", "path": str(output_path), "filename": output_path.name, "dependency_status": dependency_status}

@router.get("/{project_id}/download")
async def download_modpack(project_id: int, db: AsyncSession = Depends(get_db)):
    project = await db.get(Project, project_id)
    if not project: raise HTTPException(status_code=404, detail="Project not found")
    if not project.mrpack_path: raise HTTPException(status_code=404, detail="No modpack generated yet. Run generate first.")
    path = Path(project.mrpack_path).resolve(); output_dir = config.output_dir.resolve()
    if output_dir not in path.parents or not path.exists(): raise HTTPException(status_code=404, detail="Modpack file not found")
    return FileResponse(path=str(path), filename=path.name, media_type="application/zip")
