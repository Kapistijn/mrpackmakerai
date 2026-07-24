"""Durable generation workflow with backend-owned validation and reasoning."""
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
from app.services.dependency_graph import DependencyGraphGuard,DependencyGraphLimitError
from app.services.generation_diagnostics import GenerationDiagnostics
from app.services.intent_analysis import analyze_intent,merge_ai_intent
from app.services.mod_resolver import ModResolver,mod_identity
from app.services.mod_scoring import rank_mods
from app.services.pack_assets import shader_loader_queries
from app.services.pack_profile import build_pack_profile
from app.services.pack_analysis import persist_analysis
from app.services.ai_reasoning import build_mod_memory,critique_pack,confidence_for,alternatives_for
from app.services.hardware_intelligence import selection_hints
from app.services.prompt_pipeline import optimize_prompt
from app.services.quality_scoring import rank_by_quality,select_quality
from app.services.requirements import parse_requirements,theme_matches
from app.services.intelligent_planning import build_pack_design
from app.services.self_check import fill_missing,verify_requirements
from app.services.modrinth import ModrinthClient
from app.services.source_registry import ModSourceRegistry,UnknownModSourceError
from app.services.dependency_repair import repair_project_dependencies
from app.services.compatibility import CompatibilityService
logger=logging.getLogger(__name__)
TERMINAL_STATUSES={'complete','error','cancelled'}
THEME_CATEGORIES={ThemeType.TECHNOLOGY:['technology','storage','utility'],ThemeType.ADVENTURE:['adventure','worldgen','mobs'],ThemeType.MAGIC:['magic','adventure'],ThemeType.EXPLORATION:['worldgen','adventure','utility'],ThemeType.SURVIVAL:['food','utility','storage'],ThemeType.CUSTOM:[]}
POPULAR_FALLBACK_QUERIES=['performance','utility','storage']
class AIOrchestrator:
 def __init__(self):self._active={};self._events={};self._final={}
 @staticmethod
 def _fallback_queries(project,prompt):
  base=parse_requirements(prompt,theme=project.theme,minimum_mods=project.minimum_mods,maximum_mods=project.maximum_mods,minimum_downloads=project.minimum_downloads);design=build_pack_design(base);custom=(project.theme_custom or '').strip();hints=selection_hints(project);queries=([custom] if custom else [])+list(design.search_queries or ())+list(THEME_CATEGORIES.get(ThemeType(project.theme),()))+POPULAR_FALLBACK_QUERIES+hints['prefer_queries'];return [q for q in dict.fromkeys(queries) if not any(x in q.casefold() for x in hints['avoid_queries'])]
 async def _emit(self,pid,event,run=None):
  if queue:=self._events.get(pid):await queue.put(event)
  if event.status in TERMINAL_STATUSES:self._final[pid]=event
  if run is not None:run.event_log_json=json.dumps([*json.loads(run.event_log_json or '[]'),event.model_dump(mode='json')])
 async def _gather_candidates(self,registry,resolver,queries,mc,loader,requirements=None,seed=0):
  candidates={}
  for query in dict.fromkeys([*queries[:32],'']):
   for source in registry.providers(available_only=True):
    try:hits,_=await source.search(query,mc,loader,limit=50)
    except Exception as exc:logger.warning("Search failed on %s for '%s': %s",source.source_id,query,exc);continue
    for hit in hits:
     text=' '.join((hit.name,hit.slug,hit.summary,*hit.categories))
     if requirements is None or (hit.downloads>=requirements.minimum_downloads and theme_matches(text,requirements)):candidates.setdefault(mod_identity(hit),hit)
  if requirements is None:return list(candidates.values())
  return [item.mod for item in rank_mods(list(candidates.values()),requirements,seed=seed)]
 async def generate(self,project_id:int,*,use_ai:bool=True)->None:
  queue=self._events[project_id];provider=create_ai_provider() if use_ai else None;registry=ModSourceRegistry([ModrinthClient(config.apis.modrinth_key),CurseForgeClient(config.apis.curseforge_key)]);diagnostics=GenerationDiagnostics()
  try:
   async with AsyncSessionLocal() as db:
    project=await db.get(Project,project_id)
    if not project:return
    run=GenerationRun(project_id=project_id,provider=provider.provider_id if provider else 'quick');db.add(run);project.status=ProjectStatus.GENERATING.value;await db.flush();await db.commit()
    loader,mc=LoaderType(project.loader),project.minecraft_version;prompt=project.generation_prompt or project.description;req=parse_requirements(prompt,theme=project.theme,minimum_mods=project.minimum_mods,maximum_mods=project.maximum_mods,minimum_downloads=project.minimum_downloads,target_ram_gb=project.target_ram_gb,target_fps=project.target_fps,shader_support=project.shader_support,performance_preference=project.performance_preference,visual_quality=project.shader_quality,resourcepack_support=project.resourcepack_support)
    if req.warnings:raise RuntimeError('; '.join(req.warnings))
    intent=analyze_intent(prompt,theme=project.theme,forbidden=req.forbidden_features);profile=build_pack_profile(req);hints=selection_hints(project);seed=project.id^int(datetime.now(timezone.utc).timestamp());brief=optimize_prompt(prompt,minecraft_version=mc,loader=loader.value,theme=project.theme,difficulty=project.difficulty,performance_preference=project.performance_preference);design=build_pack_design(req)
    query_parts=[self._fallback_queries(project,prompt),list(req.required_features),list(intent.categories)]
    if not hints['low_hardware']:query_parts.append(shader_loader_queries(profile,loader.value))
    queries=list(dict.fromkeys([item for part in query_parts for item in part]));target=max(req.minimum_mods or 40,min(profile.max_content_mods,req.maximum_mods or profile.max_content_mods))
    await self._emit(project_id,AIProgressEvent(step=1,message='Intent analysis and candidate search planning...',data={'intent':intent.to_dict(),'profile':profile.as_pack_info(),'hardware_hints':hints}),run)
    if use_ai and provider:
     try:
      analysis=await provider.chat_json(system_prompt=brief.system_prompt,user_prompt=brief.as_user_prompt(),schema=RequirementAnalysisSchema)
      if analysis.missing_information:raise RuntimeError('; '.join(analysis.missing_information))
      if analysis.target_mod_count:target=max(req.minimum_mods or 1,min(profile.max_content_mods,analysis.target_mod_count))
      queries=list(dict.fromkeys([*queries,*(analysis.gameplay_style or []),*(analysis.required_mods or [])]))
      try:
       ai_intent=await provider.chat_json(system_prompt=brief.system_prompt,user_prompt=brief.as_user_prompt(),schema=IntentAnalysisSchema);intent=merge_ai_intent(intent,goal=ai_intent.goal or None,categories=ai_intent.categories,avoid=ai_intent.avoid,realism_focus=ai_intent.realism_focus);queries=list(dict.fromkeys([*queries,*intent.categories]))
      except AIProviderError:pass
      gameplay=await provider.chat_json(system_prompt=brief.system_prompt,user_prompt=f'{brief.as_user_prompt()}\n{analysis.model_dump_json()}',schema=GameplayAnalysis);plan=await provider.chat_json(system_prompt=brief.system_prompt,user_prompt=f'{brief.as_user_prompt()}\n{gameplay.model_dump_json()}',schema=CategoryPlan);queries=list(dict.fromkeys([*plan.search_queries,*queries]))
     except AIProviderError as exc:logger.warning('AI planning failed: %s',exc)
    candidates=await self._gather_candidates(registry,None,queries,mc,loader,req,seed)
    if not candidates:raise RuntimeError('No compatible mods matched the selected requirements')
    selected=select_quality(rank_by_quality(candidates,intent,profile,minimum_downloads=req.minimum_downloads),target,profile)
    if hints['low_hardware']:selected=[m for m in selected if not any(x in ' '.join(m.categories).casefold() for x in ('worldgen','dimension','particle','shader'))] or selected[:1]
    memory=[build_mod_memory(m,confidence=confidence_for(m,list(intent.categories))) for m in selected]
    critique=critique_pack(selected,list(intent.categories),ram_gb=project.target_ram_gb,fps_target=project.target_fps,shader_support=project.shader_support)
    if critique['missing_categories']:
     additions=fill_missing(candidates,selected,verify_requirements(selected,intent),intent,profile);selected.extend(additions);memory.extend(build_mod_memory(m,confidence=confidence_for(m,list(intent.categories))) for m in additions)
    if req.minimum_mods and len(selected)<req.minimum_mods:raise RuntimeError('Could not select the requested minimum')
    resolved=[];pending=[(m,0) for m in selected];guard=DependencyGraphGuard();resolver=ModResolver(registry=registry);seen=set()
    while pending and len(resolved)<max(500,target*2):
     item,depth=pending.pop(0);key=resolver.mod_key(item)
     try:
      if not guard.visit(key,depth):continue
      entry=await resolver.resolve_mod(item.source,item.id,mc,loader)
     except (UnknownModSourceError,DependencyGraphLimitError):continue
     if not entry or not entry.file_name or not entry.download_url or mod_identity(entry) in seen:continue
     resolved.append(entry);seen.add(mod_identity(entry));pending.extend((ModEntry(id=d.project_id,source=d.source or entry.source,name=d.project_id),depth+1) for d in entry.dependencies if d.dependency_type in {'required','embedded'} and d.project_id)
    resolved=resolver.deduplicate(resolved)
    if req.minimum_mods and len(resolved)<req.minimum_mods:raise RuntimeError('Dependencies reduced the result below the requested minimum')
    loader_version=project.loader_version or await resolver.resolve_loader_version(loader,mc)
    if not loader_version:raise RuntimeError(f'No compatible {loader.value} loader version found')
    project.mods_json=json.dumps([m.model_dump(mode='json') for m in resolved]);project.resolved_loader_version=loader_version;project.status=ProjectStatus.REVIEW.value;project.ai_summary=f'Designed {project.theme} pack: {len(resolved)} mods';run.status='completed';run.summary=project.ai_summary;run.completed_at=datetime.now(timezone.utc)
    repair_status=await repair_project_dependencies(project,db);compatibility=CompatibilityService(ModrinthClient(config.apis.modrinth_key),CurseForgeClient(config.apis.curseforge_key))
    try:compatibility_report=await compatibility.check_project(project)
    finally:await compatibility.close()
    if not compatibility_report.export_ready:raise RuntimeError('Compatibility gate failed: '+'; '.join(compatibility_report.errors))
    await persist_analysis(db,project,'generation');await db.commit();await self._emit(project_id,AIProgressEvent(step=7,message=f'Generation complete: {len(resolved)} mods.',status='complete',data={'mod_count':len(resolved),'dependency_repair':repair_status,'compatibility':compatibility_report.model_dump(mode='json'),'hardware_hints':hints,'mod_memory':memory,'critique':critique}),run)
  except asyncio.CancelledError:await self._mark_failed(project_id,'Cancelled by user');await self._emit(project_id,AIProgressEvent(step=0,message='Generation cancelled.',status='cancelled'));raise
  except Exception as exc:logger.exception('Generation failed for project %d',project_id);await self._mark_failed(project_id,str(exc));await self._emit(project_id,AIProgressEvent(step=0,message=f'Generation failed: {exc}',status='error'))
  finally:
   if provider is not None:await provider.close()
   await registry.close();await queue.put(None);self._active.pop(project_id,None);self._events.pop(project_id,None)
 async def _mark_failed(self,project_id,message):
  async with AsyncSessionLocal() as db:
   project=await db.get(Project,project_id)
   if project:project.status=ProjectStatus.DRAFT.value
   from sqlalchemy import select
   run=(await db.execute(select(GenerationRun).where(GenerationRun.project_id==project_id,GenerationRun.status=='running').order_by(GenerationRun.started_at.desc()))).scalars().first()
   if run:run.status='failed';run.error=message[:4000];run.completed_at=datetime.now(timezone.utc)
   await db.commit()
 def start_generation(self,project_id,*,use_ai=True):
  if self.is_active(project_id):raise RuntimeError('Generation already in progress')
  self._final.pop(project_id,None);self._events[project_id]=asyncio.Queue();self._active[project_id]=asyncio.create_task(self.generate(project_id,use_ai=use_ai))
 def is_active(self,project_id):return bool(self._active.get(project_id) and not self._active[project_id].done())
 async def stream_events(self,project_id)->AsyncGenerator[AIProgressEvent,None]:
  queue=self._events.get(project_id)
  if queue is None:
   if final:=self._final.pop(project_id,None):yield final
   return
  while True:
   event=await queue.get()
   if event is None:break
   yield event
 def cancel(self,project_id):
  task=self._active.get(project_id)
  if task and not task.done():task.cancel();return True
  return False
orchestrator=AIOrchestrator()
