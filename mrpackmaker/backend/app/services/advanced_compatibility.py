"""Compatibility checks for advanced configuration and exported assets."""
from __future__ import annotations
import json, zipfile
from pathlib import Path
from app.schemas.mod import ModEntry
from app.services.pack_assets import is_shader_loader
from app.services.pack_profile import build_pack_profile
from app.services.requirements import parse_requirements

def check_advanced(project, mods:list[ModEntry]):
    value=lambda name,default=None:getattr(project,name,default)
    req=parse_requirements(value('generation_prompt','') or value('description',''),theme=value('theme'),target_ram_gb=value('target_ram_gb'),target_fps=value('target_fps'),shader_support=value('shader_support'),performance_preference=value('performance_preference'),visual_quality=value('shader_quality'),resourcepack_support=value('resourcepack_support',False),required_mods=value('required_mods_json','[]'),forbidden_mods=value('forbidden_mods_json','[]'))
    profile=build_pack_profile(req);items=[];errors=[];warnings=[];texts=' '.join(' '.join((m.name,m.slug,m.summary,*m.categories)).casefold() for m in mods)
    heavy=any(x in texts for x in ('worldgen','world generation','dimension','volumetric','shader','high quality'))
    if profile.recommended_ram_gb<=4 and heavy: errors.append('4GB profile contains heavy worldgen/visual content');items.append({'name':'RAM profile','status':'ERROR','message':'Heavy content is not compatible with 4GB target'})
    else: items.append({'name':'RAM profile','status':'OK','message':f'{profile.recommended_ram_gb}GB profile accepted'})
    perf=any(x in texts for x in ('sodium','modernfix','ferritecore','embeddium','optimization','performance'))
    if profile.target_fps and profile.target_fps>=120 and not perf: errors.append(f'{profile.target_fps} FPS target requires an optimization mod');items.append({'name':'FPS target','status':'ERROR','message':'No optimization mod found'})
    else: items.append({'name':'FPS target','status':'OK','message':f'{profile.target_fps or "balanced"} target'})
    if profile.shader_mode!='off' and not any(is_shader_loader(m) for m in mods): errors.append('Shader support requires Iris/Oculus in the resolved mod list');items.append({'name':'Shader loader','status':'ERROR','message':'Iris/Oculus missing'})
    elif profile.shader_mode!='off': items.append({'name':'Shader loader','status':'OK','message':'Compatible shader loader present'})
    path=value('mrpack_path')
    if path and Path(path).exists():
        try:
            with zipfile.ZipFile(path) as archive:
                names=set(archive.namelist()); required={'overrides/pack_info.json','overrides/options.txt'}; missing=required-names
                if missing: errors.append('Missing override asset(s): '+', '.join(sorted(missing)))
                info=json.loads(archive.read('overrides/pack_info.json'))
                if info.get('recommended_ram')!=profile.recommended_ram_gb or info.get('target_fps')!=profile.target_fps: errors.append('pack_info.json does not match the project profile')
                if profile.shader_mode!='off' and 'overrides/shaderpacks/mrpackmaker-shader.json' not in names: errors.append('Shader metadata asset missing')
                items.append({'name':'MRPack overrides','status':'ERROR' if errors else 'OK','message':'Override files and pack_info.json validated'})
        except (OSError,zipfile.BadZipFile,json.JSONDecodeError,KeyError) as exc: errors.append(f'Invalid MRPack configuration assets: {exc}')
    return items,errors,warnings
