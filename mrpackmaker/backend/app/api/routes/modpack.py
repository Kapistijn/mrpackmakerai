"""Modpack generation, dependency repair, and download routes."""
import json
from pathlib import Path
from fastapi import APIRouter,Depends,HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import config
from app.db.session import get_db
from app.models.enums import ProjectStatus
from app.models.project import Project
from app.schemas.mod import ModEntry
from app.services.dependency_repair import repair_project_dependencies
from app.services.intent_analysis import analyze_intent
from app.services.mrpack import MrpackGenerator
from app.services.mrpack_validation import MrpackValidationError
from app.services.self_check import verify_requirements
router=APIRouter()
def _enforce_requirements(project:Project)->None:
 if (project.ai_strictness or 'balanced').strip().casefold()!='strict':return
 intent=analyze_intent(project.generation_prompt or project.description or '',theme=project.theme)
 if not intent.categories:return
 mods=[ModEntry.model_validate(raw) for raw in json.loads(project.mods_json or '[]')];check=verify_requirements(mods,intent)
 if not check.complete:raise HTTPException(status_code=422,detail={'message':'Pack does not yet satisfy all requested requirements (strict mode).','missing':list(check.missing),'satisfied':list(check.satisfied)})
@router.post('/{project_id}/generate')
async def generate_modpack(project_id:int,db:AsyncSession=Depends(get_db)):
 project=await db.get(Project,project_id)
 if not project:raise HTTPException(status_code=404,detail='Project not found')
 status=await repair_project_dependencies(project,db);_enforce_requirements(project)
 try:output=MrpackGenerator().generate(project)
 except MrpackValidationError as exc:raise HTTPException(status_code=422,detail={'message':'Modpack cannot be exported after dependency repair.','errors':[i.message for i in exc.issues],'dependency_status':status}) from exc
 project.mrpack_path=str(output);project.status=ProjectStatus.EXPORTED.value;await db.flush();return {'status':'generated','path':str(output),'filename':output.name,'dependency_status':status}
@router.get('/{project_id}/download')
async def download_modpack(project_id:int,db:AsyncSession=Depends(get_db)):
 project=await db.get(Project,project_id)
 if not project:raise HTTPException(status_code=404,detail='Project not found')
 if not project.mrpack_path:raise HTTPException(status_code=404,detail='No modpack generated yet. Run generate first.')
 path=Path(project.mrpack_path).resolve();out=config.output_dir.resolve()
 if out not in path.parents or not path.exists():raise HTTPException(status_code=404,detail='Modpack file not found')
 return FileResponse(path=str(path),filename=path.name,media_type='application/zip')