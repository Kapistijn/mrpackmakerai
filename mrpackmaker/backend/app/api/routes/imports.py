from __future__ import annotations
import json,os,tempfile
from pathlib import Path
from fastapi import APIRouter,Depends,File,HTTPException,UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models.imported_pack import ImportedPack
from app.models.project import Project
from app.models.enums import ProjectStatus,ShaderSupport
from app.services.modpack_importer import import_manifest
from app.services.pack_analysis import persist_analysis
router=APIRouter()
@router.post('')
async def import_mrpack(file:UploadFile=File(...),db:AsyncSession=Depends(get_db)):
 if not (file.filename or '').lower().endswith('.mrpack'):raise HTTPException(status_code=400,detail='Only .mrpack files are supported')
 data=await file.read()
 if not data:raise HTTPException(status_code=400,detail='The uploaded MRPack is empty')
 fd,path=tempfile.mkstemp(suffix='.mrpack');os.close(fd)
 try:
  with open(path,'wb') as tmp:tmp.write(data)
  result=import_manifest(path,None)
 except (ValueError,OSError) as exc:raise HTTPException(status_code=422,detail=str(exc)) from exc
 finally:
  try:os.unlink(path)
  except FileNotFoundError:pass
 info=result.get('pack_info') or {};shader=info.get('shader_mode','off');shader=shader if shader in {x.value for x in ShaderSupport} else 'off'
 project=Project(name=Path(file.filename).stem,description='Imported MRPack',minecraft_version=result['minecraft_version'],loader=(result['loader'] or '').replace('-loader',''),loader_version=result['loader_version'],theme='custom',generation_prompt='',target_ram_gb=info.get('recommended_ram'),target_fps=info.get('target_fps'),shader_support=shader,shader_quality=info.get('shader_quality'),resourcepack_support=bool(info.get('resourcepack_support',False)),ai_creativity='balanced',ai_strictness='balanced',discovery_depth='standard')
 project.mods_json=json.dumps([m.model_dump(mode='json') for m in result['mods']]);project.status=ProjectStatus.REVIEW.value;db.add(project);await db.flush();db.add(ImportedPack(project_id=project.id,filename=file.filename,manifest_json=json.dumps(result['manifest'])));await db.flush();report=await persist_analysis(db,project,'import');await db.commit();return {'project_id':project.id,'name':project.name,'mods':len(result['mods']),'pack_info':info,'analysis':report}
