"""Parallel AI candidate generation and quality-aware merge rounds."""
from __future__ import annotations
import asyncio,hashlib
from dataclasses import dataclass,field
from typing import Awaitable,Callable
from pydantic import BaseModel
from app.models.enums import LoaderType
from app.schemas.mod import ModEntry
from app.services.ai_provider import AIProviderError,create_ai_provider
from app.services.cache import shared_catalog_cache
from app.services.mod_resolver import mod_identity
from app.services.source_registry import ModSourceRegistry
MAX_WORKERS=24
@dataclass(frozen=True)
class WorkerDirective:index:int;seed:int;focus:str
@dataclass
class WorkerCandidate:
 directive:WorkerDirective;mods:list[ModEntry]=field(default_factory=list);score:float=0.0;intent_coverage:float=0.0;compatibility:float=0.0;performance:float=0.0;dependency_quality:float=0.0;confidence:float=0.0;reasoning:str='';ai_used:bool=False;fallback_reason:str|None=None
 def keyset(self)->set[str]:return {mod_identity(mod) for mod in self.mods}
 def evidence(self)->dict:return {'worker':self.directive.index,'focus':self.directive.focus,'score':round(self.score,2),'intent_coverage':self.intent_coverage,'compatibility':self.compatibility,'performance':self.performance,'dependency_quality':self.dependency_quality,'confidence':self.confidence,'redundancy':0.0,'synergy':0.0,'worldgen':self._category_score(('worldgen','biome','structure')),'export_validity':self._export_score(),'reasoning':self.reasoning,'ai_used':self.ai_used,'fallback_reason':self.fallback_reason,'mod_count':len(self.mods)}
 def _category_score(self,terms:tuple[str,...])->float:
  return min(100.0,100.0*sum(any(term in ' '.join(mod.categories).casefold() for term in terms) for mod in self.mods)/max(1,len(self.mods)))
 def _export_score(self)->float:return min(100.0,100.0*sum(bool(mod.file_name and mod.download_url and (mod.hashes.sha1 or mod.hashes.sha512)) for mod in self.mods)/max(1,len(self.mods)))
class AsyncCoalescingCache:
 def __init__(self):self._values={};self._inflight={};self._lock=asyncio.Lock()
 async def get_or_fetch(self,key,fetch):
  shared=shared_catalog_cache
  return await shared.get_or_fetch(key,fetch)
class WorkerGenerationEngine:
 def __init__(self,registry:ModSourceRegistry,*,max_concurrency:int|None=None):self.registry=registry;self.cache=AsyncCoalescingCache();self.max_concurrency=max(1,min(max_concurrency or 8,MAX_WORKERS))
 @staticmethod
 def validate_worker_count(value:int)->int:
  if value<2 or value>MAX_WORKERS:raise ValueError(f'workers must be between 2 and {MAX_WORKERS}')
  return value
 @staticmethod
 def merge_group(left:WorkerCandidate,right:WorkerCandidate)->WorkerCandidate:
  ranked=sorted((left,right),key=lambda item:(item.score,item.compatibility,item.confidence),reverse=True);merged=[];seen=set()
  for candidate in ranked:
   for mod in candidate.mods:
    identity=mod_identity(mod)
    if identity not in seen:seen.add(identity);merged.append(mod)
  overlap=len(left.keyset()&right.keyset());union=max(1,len(left.keyset()|right.keyset()));redundancy=100.0*overlap/union;unique_bonus=min(10.0,max(0,len(merged)-overlap)*0.05);synergy=min(100.0,max(left.intent_coverage,right.intent_coverage)*0.5+unique_bonus);score=(left.score+right.score)/2+unique_bonus-(redundancy*0.03)
  return WorkerCandidate(WorkerDirective(min(left.directive.index,right.directive.index),left.directive.seed^right.directive.seed,f'merged: {left.directive.focus} + {right.directive.focus}'),merged,score,max(left.intent_coverage,right.intent_coverage),min(left.compatibility,right.compatibility),min(left.performance,right.performance),min(left.dependency_quality,right.dependency_quality),(left.confidence+right.confidence)/2,f'Compared quality, compatibility, performance, dependencies, intent coverage and redundancy; preserved unique content from workers {left.directive.index} and {right.directive.index}.',left.ai_used or right.ai_used,left.fallback_reason or right.fallback_reason)
 @classmethod
 def merge_rounds(cls,candidates:list[WorkerCandidate])->tuple[WorkerCandidate,list[dict]]:
  if not candidates:raise ValueError('No worker candidates were produced')
  current=list(candidates);rounds=[]
  while len(current)>1:
   next_round=[];comparisons=[]
   for offset in range(0,len(current),2):
    if offset+1==len(current):next_round.append(current[offset]);continue
    left,right=current[offset],current[offset+1];merged=cls.merge_group(left,right);comparisons.append({'left':left.evidence(),'right':right.evidence(),'result':merged.evidence(),'decision':'preserve both and deduplicate by project identity'}) ;next_round.append(merged)
   rounds.append({'input_count':len(current),'output_count':len(next_round),'comparisons':comparisons});current=next_round
  return current[0],rounds
 async def _search(self,provider,directive,query,mc,loader):return await self.cache.get_or_fetch(f'{provider.source_id}:{mc}:{loader.value}:{query.casefold()}',lambda:provider.search(query,mc,loader,limit=50,offset=0))
 async def _worker(self,directive,prompt,mc,loader,target):
  provider=create_ai_provider();plan=None;fallback_reason=None
  try:
   try:plan=await provider.chat_json(system_prompt='You are one independent modpack worker. Return JSON with queries, rationale, intent_coverage and performance.',user_prompt=f'Request: {prompt}\nWorker {directive.index}. Focus: {directive.focus}. Seed: {directive.seed}.',schema=_WorkerPlan)
   except AIProviderError as exc:fallback_reason=str(exc)
  finally:await provider.close()
  queries=list(plan.queries) if plan else [directive.focus,prompt];candidates={}
  for catalog in self.registry.providers(available_only=True):
   for query in queries[:8]:
    hits,_=await self._search(catalog,directive,query,mc,loader)
    for mod in hits:candidates.setdefault(mod_identity(mod),mod)
  mods=list(candidates.values())[:max(target,1)];coverage=float(plan.intent_coverage if plan else 40);performance=float(plan.performance if plan else 50)
  return WorkerCandidate(directive,mods,coverage*.45+performance*.2+min(len(mods),target)/max(target,1)*35,coverage,70.0,performance,60.0,65.0 if plan else 35.0,plan.rationale if plan else 'Deterministic catalog exploration fallback.',plan is not None,fallback_reason)
 async def generate(self,prompt:str,mc:str,loader:LoaderType,workers:int,target:int=40):
  count=self.validate_worker_count(workers);focuses=('survival progression','performance stability','world generation','immersion realism','content diversity','structures exploration','automation utility','multiplayer balance');directives=[WorkerDirective(i,int(hashlib.sha256(f'{prompt}:{i}'.encode()).hexdigest()[:8],16),focuses[i%len(focuses)]) for i in range(count)];semaphore=asyncio.Semaphore(self.max_concurrency)
  async def run(directive):
   async with semaphore:return await self._worker(directive,prompt,mc,loader,target)
  candidates=await asyncio.gather(*(run(directive) for directive in directives));return self.merge_rounds(list(candidates))
class _WorkerPlan(BaseModel):
 queries:list[str]=[];rationale:str='';intent_coverage:float=50;performance:float=50
