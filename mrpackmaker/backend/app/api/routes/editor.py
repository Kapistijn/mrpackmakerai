from __future__ import annotations
import json
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models.ai_request import AIRequest
from app.models.modpack_change import ModpackChange
from app.models.project import Project
from app.schemas.editor import ChangePrompt,ApproveChange
from app.services.ai_mod_editor import apply,propose
router=APIRouter()
@router.post('/{project_id}/propose')
async def propose_change(project_id:int,body:ChangePrompt,db:AsyncSession=Depends(get_db)):
 project=await db.get(Project,project_id)
 if not project:raise HTTPException(status_code=404,detail='Project not found')
 result=await propose(project,body.prompt);request=AIRequest(project_id=project_id,prompt=body.prompt,status='planned',plan_json=json.dumps(result));db.add(request);await db.flush();return {'request_id':request.id,**result}
@router.post('/{project_id}/apply')
async def apply_change(project_id:int,body:ApproveChange,db:AsyncSession=Depends(get_db)):
 project=await db.get(Project,project_id)
 if not project:raise HTTPException(status_code=404,detail='Project not found')
 request=await db.get(AIRequest,body.request_id)
 if not request or request.project_id!=project_id:raise HTTPException(status_code=404,detail='Change plan not found')
 if request.status!='planned':raise HTTPException(status_code=409,detail=f'Change plan is {request.status}, not awaiting approval')
 plan=json.loads(request.plan_json)
 if not plan.get('plan',{}).get('requires_approval',True):raise HTTPException(status_code=422,detail='Invalid change plan')
 try:mods,added,removed=await apply(project,request.prompt,plan.get('plan',{}),db)
 except ValueError as exc:raise HTTPException(status_code=422,detail=str(exc)) from exc
 change=ModpackChange(project_id=project_id,action=plan.get('plan',{}).get('action','change'),mods_added=json.dumps([m.model_dump(mode='json') for m in added]),mods_removed=json.dumps([m.model_dump(mode='json') for m in removed]),reason=plan.get('plan',{}).get('reason',''),ai_prompt=request.prompt,impact=json.dumps({'mod_count':len(mods)}));db.add(change);request.status='applied';await db.flush();return {'change_id':change.id,'mods':len(mods),'status':'applied'}
@router.get('/{project_id}/history')
async def history(project_id:int,db:AsyncSession=Depends(get_db)):
 if not await db.get(Project,project_id):raise HTTPException(status_code=404,detail='Project not found')
 rows=(await db.execute(select(ModpackChange).where(ModpackChange.project_id==project_id).order_by(ModpackChange.created_at.desc()))).scalars().all();return [{'id':r.id,'action':r.action,'added':json.loads(r.mods_added),'removed':json.loads(r.mods_removed),'reason':r.reason,'prompt':r.ai_prompt,'impact':json.loads(r.impact),'created_at':r.created_at} for r in rows]
