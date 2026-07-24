from __future__ import annotations
import json
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.enums import LoaderType,ProjectStatus
from app.models.project import Project
from app.schemas.mod import ModEntry
from app.services.dependency_resolver import DependencyResolver
from app.services.mod_resolver import ModResolver
from app.services.source_registry import create_default_registry
async def repair_project_dependencies(project:Project,db:AsyncSession,*,strict:bool=False)->dict:
 selected=[ModEntry.model_validate(raw) for raw in json.loads(project.mods_json or '[]')];registry=create_default_registry();resolver=ModResolver(registry=registry)
 try:
  refreshed=[]
  for item in selected:
   try:detail=await resolver.resolve_mod(item.source,item.id,project.minecraft_version,LoaderType(project.loader))
   except Exception:detail=None
   refreshed.append(detail or item)
  result=await DependencyResolver(resolver).resolve_pack(refreshed,project.minecraft_version,LoaderType(project.loader),include_optional=False)
  failures=[{'mod':f.parent,'missing':f.dependency,'reason':f.reason,'suggestion':f.suggestion} for f in result.failures]
  if (result.failures or result.cycles) and strict:
   raise HTTPException(status_code=422,detail={'message':'Some dependencies could not be resolved.','unresolved':failures,'cycles':[list(c) for c in result.cycles],'passes':result.passes,'events':[e.__dict__ for e in result.events]})
  dropped=[]
  if result.failures and not strict:
   blocked={f.parent for f in result.failures};missing={f.dependency for f in result.failures};keep=[]
   for item in refreshed:
    dep_ids={d.project_id for d in item.dependencies}
    if item.id in blocked or dep_ids & (blocked|missing):dropped.append(item.name);continue
    keep.append(item)
   if keep and len(keep)<len(refreshed):result=await DependencyResolver(resolver).resolve_pack(keep,project.minecraft_version,LoaderType(project.loader),include_optional=False)
  repaired=list(result.mods)
  if len(repaired)!=len(selected) or any(a.model_dump()!=b.model_dump() for a,b in zip(repaired,selected)):
   project.mods_json=json.dumps([m.model_dump(mode='json') for m in repaired]);project.mrpack_path=None;project.status=ProjectStatus.REVIEW.value;await db.flush()
  return {'mods':len(repaired),'optional_added':result.optional_added,'passes':result.passes,'dropped_unresolved':dropped,'unresolved':failures,'events':[e.__dict__ for e in result.events]}
 finally:await resolver.close()
