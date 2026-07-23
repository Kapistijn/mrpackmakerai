from __future__ import annotations
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.db.session import AsyncSessionLocal
from app.models.project import Project
from app.schemas.mod import ModEntry
from app.services.pack_intelligence import quality_report, synergy_report, performance_estimate, reputation_report, variant_plan, natural_language_plan
router = APIRouter()
async def _mods(project_id: int) -> tuple[Project, list[ModEntry]]:
    async with AsyncSessionLocal() as db:
        project = await db.get(Project, project_id)
        if not project: raise HTTPException(status_code=404, detail="Project not found")
        return project, [ModEntry.model_validate(item) for item in json.loads(project.mods_json or "[]")]
@router.get('/{project_id}')
async def insights(project_id: int):
    project, mods = await _mods(project_id)
    return {"quality": quality_report(mods), "synergy": synergy_report(mods), "performance": performance_estimate(mods, ram_gb=project.target_ram_gb, fps_target=project.target_fps, shader_support=project.shader_support), "reputation": [reputation_report(mod) for mod in mods], "variants": variant_plan(project.name, mods)}
class EditRequest(BaseModel): prompt: str
@router.post('/{project_id}/natural-language')
async def natural_language(project_id: int, request: EditRequest):
    _project, mods = await _mods(project_id)
    return natural_language_plan(request.prompt, mods)
@router.post('/{project_id}/update-plan')
async def update_plan(project_id: int):
    project, mods = await _mods(project_id)
    return {"project_id": project_id, "backup_required": True, "approval_required": True, "steps": ["create backup", "check newer versions", "resolve dependencies", "run compatibility checks", "show diff", "apply only after approval"], "current_mods": len(mods), "minecraft_version": project.minecraft_version, "loader": project.loader}
