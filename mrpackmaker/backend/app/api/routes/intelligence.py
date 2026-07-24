from __future__ import annotations
import json
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import config
from app.db.session import get_db
from app.models.project import Project
from app.models.pack_analysis import PackAnalysis
from app.models.pack_snapshot import PackSnapshot
from app.services.pack_analysis import persist_analysis
from app.services.pack_snapshots import list_snapshots,restore_snapshot
from app.services.dependency_repair import repair_project_dependencies
from app.services.compatibility import CompatibilityService
from app.services.modrinth import ModrinthClient
from app.services.curseforge import CurseForgeClient
router=APIRouter()
class HardwareInput(BaseModel):
 cpu:str|None=None;gpu:str|None=None;ram_gb:int|None=Field(default=None,ge=1,le=512);resolution:str|None=None;refresh_rate:int|None=Field(default=None,ge=1,le=1000);target_fps:int|None=Field(default=None,ge=1,le=1000);shader_preference:str|None=None
async def _project(project_id,db):
 project=await db.get(Project,project_id)
 if not project:raise HTTPException(status_code=404,detail='Project not found')
 return project
@router.get('/{project_id}')
async def get_intelligence(project_id:int,db:AsyncSession=Depends(get_db)):
 project=await _project(project_id,db);latest=(await db.execute(select(PackAnalysis).where(PackAnalysis.project_id==project_id).order_by(PackAnalysis.version.desc()).limit(1))).scalars().first()
 if not latest:report=await persist_analysis(db,project,'on-demand');await db.commit();latest=(await db.execute(select(PackAnalysis).where(PackAnalysis.project_id==project_id).order_by(PackAnalysis.version.desc()).limit(1))).scalars().first()
 else:report=json.loads(latest.report_json)
 return {'analysis_id':latest.id,'version':latest.version,'created_at':latest.created_at,'report':report}
@router.post('/{project_id}/hardware')
async def set_hardware(project_id:int,body:HardwareInput,db:AsyncSession=Depends(get_db)):
 project=await _project(project_id,db)
 for field,target in {'cpu':'hardware_cpu','gpu':'hardware_gpu','resolution':'hardware_resolution','refresh_rate':'hardware_refresh_rate'}.items():setattr(project,target,getattr(body,field))
 if body.ram_gb is not None:project.target_ram_gb=body.ram_gb
 if body.target_fps is not None:project.target_fps=body.target_fps
 if body.shader_preference is not None:project.shader_support=body.shader_preference
 report=await persist_analysis(db,project,'hardware-change');await db.commit();return report
@router.post('/{project_id}/scan')
async def scan(project_id:int,db:AsyncSession=Depends(get_db)):
 project=await _project(project_id,db);report=await persist_analysis(db,project,'manual');await db.commit();return report
@router.get('/{project_id}/history')
async def analysis_history(project_id:int,db:AsyncSession=Depends(get_db)):
 await _project(project_id,db);rows=(await db.execute(select(PackAnalysis).where(PackAnalysis.project_id==project_id).order_by(PackAnalysis.version.desc()))).scalars().all();return [{'id':r.id,'version':r.version,'score':r.overall_score,'source':r.source,'created_at':r.created_at,'report':json.loads(r.report_json)} for r in rows]
@router.get('/{project_id}/snapshots')
async def snapshots(project_id:int,db:AsyncSession=Depends(get_db)):
 await _project(project_id,db);rows=await list_snapshots(db,project_id);return [{'id':r.id,'version':r.version,'reason':r.reason,'change':json.loads(r.change_json),'created_at':r.created_at} for r in rows]
@router.post('/{project_id}/snapshots/{snapshot_id}/restore')
async def restore(project_id:int,snapshot_id:int,db:AsyncSession=Depends(get_db)):
 project=await _project(project_id,db);snapshot=await db.get(PackSnapshot,snapshot_id)
 if not snapshot or snapshot.project_id!=project_id:raise HTTPException(status_code=404,detail='Snapshot not found')
 await restore_snapshot(db,project,snapshot);await repair_project_dependencies(project,db)
 service=CompatibilityService(modrinth=ModrinthClient(config.apis.modrinth_key),curseforge=CurseForgeClient(config.apis.curseforge_key))
 try:report=await service.check_project(project)
 finally:await service.close()
 if not report.export_ready:raise HTTPException(status_code=422,detail='Restored snapshot failed compatibility validation')
 analysis=await persist_analysis(db,project,'rollback');await db.commit();return {'status':'restored','version':snapshot.version,'analysis':analysis}
@router.get('/{project_id}/snapshots/compare/{left}/{right}')
async def compare(project_id:int,left:int,right:int,db:AsyncSession=Depends(get_db)):
 await _project(project_id,db);a=await db.get(PackSnapshot,left);b=await db.get(PackSnapshot,right)
 if not a or not b or a.project_id!=project_id or b.project_id!=project_id:raise HTTPException(status_code=404,detail='Snapshot not found')
 am={f"{x.get('source')}:{x.get('id')}":x for x in json.loads(a.mods_json)};bm={f"{x.get('source')}:{x.get('id')}":x for x in json.loads(b.mods_json)}
 return {'left':a.version,'right':b.version,'added':[bm[k] for k in bm.keys()-am.keys()],'removed':[am[k] for k in am.keys()-bm.keys()],'changed':[bm[k] for k in bm.keys()&am.keys() if bm[k]!=am[k]]}
