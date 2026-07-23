from __future__ import annotations
import json,tempfile
from pathlib import Path
from fastapi import APIRouter,Depends,File,HTTPException,UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models.imported_pack import ImportedPack
from app.models.project import Project
from app.models.enums import ProjectStatus
from app.services.modpack_importer import import_manifest
router=APIRouter()
@router.post('')
async def import_mrpack(file:UploadFile=File(...),db:AsyncSession=Depends(get_db)):
 if not (file.filename or '').lower().endswith('.mrpack'):raise HTTPException(400,'Only .mrpack files are supported')
 data=await file.read()
 with tempfile.NamedTemporaryFile(suffix='.mrpack') as tmp:
  tmp.write(data);tmp.flush();result=import_manifest(tmp.name,None)
 project=Project(name=Path(file.filename).stem,description='Imported MRPack',minecraft_version=result['minecraft_version'],loader=(result['loader'] or '').replace('-loader',''),loader_version=result['loader_version'],theme='custom',generation_prompt='')
 project.mods_json=json.dumps([m.model_dump(mode='json') for m in result['mods']]);project.status=ProjectStatus.REVIEW.value;db.add(project);await db.flush();db.add(ImportedPack(project_id=project.id,filename=file.filename,manifest_json=json.dumps(result['manifest'])));await db.flush();return {'project_id':project.id,'name':project.name,'mods':len(result['mods'])}
