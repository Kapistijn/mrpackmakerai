"""Durable, requirement-driven generation workflow."""
from __future__ import annotations
import asyncio,json,logging
from collections.abc import AsyncGenerator
from datetime import datetime,timezone
from app.config import config
from app.db.session import AsyncSessionLocal
from app.models.enums import LoaderType,ProjectStatus,ThemeType
from app.models.generation import GenerationRun
from app.models.project import Project
from app.schemas.ai import AIProgressEvent,CategoryPlan,GameplayAnalysis,IntentAnalysisSchema,RequirementAnalysisSchema
from app.services.ai_provider import AIProviderError,create_ai_provider
from app.services.curseforge import CurseForgeClient
from app.services.discovery_strategy import DiscoveryPlan,build_discovery_plan
from app.services.intent_analysis import analyze_intent,merge_ai_intent
from app.services.mod_resolver import ModResolver,mod_identity
from app.services.pack_assets import ensure_shader_loader,shader_loader_queries,is_shader_loader
from app.services.pack_profile import build_pack_profile
from app.services.prompt_pipeline import optimize_prompt
from app.services.quality_scoring import rank_by_quality,select_quality
from app.services.requirements import parse_requirements,theme_matches,mod_matches_constraint
from app.services.intelligent_planning import build_pack_design,review_pack
from app.services.self_check import fill_missing,verify_requirements
from app.services.modrinth import ModrinthClient
from app.services.source_registry import ModSourceRegistry,UnknownModSourceError
logger=logging.getLogger(__name__)
TERMINAL_STATUSES={'complete','error','cancelled'}
THEME_CATEGORIES={ThemeType.TECHNOLOGY:['technology','storage','utility'],ThemeType.ADVENTURE:['adventure','worldgen','mobs'],ThemeType.MAGIC:['magic','adventure'],ThemeType.EXPLORATION:['worldgen','adventure','utility'],ThemeType.SURVIVAL:['food','utility','storage'],ThemeType.CUSTOM:[]}
POPULAR_FALLBACK_QUERIES=['performance','utility','storage']
class AIOrchestrator:
 def __init__(self):self._active={};self._events={};self._final={}
 @staticmethod
 def _fallback_queries(project,prompt):
  base=parse_requirements(prompt,theme=project.theme,minimum_mods=project.minimum_mods,maximum_mods=project.maximum_mods,minimum_downloads=project.minimum_downloads,required_mods=json.loads(getattr(project,'required_mods_json','[]') or '[]'),forbidden_mods=json.loads(getattr(project,'forbidden_mods_json','[]') or '[]'));design=build_pack_design(base);custom=(project.theme_custom or '').strip();return list(dict.fromkeys(([custom] if custom else [])+list(design.search_queries)+THEME_CATEGORIES.get(ThemeType(project.theme),[])+POPULAR_FALLBACK_QUERIES+list(base.constraint.required_mods)))
 async def _emit(self,pid,event,run=None):
  if queue:=self._events.get(pid):await queue.put(event)
  if event.status in TERMINAL_STATUSES:self._final[pid]=event
  if run is not None:run.event_log_json=json.dumps([*json.loads(run.event_log_json or '[]'),event.model_dump(mode='json')])
 async def _gather_candidates(self, registry, resolver_or_queries, queries_or_mc, mc_or_loader, loader_or_requirements=None, requirements=None, plan=None):
  """Gather candidates with the old beta13 call shape still supported.

  Legacy callers pass (registry, resolver, queries, mc, loader); the current
  pipeline passes (registry, queries, mc, loader, requirements, plan). The
  resolver was never needed by this stage, so it remains accepted for API
  compatibility without changing the new pipeline.
  """
  if isinstance(resolver_or_queries, (list, tuple)):
   queries=list(resolver_or_queries);mc=queries_or_mc;loader=mc_or_loader;requirements=loader_or_requirements or parse_requirements('');plan=plan or build_discovery_plan(50,'medium')
  else:
   queries=list(queries_or_mc);mc=mc_or_loader;loader=loader_or_requirements;requirements=requirements or parse_requirements('');plan=plan or build_discovery_plan(50,'medium')
  candidates={};search_queries=queries if plan.include_queries else queries[:4]
  for query in list(dict.fromkeys([*search_queries,''])):
   for offset in plan.offsets:
    for source in registry.providers(available_only=True):
     try:hits,_=await source.search(query,mc,loader,limit=plan.limit,offset=offset)
     except Exception as exc:logger.warning('Search failed on %s for %r at offset %s: %s',source.source_id,query,offset,exc);continue
     for hit in hits:
      text=' '.join((hit.name,hit.slug,hit.summary,*hit.categories))
      if hit.downloads<requirements.minimum_downloads or not theme_matches(text,requirements):continue
      if any(mod_matches_constraint(hit,item) for item in requirements.constraint.forbidden_mods):continue
      candidates.setdefault(mod_identity(hit),hit)
  return list(candidates.values())
 async def generate(self,project_id:int,*,use_ai=True)->None:
  queue=self._events[project_id];provider=create_ai_provider() if use_ai else None;registry=ModSourceRegistry([ModrinthClient(config.apis.modrinth_key),CurseForgeClient(config.apis.curseforge_key)]);resolver=ModResolver(registry=registry)
  try:
   async with AsyncSessionLocal() as db:
    project=await db.get(Project,project_id)
    if not project:return
    run=GenerationRun(project_id=project_id,provider=provider.provider_id if provider else 'quick');db.add(run);project.status=ProjectStatus.GENERATING.value;await db.flush();await db.commit();loader,mc=LoaderType(project.loader),project.minecraft_version;prompt=project.generation_prompt or project.description
    requirements=parse_requirements(prompt,theme=project.theme,minimum_mods=project.minimum_mods,maximum_mods=project.maximum_mods,minimum_downloads=project.minimum_downloads,target_ram_gb=getattr(project,'target_ram_gb',None),target_fps=getattr(project,'target_fps',None),shader_support=getattr(project,'shader_support',None),performance_preference=project.performance_preference,visual_quality=getattr(project,'shader_quality',None),resourcepack_support=getattr(project,'resourcepack_support',False),required_mods=json.loads(getattr(project,'required_mods_json','[]') or '[]'),forbidden_mods=json.loads(getattr(project,'forbidden_mods_json','[]') or '[]'))
    if requirements.warnings:raise RuntimeError('; '.join(requirements.warnings))
    intent=analyze_intent(prompt,theme=project.theme,forbidden=requirements.forbidden_features);profile=build_pack_profile(requirements);plan=build_discovery_plan(getattr(project,'ai_creativity',50),getattr(project,'discovery_depth','medium'));brief=optimize_prompt(prompt,minecraft_version=mc,loader=loader.value,theme=project.theme,difficulty=project.difficulty,performance_preference=project.performance_preference);design=build_pack_design(requirements);queries=list(dict.fromkeys(self._fallback_queries(project,prompt)+list(requirements.required_features)+list(intent.categories)+shader_loader_queries(profile,loader.value)))
    await self._emit(project_id,AIProgressEvent(step=1,message='Analyzing intent and configuration...',data={'intent':intent.to_dict(),'profile':profile.as_pack_info(),'discovery':plan.__dict__}),run)
    if use_ai and provider:
     try:
      analysis=await provider.chat_json(system_prompt=brief.system_prompt,user_prompt=brief.as_user_prompt(),schema=RequirementAnalysisSchema)
      if analysis.missing_information:raise RuntimeError(f'Missing required information: {"; ".join(analysis.missing_information)}')
      await self._emit(project_id,AIProgressEvent(step=2,message='Understanding requirements...',data=analysis.model_dump(mode='json')),run);queries=list(dict.fromkeys(queries+analysis.gameplay_style+analysis.required_mods+analysis.forbidden_mods));ai_intent=await provider.chat_json(system_prompt=brief.system_prompt+'\nReturn machine-readable intent only.',user_prompt=f'{brief.as_user_prompt()}\nDeterministic intent: {json.dumps(intent.to_dict())}',schema=IntentAnalysisSchema);intent=merge_ai_intent(intent,goal=ai_intent.goal,categories=ai_intent.categories,avoid=ai_intent.avoid,realism_focus=ai_intent.realism_focus);queries=list(dict.fromkeys(queries+list(intent.categories)));gameplay=await provider.chat_json(system_prompt=brief.system_prompt,user_prompt=f'{brief.as_user_prompt()}\nDesign: {design}\nAnalysis: {analysis.model_dump_json()}',schema=GameplayAnalysis);plan_ai=await provider.chat_json(system_prompt=brief.system_prompt,user_prompt=f'{brief.as_user_prompt()}\nDesign: {design}\nAnalysis: {gameplay.model_dump_json()}',schema=CategoryPlan);queries=list(dict.fromkeys(queries+plan_ai.search_queries))
     except AIProviderError as exc:logger.warning('AI unavailable, using deterministic fallback: %s',exc)
    else:await self._emit(project_id,AIProgressEvent(step=2,message='Using deterministic fallback...',data={'intent':intent.to_dict()}),run)
    await self._emit(project_id,AIProgressEvent(step=3,message='Searching catalog with configured discovery depth...'),run);candidates=await self._gather_candidates(registry,queries,mc,loader,requirements,plan);required_missing=[item for item in requirements.constraint.required_mods if not any(mod_matches_constraint(m,item) for m in candidates)]
    if required_missing:raise RuntimeError('Required mod(s) not found or incompatible: '+', '.join(required_missing))
    if not candidates:raise RuntimeError('No compatible mods matched the selected requirements')
    await self._emit(project_id,AIProgressEvent(step=4,message='Scoring intent, quality and performance cost...'),run);target=max(requirements.minimum_mods or 40,min(profile.max_content_mods,requirements.maximum_mods or profile.max_content_mods));ranked=rank_by_quality(candidates,intent,profile,minimum_downloads=requirements.minimum_downloads);selected=select_quality(ranked,target,profile)
    for required in requirements.constraint.required_mods:
     forced=next((m for m in candidates if mod_matches_constraint(m,required)),None)
     if forced and forced not in selected:selected.append(forced)
    if profile.shader_mode!='off':
     selected=ensure_shader_loader(candidates,profile)[:max(len(selected),1)] if any(is_shader_loader(m) for m in candidates) else selected
     if not any(is_shader_loader(m) for m in selected):raise RuntimeError('Shader support requires a compatible Iris/Oculus loader, but none was found')
    check=verify_requirements(selected,intent)
    if not check.complete:selected.extend(fill_missing(candidates,selected,check,intent,profile));check=verify_requirements(selected,intent)
    if not check.complete:raise RuntimeError('Intent requirements not satisfied: '+', '.join(check.missing))
    await self._emit(project_id,AIProgressEvent(step=5,message='Resolving dependencies and compatibility...'),run);resolved=[];pending=[resolver.mod_key(m) for m in selected];seen=set()
    while pending and len(resolved)<max(300,(requirements.maximum_mods or 40)*2):
     key=pending.pop(0)
     if key in seen:continue
     seen.add(key)
     try:entry=await resolver.resolve_mod_by_key(key,mc,loader)
     except UnknownModSourceError:continue
     if not entry or not entry.file_name or not entry.download_url:continue
     if mod_identity(entry) in {mod_identity(m) for m in resolved}:continue
     if any(mod_matches_constraint(entry,x) for x in requirements.constraint.forbidden_mods):raise RuntimeError(f'Forbidden mod selected as dependency: {entry.name}')
     resolved.append(entry);pending += [f'{d.source or entry.source}:{d.project_id}' for d in entry.dependencies if d.dependency_type in {'required','embedded'} and d.project_id]
    resolved=resolver.deduplicate(resolved)
    for required in requirements.constraint.required_mods:
     if not any(mod_matches_constraint(m,required) for m in resolved):raise RuntimeError(f'Required mod {required} could not be resolved for {mc}/{loader.value}')
    final_check=verify_requirements(resolved,intent);quality=review_pack(resolved,requirements);await self._emit(project_id,AIProgressEvent(step=6,message='Self-checking intent, assets and compatibility...',data={'quality_score':quality.overall,'requirement_check':final_check.to_dict(),'profile':profile.as_pack_info()}),run)
    if not final_check.complete:raise RuntimeError('Final intent check failed: '+', '.join(final_check.missing))
    if quality.compatibility<1:raise RuntimeError('Self-review found unresolved downloadable-file compatibility issues')
    loader_version=project.loader_version or await resolver.resolve_loader_version(loader,mc)
    if not loader_version:raise RuntimeError(f'No compatible {loader.value} loader version found')
    project.mods_json=json.dumps([m.model_dump(mode='json') for m in resolved]);project.resolved_loader_version=loader_version;project.ai_summary=f'Designed {intent.goal}: {len(resolved)} mods, coverage {len(final_check.satisfied)}/{len(intent.categories)}';project.status=ProjectStatus.REVIEW.value;run.status='completed';run.summary=project.ai_summary;run.completed_at=datetime.now(timezone.utc);await self._emit(project_id,AIProgressEvent(step=7,message=f'Generation complete: {len(resolved)} mods.',status='complete',data={'mod_count':len(resolved),'requirement_check':final_check.to_dict()}),run);await db.commit()
  except asyncio.CancelledError:await self._mark_cancelled(project_id);raise
  except Exception as exc:logger.exception('Generation failed for project %d',project_id);await self._mark_failed(project_id,str(exc));await self._emit(project_id,AIProgressEvent(step=0,message=f'Generation failed: {exc}',status='error'))
  finally:
   if provider:await provider.close()
   await registry.close();await queue.put(None);self._active.pop(project_id,None);self._events.pop(project_id,None)
 async def _mark_failed(self,pid,msg):
  async with AsyncSessionLocal() as db:
   project=await db.get(Project,pid)
   if project:project.status=ProjectStatus.DRAFT.value
   from sqlalchemy import select
   run=(await db.execute(select(GenerationRun).where(GenerationRun.project_id==pid,GenerationRun.status=='running').order_by(GenerationRun.started_at.desc()))).scalars().first()
   if run:run.status='failed';run.error=msg[:4000];run.completed_at=datetime.now(timezone.utc)
   await db.commit()
 async def _mark_cancelled(self,pid):await self._mark_failed(pid,'Cancelled by user')
 def start_generation(self,pid,*,use_ai=True):
  if self.is_active(pid):raise RuntimeError('Generation already in progress')
  self._final.pop(pid,None);self._events[pid]=asyncio.Queue();self._active[pid]=asyncio.create_task(self.generate(pid,use_ai=use_ai))
 def is_active(self,pid):return bool(self._active.get(pid) and not self._active[pid].done())
 async def stream_events(self,pid)->AsyncGenerator[AIProgressEvent,None]:
  queue=self._events.get(pid)
  if queue is None:
   if final:=self._final.pop(pid,None):yield final
   return
  while True:
   event=await queue.get()
   if event is None:break
   yield event
 def cancel(self,pid):
  task=self._active.get(pid)
  if task and not task.done():task.cancel();return True
  return False
orchestrator=AIOrchestrator()
