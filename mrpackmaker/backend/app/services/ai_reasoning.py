"""Deterministic multi-round pack engineering primitives.

This layer is deliberately provider-agnostic: catalog facts are gathered first,
then scored, checked for missing intent coverage, critiqued, and only then
handed to the existing generation/export pipeline.
"""
from __future__ import annotations
from dataclasses import dataclass,asdict
from typing import Any
from app.schemas.mod import ModEntry
from app.services.pack_intelligence import quality_report,synergy_report,performance_estimate,reputation_report

@dataclass(frozen=True)
class ModMemory:
 name:str
 source:str
 categories:tuple[str,...]
 roles:tuple[str,...]
 dependencies:tuple[str,...]
 downloads:int
 performance_impact:str
 compatibility:str
 reason:str
 confidence:int
 alternatives:tuple[str,...]=()

def _roles(mod:ModEntry)->tuple[str,...]:
 text=' '.join((mod.name,mod.slug,mod.summary,*mod.categories)).casefold();roles=[]
 for token,role in (('create','automation'),('factory','engineering'),('storage','storage'),('transport','transport'),('food','farming'),('farm','farming'),('worldgen','world generation'),('quest','progression'),('magic','magic'),('boss','combat'),('aircraft','transport')):
  if token in text and role not in roles:roles.append(role)
 return tuple(roles or ['general'])

def build_mod_memory(mod:ModEntry,reason:str='',confidence:int=70,alternatives:tuple[str,...]=())->dict[str,Any]:
 impact='high' if any(x in ' '.join(mod.categories).casefold() for x in ('worldgen','particle','shader','dimension')) else 'low'
 compatible='excellent' if mod.file_name and mod.download_url and (mod.hashes.sha1 or mod.hashes.sha512) else 'needs validation'
 return asdict(ModMemory(mod.name,mod.source,tuple(mod.categories),_roles(mod),tuple(d.project_id for d in mod.dependencies),mod.downloads,impact,compatible,reason or 'Matches the requested pack intent',max(0,min(100,confidence)),alternatives))

def missing_categories(mods:list[ModEntry],requested:list[str])->list[str]:
 covered={role for mod in mods for role in _roles(mod)};return [item for item in requested if item.casefold() not in covered]

def critique_pack(mods:list[ModEntry],requested:list[str],*,ram_gb=None,fps_target=None,shader_support=None)->dict[str,Any]:
 quality=quality_report(mods);synergy=synergy_report(mods);performance=performance_estimate(mods,ram_gb=ram_gb,fps_target=fps_target,shader_support=shader_support);missing=missing_categories(mods,requested);redundant=[]
 by_role={}
 for mod in mods:
  for role in _roles(mod):by_role.setdefault(role,[]).append(mod.name)
 for role,names in by_role.items():
  if len(names)>3:redundant.append({'role':role,'mods':names,'reason':'Several mods serve the same role; review overlap.'})
 problems=[]
 problems.extend({'type':'missing_category','category':item,'severity':'medium','recommendation':f'Search for more {item} content'} for item in missing)
 problems.extend({'type':'worldgen_overlap','mods':item['mods'],'severity':'high','recommendation':'Review configs before export'} for item in synergy['conflicts'])
 return {'quality':quality,'performance':performance,'synergy':synergy,'missing_categories':missing,'redundancy':redundant,'problems':problems,'recommendations':[p['recommendation'] for p in problems]}

def confidence_for(mod:ModEntry,requested_roles:list[str])->int:
 roles=set(_roles(mod));match=len(roles.intersection({x.casefold() for x in requested_roles}));evidence=sum(bool(x) for x in (mod.file_name,mod.download_url,mod.hashes.sha1 or mod.hashes.sha512));return max(20,min(99,45+match*15+evidence*10))

def alternatives_for(mod:ModEntry,candidates:list[ModEntry],limit:int=3)->list[str]:
 roles=set(_roles(mod));ranked=[item for item in candidates if item is not mod and roles.intersection(_roles(item))];return [item.name for item in sorted(ranked,key=lambda x:x.downloads,reverse=True)[:limit]]
