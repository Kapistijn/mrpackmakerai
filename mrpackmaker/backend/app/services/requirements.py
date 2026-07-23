"""Requirement parsing, optional preferences, and deterministic quota planning."""
from __future__ import annotations
import json
import re
from dataclasses import dataclass
@dataclass(frozen=True)
class Requirements:
    themes: tuple[str,...]=(); required_features: tuple[str,...]=(); forbidden_features: tuple[str,...]=(); minimum_mods: int|None=None; maximum_mods: int|None=None; minimum_downloads: int=0; multiplayer: bool=False; target_ram_gb: int|None=None; target_fps: int|None=None; shader_support: str|None=None; performance_preference: str|None=None; visual_quality: str|None=None; hardware_profile: str|None=None; multiplayer_mode: str|None=None; world_style: str|None=None; progression: str|None=None; warnings: tuple[str,...]=(); resourcepack_support: bool=False
    @property
    def target_count(self)->int: return self.maximum_mods or self.minimum_mods or 40

def category_quotas(requirements: Requirements,target_count: int|None=None)->dict[str,int]:
    target=target_count or requirements.target_count; target=max(requirements.minimum_mods or 0,target)
    if requirements.maximum_mods is not None: target=min(target,requirements.maximum_mods)
    text=' '.join((*requirements.themes,*requirements.required_features,requirements.world_style or '',requirements.progression or '')).casefold(); categories=[]
    if requirements.themes: categories.append((requirements.themes[0],.15))
    if any(t in text for t in ('qol','inventory','utility','storage')): categories.append(('qol',.20))
    if any(t in text for t in ('performance','fps','optimization')): categories.append(('performance',.10))
    if any(t in text for t in ('worldgen','exploration','adventure','structures','world')): categories.append(('world',.15))
    if any(t in text for t in ('boss','combat','mobs')): categories.append(('combat',.15))
    if requirements.progression and requirements.progression != 'fast': categories.append(('progression',.10))
    if not categories: categories.append(('requested',.50))
    quotas={name:max(1,int(target*share)) for name,share in categories}; quotas['remaining']=max(0,target-sum(quotas.values())); return quotas
THEME_RULES={'horror':{'include':('horror','mobs','worldgen','sound','atmosphere','lighting','survival'),'exclude':('cobblemon','pokemon','technology','magic','farming')},'technology':{'include':('technology','automation','storage','utility'),'exclude':('magic',)},'magic':{'include':('magic','adventure','mobs'),'exclude':('technology',)},'adventure':{'include':('adventure','worldgen','mobs','structures'),'exclude':()}}
def _number(text,markers):
    for marker in markers:
        match=re.search(rf'(?:{marker})\s*(\d+)',text,re.I)
        if match:return int(match.group(1))
    return None
def _advanced(prompt):
    try:
        value=json.loads(prompt); return value.get('advanced',{}) if isinstance(value,dict) else {}
    except (TypeError,json.JSONDecodeError): return {}
def _optional_int(value):
    if value in (None,'','none'): return None
    return int(value)
def _optional_text(value):
    if value in (None,'','none'): return None
    text=str(value).strip().casefold(); return text or None
def parse_requirements(prompt: str, *, theme: str|None=None, minimum_mods: int|None=None, maximum_mods: int|None=None, minimum_downloads: int|None=None, target_ram_gb: int|None=None, target_fps: int|None=None, shader_support: str|None=None, performance_preference: str|None=None, visual_quality: str|None=None, resourcepack_support: bool|None=None)->Requirements:
    text=(prompt or '').casefold(); advanced=_advanced(prompt); selected_theme=_optional_text(advanced.get('theme')) or theme
    detected=[name for name in THEME_RULES if re.search(rf'\b{re.escape(name)}\b',text)]
    if selected_theme in THEME_RULES and selected_theme not in detected: detected.insert(0,selected_theme)
    active=THEME_RULES.get(detected[0],{}) if detected else {}; required=list(active.get('include',())); forbidden=list(active.get('exclude',()))
    gameplay=[str(v).casefold() for v in advanced.get('gameplay_style',[]) if str(v).strip()]; required += gameplay + [str(v).casefold() for v in advanced.get('required_mods',[]) if str(v).strip()]
    world_style=_optional_text(advanced.get('world_style')); progression=_optional_text(advanced.get('progression'))
    if world_style: required += [world_style,'worldgen']
    if progression: required += [progression,'progression']
    if advanced.get('qol_level') in {'high','maximum'}: required += ['qol','inventory','ui','storage']
    # Explicit keyword arguments (persisted project fields) always win over any
    # values embedded in an advanced-JSON prompt, which in turn win over free text.
    eff_ram = target_ram_gb if target_ram_gb is not None else _optional_int(advanced.get('target_ram_gb'))
    eff_fps = target_fps if target_fps is not None else _optional_int(advanced.get('target_fps') or advanced.get('fps_target'))
    eff_shader = _optional_text(shader_support) if shader_support is not None else _optional_text(advanced.get('shader_support'))
    eff_perf = _optional_text(performance_preference) if performance_preference is not None else _optional_text(advanced.get('performance_preference'))
    eff_visual = _optional_text(visual_quality) if visual_quality is not None else _optional_text(advanced.get('visual_quality'))
    eff_resourcepack = bool(resourcepack_support) if resourcepack_support is not None else bool(advanced.get('resourcepack_support', False))
    if eff_shader not in (None,'none'): required += ['shader','performance']
    if eff_fps is not None and eff_fps>=120: required.append('performance')
    forbidden += [str(v).casefold() for v in advanced.get('forbidden_mods',[]) if str(v).strip()]
    if re.search(r'qol|quality of life',text): required += ['qol','inventory','ui','sound']
    if re.search(r'boss|bazen',text): required.append('bosses')
    if re.search(r'monster|mob|zombie',text): required.append('mobs')
    if re.search(r'no magic|geen magie',text): forbidden.append('magic')
    if re.search(r'no technology|geen technologie',text): forbidden.append('technology')
    parsed_min=_number(text,('at least','minimum','minimaal','minstens')); match=re.search(r'\b(\d+)\s+mods?\b',text); explicit_count=int(match.group(1)) if match else None; parsed_max=_number(text,('at most','maximum','maximaal'))
    advanced_min=_optional_int(advanced.get('minimum_mods')) if advanced.get('minimum_mods') is not None else None; advanced_max=_optional_int(advanced.get('maximum_mods')) if advanced.get('maximum_mods') is not None else None
    effective_min=minimum_mods if minimum_mods is not None else (advanced_min if advanced_min is not None else (parsed_min or explicit_count)); effective_max=maximum_mods if maximum_mods is not None else (advanced_max if advanced_max is not None else parsed_max)
    downloads=minimum_downloads if minimum_downloads else (_number(text,(r'minimum\s+downloads?',r'min(?:imum)?\s+downloads?',r'downloads?\s*[:=]')) or 0)
    mode=_optional_text(advanced.get('multiplayer_mode')); warnings=('minimum_mods exceeds maximum_mods',) if effective_min and effective_max and effective_min>effective_max else ()
    return Requirements(tuple(dict.fromkeys(detected)),tuple(dict.fromkeys(required)),tuple(dict.fromkeys(forbidden)),effective_min,effective_max,max(0,downloads),bool(re.search(r'multiplayer|server|samen spelen',text)),eff_ram,eff_fps,eff_shader,eff_perf,eff_visual,_optional_text(advanced.get('hardware_profile')),mode,world_style,progression,warnings,resourcepack_support=eff_resourcepack)
def theme_matches(mod_text: str,requirements: Requirements)->bool:
    text=(mod_text or '').casefold(); return not any(re.search(rf'\b{re.escape(term)}\b',text) for term in requirements.forbidden_features)
