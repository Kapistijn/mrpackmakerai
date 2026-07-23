"""Project CRUD routes and loader metadata."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from fastapi import APIRouter,Depends,HTTPException,Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import config
from app.db.session import get_db
from app.models.enums import LoaderType,ProjectStatus,ShaderSupport
from app.models.project import Project
from app.schemas.project import ProjectCreate,ProjectListItem,ProjectResponse,ProjectUpdate
from app.services.loader_metadata import LoaderMetadataError,OfficialLoaderResolver
router=APIRouter()
def _value(project,name,default=None):
 value=getattr(project,name,default)
 return default if value is None else value
def _preference_hints(body)->str:
 """Fold the moved advanced preferences into the generation prompt so the
 existing keyword-driven requirement parser actually uses them."""
 parts=[]
 if body.gameplay_style:parts.append('Gameplay focus: '+', '.join(body.gameplay_style))
 if body.world_style:parts.append(f'World style: {body.world_style}')
 if body.progression:parts.append(f'Progression: {body.progression}')
 if body.qol_level:parts.append(f'Quality of life: {body.qol_level}')
 if body.multiplayer_mode:parts.append(f'Multiplayer: {body.multiplayer_mode}')
 if body.hardware_profile:parts.append(f'Hardware profile: {body.hardware_profile}')
 return ' '.join(parts)
def _project_to_response(project:Project)->ProjectResponse:
 mods=json.loads(_value(project,'mods_json','[]') or '[]')
 return ProjectResponse(id=project.id,name=project.name,description=project.description,minecraft_version=project.minecraft_version,loader=project.loader_enum(),loader_version=project.loader_version,theme=project.theme_enum(),theme_custom=project.theme_custom,difficulty=_value(project,'difficulty','normal'),performance_preference=_value(project,'performance_preference','balanced'),generation_prompt=_value(project,'generation_prompt',project.description),minimum_mods=project.minimum_mods,maximum_mods=project.maximum_mods,minimum_downloads=_value(project,'minimum_downloads',0),target_ram_gb=project.target_ram_gb,target_fps=project.target_fps,shader_support=ShaderSupport(_value(project,'shader_support','off')),shader_quality=project.shader_quality,resourcepack_support=_value(project,'resourcepack_support',False),required_mods=json.loads(_value(project,'required_mods_json','[]') or '[]'),forbidden_mods=json.loads(_value(project,'forbidden_mods_json','[]') or '[]'),ai_creativity=_value(project,'ai_creativity','balanced'),ai_strictness=_value(project,'ai_strictness','balanced'),discovery_depth=_value(project,'discovery_depth','standard'),gameplay_style=json.loads(_value(project,'gameplay_style_json','[]') or '[]'),qol_level=getattr(project,'qol_level',None),hardware_profile=getattr(project,'hardware_profile',None),multiplayer_mode=getattr(project,'multiplayer_mode',None),world_style=getattr(project,'world_style',None),progression=getattr(project,'progression',None),status=project.status_enum(),mods=mods,resolved_loader_version=project.resolved_loader_version,ai_summary=project.ai_summary,mrpack_path=project.mrpack_path,settings_locked=_value(project,'settings_locked',False),created_at=project.created_at,updated_at=project.updated_at)
@router.get('/loader-versions')
async def loader_versions(mc:str=Query(...,min_length=3,max_length=32),loader:LoaderType=Query(...)):
 try:versions=await OfficialLoaderResolver().list_versions(loader,mc)
 except LoaderMetadataError as exc:raise HTTPException(status_code=502,detail=str(exc)) from exc
 return {'minecraft_version':mc,'loader':loader.value,'source':versions[0].source if versions else None,'versions':[{'id':f'{loader.value}:{item.version}','version':item.version,'type':'release' if item.stable else 'beta','stable':item.stable} for item in versions]}
@router.get('',response_model=list[ProjectListItem])
async def list_projects(db:AsyncSession=Depends(get_db)):
 result=await db.execute(select(Project).order_by(Project.updated_at.desc()));return [ProjectListItem(id=p.id,name=p.name,minecraft_version=p.minecraft_version,loader=p.loader_enum(),status=p.status_enum(),created_at=p.created_at,updated_at=p.updated_at) for p in result.scalars().all()]
@router.post('',response_model=ProjectResponse,status_code=201)
async def create_project(body:ProjectCreate,db:AsyncSession=Depends(get_db)):
 base_prompt=body.generation_prompt or body.description
 hints=_preference_hints(body)
 generation_prompt=(f'{base_prompt}\n{hints}'.strip() if hints else base_prompt)
 project=Project(name=body.name,description=body.description,minecraft_version=body.minecraft_version,loader=body.loader.value,loader_version=body.loader_version,theme=body.theme.value,theme_custom=body.theme_custom,difficulty=body.difficulty.value,performance_preference=body.performance_preference.value,generation_prompt=generation_prompt,minimum_mods=body.minimum_mods,maximum_mods=body.maximum_mods,minimum_downloads=body.minimum_downloads,target_ram_gb=body.target_ram_gb,target_fps=body.target_fps,shader_support=body.shader_support.value,shader_quality=body.shader_quality,resourcepack_support=body.resourcepack_support,required_mods_json=json.dumps(body.required_mods),forbidden_mods_json=json.dumps(body.forbidden_mods),ai_creativity=body.ai_creativity,ai_strictness=body.ai_strictness,discovery_depth=body.discovery_depth,gameplay_style_json=json.dumps(body.gameplay_style),qol_level=body.qol_level,hardware_profile=body.hardware_profile,multiplayer_mode=body.multiplayer_mode,world_style=body.world_style,progression=body.progression,status=ProjectStatus.DRAFT.value,mods_json='[]',settings_locked=True);db.add(project);await db.flush();await db.refresh(project);return _project_to_response(project)
@router.get('/{project_id}',response_model=ProjectResponse)
async def get_project(project_id:int,db:AsyncSession=Depends(get_db)):
 project=await db.get(Project,project_id)
 if not project:raise HTTPException(status_code=404,detail='Project not found',headers={'X-Error-Code':'not_found'})
 return _project_to_response(project)
@router.patch('/{project_id}',response_model=ProjectResponse)
async def update_project(project_id:int,body:ProjectUpdate,db:AsyncSession=Depends(get_db)):
 project=await db.get(Project,project_id)
 if not project:raise HTTPException(status_code=404,detail='Project not found')
 if body.generation_prompt is not None:project.generation_prompt=body.generation_prompt;project.mrpack_path=None
 if body.loader_version is not None:project.loader_version=body.loader_version.strip() or None;project.resolved_loader_version=None;project.mrpack_path=None
 for field in ('minimum_mods','maximum_mods','minimum_downloads','target_ram_gb','target_fps','resourcepack_support','ai_creativity','ai_strictness','discovery_depth'):
  value=getattr(body,field,None)
  if value is not None:setattr(project,field,value);project.mrpack_path=None
 if body.shader_support is not None:project.shader_support=body.shader_support.value;project.mrpack_path=None
 if body.shader_quality is not None:project.shader_quality=body.shader_quality.strip() or None;project.mrpack_path=None
 if body.required_mods is not None:project.required_mods_json=json.dumps(body.required_mods);project.mrpack_path=None
 if body.forbidden_mods is not None:project.forbidden_mods_json=json.dumps(body.forbidden_mods);project.mrpack_path=None
 if body.gameplay_style is not None:project.gameplay_style_json=json.dumps(body.gameplay_style);project.mrpack_path=None
 for field in ('qol_level','hardware_profile','multiplayer_mode','world_style','progression'):
  value=getattr(body,field,None)
  if value is not None:setattr(project,field,(value.strip() or None) if isinstance(value,str) else value);project.mrpack_path=None
 if project.minimum_mods and project.maximum_mods and project.minimum_mods>project.maximum_mods:raise HTTPException(status_code=422,detail='minimum_mods cannot exceed maximum_mods')
 if body.mods is not None:project.mods_json=json.dumps([m.model_dump(mode='json') for m in body.mods]);project.mrpack_path=None;project.status=ProjectStatus.REVIEW.value
 await db.flush();await db.refresh(project);return _project_to_response(project)
@router.delete('/{project_id}',status_code=204)
async def delete_project(project_id:int,db:AsyncSession=Depends(get_db)):
 project=await db.get(Project,project_id)
 if not project:raise HTTPException(status_code=404,detail='Project not found')
 if project.mrpack_path:
  path=Path(project.mrpack_path).resolve();output_dir=config.output_dir.resolve()
  if output_dir in path.parents and path.exists():path.unlink(missing_ok=True)
 await db.delete(project)
