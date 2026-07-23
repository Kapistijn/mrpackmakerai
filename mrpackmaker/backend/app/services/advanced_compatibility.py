"""Compatibility checks for persisted advanced configuration and exported assets."""
from __future__ import annotations
import json,zipfile
from pathlib import Path
from app.models.enums import LoaderType
from app.schemas.mod import ModEntry
from app.services.pack_assets import is_shader_loader
from app.services.pack_profile import build_pack_profile
from app.services.requirements import parse_requirements

def check_advanced(project,mods:list[ModEntry]):
 req=parse_requirements(project.generation_prompt or project.description or '',theme=project.theme,target_ram_gb=project.target_ram_gb,target_fps=project.target_fps,shader_support=project.shader_support,performance_preference=project.performance_preference,visual_quality=project.shader_quality,resourcepack_support=project.resourcepack_support,required_mods=json.loads(project.required_mods_json or '[]'),forbidden_mods=json.loads(project.forbidden_mods_json or '[]'))
 profile=build_pack_profile(req); items=[];errors=[];warnings=[];texts=' '.join(' '.join((m.name,m.slug,m.summary,*m.categories)).casefold() for m in mods)
 heavy=any(x in texts for x in ('worldgen','world generation','dimension','volumetric','shader','high quality'))
 if profile.recommended_ram_gb<=4 and heavy: errors.append('4GB profile contains heavy worldgen/visual content');items.append({'name':'RAM profile','status':'ERROR','message':'Heavy content is not compatible with 4GB target'})
 else: items.append({'name':'RAM profile','status':'OK','message':f'{profile.recommended_ram_gb}GB profile accepted'})
 perf=any(x in texts for x in ('sodium','modernfix','ferritecore','embeddium','optimization','performance'))
 if profile.target_fps and profile.target_fps>=120 and not perf: errors.append(f'{profile.target_fps} FPS target requires an optimization mod');items.append({'name':'FPS target','status':'ERROR','message':'No optimization mod found'})
 else: items.append({'name':'FPS target','status':'OK','message':f'{profile.target_fps or "balanced"} target'})
 if profile.shader_mode!='off' and not any(is_shader_loader(m) for m in mods): errors.append('Shader support requires Iris/Oculus in the resolved mod list');items.append({'name':'Shader loader','status':'ERROR','message':'Iris/Oculus missing'})
 elif profile.shader_mode!='off': items.append({'name':'Shader loader','status':'OK','message':'Compatible shader loader present'})
 if project.mrpack_path and Path(project.mrpack_path).exists():
  try:
   with zipfile.ZipFile(project.mrpack_path) as archive:
    names=set(archive.namelist());required={'overrides/pack_info.json','overrides/options.txt'}
    missing=required-names
    if missing: errors.append('Missing override asset(s): '+', '.join(sorted(missing)))
    info=json.loads(archive.read('overrides/pack_info.json'))
    if info.get('recommended_ram')!=profile.recommended_ram_gb or info.get('target_fps')!=profile.target_fps: errors.append('pack_info.json does not match the project profile')
    if profile.shader_mode!='off' and 'overrides/shaderpacks/mrpackmaker-shader.json' not in names: errors.append('Shader metadata asset missing')
    items.append({'name':'MRPack overrides','status':'ERROR' if errors else 'OK','message':'Override files and pack_info.json validated'})
  except (OSError,zipfile.BadZipFile,json.JSONDecodeError,KeyError) as exc: errors.append(f'Invalid MRPack configuration assets: {exc}')
 return items,errors,warnings
