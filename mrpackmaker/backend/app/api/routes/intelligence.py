from __future__ import annotations
import json
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models.project import Project
from app.models.pack_analysis import PackAnalysis
from app.models.pack_snapshot import PackSnapshot
from app.services.pack_analysis import persist_analysis
from app.services.pack_snapshots import list_snapshots,restore_snapshot
router=APIRouter()
class HardwareInput(BaseModel):
 cpu:str|None=None;gpu:str|None=None;ram_gb:int|None=Field(default=None,ge=1,le=512);resolution:str|None=None;refresh_rate:int|None=Field(default=None,ge=1,le=1000);target_fps:int|None=Field(default=None,ge=1,le=1000);shader_preference:str|None=None
@router.get('/{project_id}')
async def get_intelligence(project_id:int,db:AsyncSession=Depends(get_db)):
 project=await db.get(Project,project_id)
 if not project:raise HTTPException(status_code=404,detail='Project not found')
 latest=(await db.execute(select(PackAnalysis).where(PackAnalysis.project_id==project_id).order_by(PackAnalysis.version.desc()))).scalars().first()
 if not latest:report=await persist_analysis(db,project,'on-demand');await db.commit();latest=(await db.execute(select(PackAnalysis).where(PackAnalysis.project_id==project_id).order_by(PackAnalysis.version.desc()))).scalars().first()
 else:report=json.loads(latest.report_json)
 return {'analysis_id':latest.id,'version':latest.version,'created_at':latest.created_at,'report':report}
@router.post('/{project_id}/hardware')
async def set_hardware(project_id:int,body:HardwareInput,db:AsyncSession=Depends(get_db)):
 project=await db.get(Project,project_id)
 if not project:raise HTTPException(status_code=404,detail='Project not found')
 for field in ('cpu','gpu','resolution','refresh_rate'):
  value=getattr(body,field);setattr(project,{'cpu':'hardware_cpu','gpu':'hardware_gpu','resolution':'hardware_resolution','refresh_rate':'hardware_refresh_rate'}[field],value)
 if body.ram_gb is not None:project.target_ram_gb=body.ram_gb
 if body.target_fps is not None:project.target_fps=body.target_fps
 if body.shader_preference is not None:project.shader_support=body.shader_preference
 report=await persist_analysis(db,project,'hardware-change');await db.commit();return report
@router.post('/{project_id}/scan')
async def scan(project_id:int,db:AsyncSession=Depends(get_db)):
 project=await db.get(Project,project_id)
 if not project:raise HTTPException(status_code=404,detail='Project not found')
 report=await persist_analysis(db,project,'manual');await db.commit();return report
@router.get('/{project_id}/history')
async def analysis_history(project_id:int,db:AsyncSession=Depends(get_db)):
 rows=(await db.execute(select(PackAnalysis).where(PackAnalysis.project_id==project_id).order_by(PackAnalysis.version.desc()))).scalars().all();return [{'id':r.id,'version':r.version,'score':r.overall_score,'source':r.source,'created_at':r.created_at,'report':json.loads(r.report_json)} for r in rows]
@router.get('/{project_id}/snapshots')
async def snapshots(project_id:int,db:AsyncSession=Depends(get_db)):
 rows=await list_snapshots(db,project_id);return [{'id':r.id,'version':r.version,'reason':r.reason,'change':json.loads(r.change_json),'created_at':r.created_at} for r in rows]
@router.post('/{project_id}/snapshots/{snapshot_id}/restore')
async def restore(project_id:int,snapshot_id:int,db:AsyncSession=Depends(get_db)):
 project=await db.get(Project,project_id);snapshot=await db.get(PackSnapshot,snapshot_id)
 if not project or not snapshot or snapshot.project_id!=project_id:raise HTTPException(status_code=404,detail='Snapshot not found')
 await restore_snapshot(db,project,snapshot);await db.commit();return {'status':'restored','version':snapshot.version}
@router.get('/{project_id}/snapshots/compare/{left}/{right}')
async def compare(project_id:int,left:int,right:int,db:AsyncSession=Depends(get_db)):
 a=await db.get(PackSnapshot,left);b=await db.get(PackSnapshot,right)
 if not a or not b or a.project_id!=project_id or b.project_id!=project_id:raise HTTPException(status_code=404,detail='Snapshot not found')
 am={x.get('id'):x for x in json.loads(a.mods_json)};bm={x.get('id'):x for x in json.loads(b.mods_json)}
 return {'left':a.version,'right':b.version,'added':[bm[k] for k in bm.keys()-am.keys()],'removed':[am[k] for k in am.keys()-bm.keys()]}
