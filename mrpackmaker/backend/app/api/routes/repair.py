from __future__ import annotations
import json
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models.repair_report import RepairReport
from app.models.project import Project
from app.schemas.editor import CrashRequest
from app.services.repair_engine import repair_report
router=APIRouter()
@router.post('/{project_id}')
async def analyze_repair(project_id:int,body:CrashRequest,db:AsyncSession=Depends(get_db)):
 project=await db.get(Project,project_id)
 if not project:raise HTTPException(status_code=404,detail='Project not found')
 result=repair_report(body.text)
 row=RepairReport(project_id=project_id,source_text=body.text,report_json=json.dumps(result));db.add(row);await db.flush();return {'id':row.id,**result}
