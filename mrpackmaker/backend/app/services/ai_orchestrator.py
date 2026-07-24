"""Durable, requirement-driven generation workflow with a transactional validation gate."""
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
from app.services.hardware_intelligence import selection_hints
from app.services.prompt_pipeline import optimize_prompt
from app.services.quality_scoring import rank_by_quality,select_quality
from app.services.requirements import parse_requirements,theme_matches
from app.services.intelligent_planning import build_pack_design,review_pack
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
  base=parse_requirements(prompt,theme=project.theme,minimum_mods=project.minimum_mods,maximum_mods=project.maximum_mods,minimum_downloads=project.minimum_downloads);design=build_pack_design(base);custom=(project.theme_custom or '').strip();hints=selection_hints(project);queries=([custom] if custom else [])+list(design.search_queries or ())+list(THEME_CATEGORIES.get(ThemeType(project.theme),()))+list(POPULAR_FALLBACK_QUERIES)+hints['prefer_queries'];return [q for q in dict.fromkeys(queries) if not any(block in q.casefold() for block in hints['avoid_queries'])]
 async def _emit(self,project_id,event,run=None):
  if queue:=self._events.get(project_id):await queue.put(event)
  if event.status in TERMINAL_STATUSES:self._final[project_id]=event
  if run is not None:history=json.loads(run.event_log_json or '[]');history.append(event.model_dump(mode='json'));run.event_log_json=json.dumps(history)
 async def _gather_candidates(self,registry,resolver,queries,mc_version,loader,requirements=None,*,seed=0):
  candidates={}
  for query in list(dict.fromkeys([*queries[:32],''])):
   for source in registry.providers(available_only=True):
    try:hits,_=await source.search(query,mc_version,loader,limit=50)
    except Exception as exc:logger.warning("Search failed on %s for '%s': %s",source.source_id,query,exc);continue
    for hit in hits:
     text=' '.join((hit.name,hit.slug,hit.summary,*hit.categories))
     if requirements is None or (hit.downloads>=requirements.minimum_downloads and theme_matches(text,requirements)):candidates.setdefault(mod_identity(hit),hit)
  if requirements is None:return list(candidates.values())
  return [item.mod for item in rank_mods(list(candidates.values()),requirements,seed=seed) if item.score>=0]
 async def generate(self,project_id:int,*,use_ai:bool=True)->None:
  queue=self._events[project_id];provider=create_ai_provider() if use_ai else None;registry=ModSourceRegistry([ModrinthClient(config.apis.modrinth_key),CurseForgeClient(config.apis.curseforge_key)]);resolver=ModResolver(registry=registry);diagnostics=GenerationDiagnostics()
  try:
   async with AsyncSessionLocal() as db:
    project=await db.get(Project,project_id)
    if not project:return
    run=GenerationRun(project_id=project_id,provider=provider.provider_id if provider else 'quick');db.add(run);project.status=ProjectStatus.GENERATING.value;await db.flush();await db.commit()
    loader,mc_version=LoaderType(project.loader),project.minecraft_version;prompt=project.generation_prompt or project.description;requirements=parse_requirements(prompt,theme=project.theme,minimum_mods=project.minimum_mods,maximum_mods=project.maximum_mods,minimum_downloads=project.minimum_downloads,target_ram_gb=project.target_ram_gb,target_fps=project.target_fps,shader_support=project.shader_support,performance_preference=project.performance_preference,visual_quality=project.shader_quality,resourcepack_support=project.resourcepack_support)
    if requirements.warnings:raise RuntimeError('; '.join(requirements.warnings))
    diagnostics.requested=requirements.minimum_mods or requirements.maximum_mods;intent=analyze_intent(prompt,theme=project.theme,forbidden=requirements.forbidden_features);profile=build_pack_profile(requirements);seed=project.id^int(datetime.now(timezone.utc).timestamp());brief=optimize_prompt(prompt,minecraft_version=mc_version,loader=loader.value,theme=project.theme,difficulty=project.difficulty,performance_preference=project.performance_preference);design=build_pack_design(requirements);hints=selection_hints(project);target_count=max(requirements.minimum_mods or 40,min(profile.max_content_mods,requirements.maximum_mods or profile.max_content_mods));queries=list(dict.fromkeys(self._fallback_queries(project,prompt)+list(requirements.required_features)+list(intent.categories)+([] if hints['low_hardware'] else list(shader_loader_queries(profile,loader.value))))
    await self._emit(project_id,AIProgressEvent(step=1,message='Analyzing intent and designing the pack vision...',data={'intent':intent.to_dict(),'profile':profile.as_pack_info(),'hardware_hints':hints,'vision':design.vision,'gameplay_loop':design.gameplay_loop}),run)
    if use_ai and provider is not None:
     try:
      analysis=await provider.chat_json(system_prompt=brief.system_prompt+'\nReason through player experience before selecting mods. Return structured requirements only; never invent missing information.',user_prompt=brief.as_user_prompt(),schema=RequirementAnalysisSchema)
      if analysis.missing_information:raise RuntimeError(f"Missing required information: {'; '.join(analysis.missing_information)}")
      await self._emit(project_id,AIProgressEvent(step=2,message='Understanding requirements and planning categories...',data=analysis.model_dump(mode='json')),run)
      if analysis.target_mod_count:target_count=max(requirements.minimum_mods or 1,min(profile.max_content_mods,analysis.target_mod_count))
      queries=list(dict.fromkeys([*queries,*(analysis.gameplay_style or []),*(analysis.required_mods or [])]))
      try:
       ai_intent=await provider.chat_json(system_prompt=brief.system_prompt+'\nReturn a machine-readable intent analysis (goal, categories, avoid).',user_prompt=f'{brief.as_user_prompt()}\nDeterministic intent: {json.dumps(intent.to_dict())}',schema=IntentAnalysisSchema);intent=merge_ai_intent(intent,goal=ai_intent.goal or None,categories=ai_intent.categories,avoid=ai_intent.avoid,realism_focus=ai_intent.realism_focus);queries=list(dict.fromkeys([*queries,*intent.categories]))
      except AIProviderError as exc:logger.warning('AI intent enrichment failed; deterministic intent remains active: %s',exc)
      gameplay=await provider.chat_json(system_prompt=brief.system_prompt,user_prompt=f'{brief.as_user_prompt()}\nDesign: {design}\nStructured analysis: {analysis.model_dump_json()}',schema=GameplayAnalysis);plan=await provider.chat_json(system_prompt=brief.system_prompt,user_prompt=f'{brief.as_user_prompt()}\nDesign: {design}\nAnalysis: {gameplay.model_dump_json()}',schema=CategoryPlan)
      if plan.search_queries:queries=list(dict.fromkeys([*plan.search_queries,*queries]))
     except AIProviderError as exc:logger.warning('AI planning failed; deterministic design remains active: %s',exc)
    else:await self._emit(project_id,AIProgressEvent(step=2,message='Using deterministic design plan...',data={'intent':intent.to_dict(),'categories':design.categories}),run)
    await self._emit(project_id,AIProgressEvent(step=3,message='Searching planned categories and expanded queries...'),run);candidates=await self._gather_candidates(registry,resolver,queries,mc_version,loader,requirements,seed=seed);diagnostics.found=len(candidates)
    if requirements.minimum_mods is not None and len(candidates)<requirements.minimum_mods:raise RuntimeError('Not enough compatible candidates for the requested minimum')
    if not candidates:raise RuntimeError('No compatible mods matched the selected requirements')
    await self._emit(project_id,AIProgressEvent(step=4,message='Scoring intent, realism, compatibility and performance cost...'),run);ranked=rank_by_quality(candidates,intent,profile,minimum_downloads=requirements.minimum_downloads);selected=select_quality(ranked,target_count,profile)
    if hints['low_hardware']:selected=[m for m in selected if not any(x in ' '.join(m.categories).casefold() for x in ('worldgen','dimension','particle','shader'))] or selected[:1]
    if requirements.minimum_mods is not None and len(selected)<requirements.minimum_mods:
     for score in ranked:
      if len(selected)>=requirements.minimum_mods:break
      if all((m.source,m.id)!=(score.mod.source,score.mod.id) for m in selected):selected.append(score.mod)
    if requirements.minimum_mods is not None and len(selected)<requirements.minimum_mods:raise RuntimeError('Could not select the requested minimum')
    check=verify_requirements(selected,intent)
    if not check.complete:
     additions=fill_missing(candidates,selected,check,intent,profile)
     if additions:selected=selected+additions;check=verify_requirements(selected,intent)
    await self._emit(project_id,AIProgressEvent(step=5,message='Resolving dependencies with safe graph limits...'),run);resolved_mods=[];resolved_keys=set();pending=[(resolver.mod_key(item),0) for item in selected];guard=DependencyGraphGuard()
    while pending and len(resolved_mods)<max(500,target_count*2):
     key,depth=pending.pop(0)
     try:
      if not guard.visit(key,depth):continue
      entry=await resolver.resolve_mod_by_key(key,mc_version,loader)
     except DependencyGraphLimitError as exc:raise RuntimeError(str(exc)) from exc
     except UnknownModSourceError:diagnostics.skip('unknown_source');continue
     if not entry or not entry.file_name or not entry.download_url:diagnostics.skip('unavailable_or_incompatible');continue
     if mod_identity(entry) in {mod_identity(item) for item in resolved_mods}:diagnostics.skip('duplicate');continue
     resolved_mods.append(entry);resolved_keys.add(key)
     for dep in entry.dependencies:
      if dep.dependency_type in {'required','embedded'} and dep.project_id:
       dep_key=f'{dep.source or entry.source}:{dep.project_id}'
       if dep_key not in resolved_keys:pending.append((dep_key,depth+1))
    resolved_mods=resolver.deduplicate(resolved_mods);diagnostics.found=len(resolved_mods)
    if requirements.minimum_mods is not None and len(resolved_mods)<requirements.minimum_mods:raise RuntimeError(f'Dependencies reduced the result below the requested minimum ({len(resolved_mods)}/{requirements.minimum_mods}); diagnostics: {json.dumps(diagnostics.snapshot())}')
    quality=review_pack(resolved_mods,requirements);final_check=verify_requirements(resolved_mods,intent)
    if quality.compatibility<1:raise RuntimeError('Self-review found unresolved downloadable-file compatibility issues')
    loader_version=project.loader_version or await resolver.resolve_loader_version(loader,mc_version)
    if not loader_version:raise RuntimeError(f'No compatible {loader.value} loader version found')
    project.mods_json=json.dumps([mod.model_dump(mode='json') for mod in resolved_mods]);project.resolved_loader_version=loader_version;project.ai_summary=f'Designed {project.theme} pack ({intent.goal}): {len(resolved_mods)} mods, quality {quality.overall:.2f}, coverage {len(final_check.satisfied)}/{len(intent.categories) or 0}.';project.status=ProjectStatus.REVIEW.value;run.status='completed';run.summary=project.ai_summary;run.completed_at=datetime.now(timezone.utc)
    repair_status=await repair_project_dependencies(project,db)
    compatibility=CompatibilityService(ModrinthClient(config.apis.modrinth_key),CurseForgeClient(config.apis.curseforge_key))
    try:compatibility_report=await compatibility.check_project(project)
    finally:await compatibility.close()
    if not compatibility_report.export_ready:raise RuntimeError('Compatibility gate failed: '+('; '.join(compatibility_report.errors)))
    await persist_analysis(db,project,'generation');await db.commit()
    await self._emit(project_id,AIProgressEvent(step=7,message=f'Generation complete: {len(resolved_mods)} mods.',status='complete',data={'mod_count':len(resolved_mods),'target_count':target_count,'quality_score':quality.overall,'requirement_check':final_check.to_dict(),'compatibility':compatibility_report.model_dump(mode='json'),'dependency_repair':repair_status,'hardware_hints':hints,'seed':seed}),run)
   finally:await db.close()
  except asyncio.CancelledError:await self._mark_cancelled(project_id);await self._emit(project_id,AIProgressEvent(step=0,message='Generation cancelled.',status='cancelled'));raise
  except Exception as exc:logger.exception('Generation failed for project %d',project_id);await self._mark_failed(project_id,str(exc));await self._emit(project_id,AIProgressEvent(step=0,message=f'Generation failed: {exc}',status='error',data={'diagnostics':diagnostics.snapshot()}))
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
 async def _mark_cancelled(self,project_id):await self._mark_failed(project_id,'Cancelled by user')
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