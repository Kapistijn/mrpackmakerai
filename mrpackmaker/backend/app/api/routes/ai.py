"""AI generation routes with SSE progress."""
from __future__ import annotations
import json
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse
from app.config import config
from app.db.session import get_db
from app.models.enums import ProjectStatus
from app.models.project import Project
from app.services.ai_orchestrator import orchestrator
from app.services.ai_provider import create_ai_provider
from app.services.compatibility import CompatibilityService
from app.services.curseforge import CurseForgeClient
from app.services.dependency_repair import repair_project_dependencies
from app.services.modrinth import ModrinthClient
from app.services.pack_analysis import persist_analysis
from app.services.source_registry import create_default_registry
from app.services.worker_generation import WorkerGenerationEngine
router=APIRouter()
class WorkerGenerationRequest(BaseModel):
 workers:int=Field(default=4,ge=2,le=24)
 target_mods:int=Field(default=40,ge=1,le=500)
async def _begin_generation(project:Project,db:AsyncSession,*,use_ai:bool)->None:
 project.status=ProjectStatus.GENERATING.value;await db.commit()
 try:orchestrator.start_generation(project.id,use_ai=use_ai)
 except RuntimeError as exc:project.status=ProjectStatus.DRAFT.value;await db.commit();raise HTTPException(status_code=409,detail=str(exc)) from exc
@router.post('/generate/{project_id}')
async def start_generation(project_id:int,db:AsyncSession=Depends(get_db)):
 project=await db.get(Project,project_id)
 if not project:raise HTTPException(status_code=404,detail='Project not found')
 if project.status==ProjectStatus.GENERATING.value or orchestrator.is_active(project_id):raise HTTPException(status_code=409,detail='Generation already in progress')
 provider=create_ai_provider()
 try:connection=await provider.connection_status()
 finally:await provider.close()
 if not connection.reachable:raise HTTPException(status_code=503,detail=(connection.detail or 'Configured AI provider is unavailable')+' You can still use Quick generate to build a pack without AI.')
 await _begin_generation(project,db,use_ai=True);return {'status':'started','project_id':project_id,'mode':'ai'}
@router.post('/generate/{project_id}/workers')
async def start_worker_generation(project_id:int,body:WorkerGenerationRequest,db:AsyncSession=Depends(get_db)):
 project=await db.get(Project,project_id)
 if not project:raise HTTPException(status_code=404,detail='Project not found')
 if project.status==ProjectStatus.GENERATING.value or orchestrator.is_active(project_id):raise HTTPException(status_code=409,detail='Generation already in progress')
 registry=create_default_registry();engine=WorkerGenerationEngine(registry)
 try:
  result,rounds=await engine.generate(project.generation_prompt or project.description,project.minecraft_version,project.loader_enum(),body.workers,body.target_mods)
  project.mods_json=json.dumps([mod.model_dump(mode='json') for mod in result.mods])
  repair_status=await repair_project_dependencies(project,db)
  compatibility=CompatibilityService(ModrinthClient(config.apis.modrinth_key),CurseForgeClient(config.apis.curseforge_key))
  try:compatibility_report=await compatibility.check_project(project)
  finally:await compatibility.close()
  if not compatibility_report.export_ready:
   project.status=ProjectStatus.DRAFT.value;await db.commit()
   raise HTTPException(status_code=422,detail='Merged worker pack failed compatibility validation: '+ '; '.join(compatibility_report.errors))
  analysis=await persist_analysis(db,project,'multi-worker-generation')
  project.ai_summary=f'Merged {body.workers} independent AI workers into one validated candidate ({len(result.mods)} mods)';project.status=ProjectStatus.REVIEW.value;await db.commit()
  return {'status':'complete','project_id':project_id,'workers':body.workers,'candidate':result.evidence(),'merge_rounds':rounds,'dependency_repair':repair_status,'compatibility':compatibility_report.model_dump(mode='json'),'analysis':analysis,'mods':[mod.model_dump(mode='json') for mod in result.mods]}
 except HTTPException:raise
 except ValueError as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
 finally:await registry.close()
@router.get('/generate/{project_id}/stream')
async def stream_generation(project_id:int):
 async def event_generator():
  async for event in orchestrator.stream_events(project_id):yield {'event':'progress','data':json.dumps(event.model_dump())}
  yield {'event':'end','data':'{}'}
 return EventSourceResponse(event_generator())
@router.post('/generate/{project_id}/cancel')
async def cancel_generation(project_id:int,db:AsyncSession=Depends(get_db)):
 cancelled=orchestrator.cancel(project_id)
 if cancelled:
  project=await db.get(Project,project_id)
  if project:project.status=ProjectStatus.DRAFT.value;await db.flush()
 return {'cancelled':cancelled}
@router.post('/generate/{project_id}/quick')
async def start_quick_generation(project_id:int,db:AsyncSession=Depends(get_db)):
 project=await db.get(Project,project_id)
 if not project:raise HTTPException(status_code=404,detail='Project not found')
 if project.status==ProjectStatus.GENERATING.value or orchestrator.is_active(project_id):raise HTTPException(status_code=409,detail='Generation already in progress')
 await _begin_generation(project,db,use_ai=False);return {'status':'started','project_id':project_id,'mode':'quick'}
