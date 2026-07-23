"""Explainable, deterministic pack intelligence used by the AI and UI."""
from __future__ import annotations
import math
from itertools import combinations
from typing import Any
from app.schemas.mod import ModEntry
_REALISM={"season","weather","temperature","thirst","hunger","terrain","ambient","realistic","survival"};_IMMERSION={"ambient","sound","biome","weather","season","lighting","atmosphere","realistic"};_PERFORMANCE={"sodium","lithium","modernfix","ferritecore","embeddium","optimization","performance","fps"};_WORLDGEN={"worldgen","world generation","terrain","biome","dimension","structures"};_ENTITIES={"mob","animal","creature","entity","boss"};_PARTICLES={"particle","visual","magic","spell","shader"}
def _text(mod):return ' '.join((mod.name,mod.slug,mod.summary,*mod.categories)).casefold()
def _hits(text,terms):return sum(term in text for term in terms)
def _pct(value):return max(0,min(100,round(value*100)))
def _bar(value,width=10):
 filled=round(value/100*width);return '█'*filled+'░'*(width-filled)
def quality_report(mods:list[ModEntry])->dict[str,Any]:
 if not mods:return {'scores':{k:0 for k in ('realism','immersion','performance','compatibility','content_balance')},'explanation':'No mods available to score.'}
 texts=[_text(mod) for mod in mods];realism=sum(min(1,_hits(text,_REALISM)/4) for text in texts)/len(texts);immersion=sum(min(1,_hits(text,_IMMERSION)/3) for text in texts)/len(texts);performance=sum(1 if _hits(text,_PERFORMANCE) else (.45 if _hits(text,_WORLDGEN|_PARTICLES) else .8) for text in texts)/len(texts);compatibility=sum(bool(mod.file_name and mod.download_url and (mod.hashes.sha1 or mod.hashes.sha512)) for mod in mods)/len(mods);categories=[category.casefold() for mod in mods for category in mod.categories];balance=min(1,len(set(categories))/max(1,min(10,len(mods)/3)));scores={'realism':_pct(realism),'immersion':_pct(immersion),'performance':_pct(performance),'compatibility':_pct(compatibility),'content_balance':_pct(balance)};return {'scores':scores,'bars':{key:_bar(value) for key,value in scores.items()},'explanation':'The pack could use more food, farming, or survival variety.' if scores['content_balance']<60 else 'Content categories are reasonably balanced.'}
def synergy_report(mods:list[ModEntry])->dict[str,Any]:
 synergies=[];conflicts=[]
 for left,right in combinations(mods,2):
  a,b=_text(left),_text(right);shared=[term for term in sorted(_REALISM|_WORLDGEN|_PERFORMANCE) if term in a and term in b]
  if shared:synergies.append({'mods':[left.name,right.name],'score':min(95,55+len(shared)*12),'signals':shared,'explanation':f"{left.name} and {right.name} reinforce {', '.join(shared[:3])}."})
  if _hits(a,_WORLDGEN) and _hits(b,_WORLDGEN):conflicts.append({'mods':[left.name,right.name],'risk':'high','type':'world_generation_overlap','explanation':'Both mods modify terrain, biomes, dimensions, or structures. Check configs before export.'})
 return {'synergies':sorted(synergies,key=lambda item:item['score'],reverse=True)[:25],'conflicts':conflicts[:25]}
def performance_estimate(mods:list[ModEntry],*,ram_gb=None,fps_target=None,shader_support=None)->dict[str,Any]:
 texts=[_text(mod) for mod in mods];worldgen=sum(bool(_hits(text,_WORLDGEN)) for text in texts);entities=sum(bool(_hits(text,_ENTITIES)) for text in texts);particles=sum(bool(_hits(text,_PARTICLES)) for text in texts);shaders=1 if shader_support in ('enabled','required','recommended') else 0;estimated_ram=max(4,round(4+len(mods)*.018+worldgen*.12+entities*.04+shaders*2));vram=max(2,round(2+shaders*2+particles*.015));cores=max(4,min(16,round(4+worldgen/30+entities/50)));fps_low=max(30,round(180-len(mods)*.12-worldgen*1.4-entities*.25-particles*.2-shaders*35));return {'ram_gb':estimated_ram,'vram_gb':vram,'cpu_cores':cores,'gpu_recommendation':'RTX 3060 or better' if vram>=6 else 'GTX 1660 / RX 5600 XT or better','expected_fps':{'low':fps_low,'high':max(fps_low+10,fps_low+50-shaders*10)},'inputs':{'mods':len(mods),'worldgen':worldgen,'entities':entities,'particles':particles,'shaders':bool(shaders),'ram_preference':ram_gb,'fps_target':fps_target}}
def reputation_report(mod):
 downloads=min(5,max(1,round(math.log10(max(mod.downloads,1))/2)));compatibility=5 if mod.file_name and mod.download_url and (mod.hashes.sha1 or mod.hashes.sha512) else 2;return {'mod':mod.name,'stability':downloads,'maintenance':5 if mod.file_name and mod.download_url else 2,'compatibility':compatibility,'performance':3 if _hits(_text(mod),_WORLDGEN|_PARTICLES) else 4,'evidence':['downloads','downloadable release','hash availability','metadata complexity']}
def variant_plan(base_name,mods):return [{'name':f'{base_name} Lite','tier':'lite','mods':min(50,len(mods)),'ram_gb':8,'shaders':False},{'name':f'{base_name} Balanced','tier':'balanced','mods':min(150,len(mods)),'ram_gb':12,'shaders':False},{'name':f'{base_name} Ultimate','tier':'ultimate','mods':min(350,len(mods)),'ram_gb':24,'shaders':True}]
def natural_language_plan(prompt,mods):
 text=prompt.casefold();additions=['horror ambience','harder mobs','darkness mechanics'] if any(word in text for word in ('enger','horror','scary')) else (['seasons','temperature','thirst','realistic terrain'] if any(word in text for word in ('echte wereld','realistic','realistisch')) else ([prompt.strip()[:120]] if prompt.strip() else []));return {'prompt':prompt,'add_queries':additions,'remove_names':[],'rationale':'Adds requested systems without removing existing content.' if additions else 'The request needs a catalog search pass before changes are applied.','approval_required':True,'current_mod_count':len(mods)}
