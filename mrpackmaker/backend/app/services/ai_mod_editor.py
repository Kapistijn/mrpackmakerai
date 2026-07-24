from __future__ import annotations
import json
from app.config import config
from app.models.enums import LoaderType,ProjectStatus
from app.services.change_planner import plan_change
from app.services.mod_discovery import discover
from app.services.mod_resolver import ModResolver,mod_identity
from app.services.dependency_resolver import DependencyResolver
from app.services.source_registry import create_default_registry
from app.services.ai_provider import AIProviderError,create_ai_provider
from app.schemas.editor import AIChangePlan
from app.schemas.mod import ModEntry
async def propose(project,prompt):
 current=[ModEntry.model_validate(x) for x in json.loads(project.mods_json or '[]')];fallback=plan_change(prompt,current);ai_used=False;fallback_reason=None;plan=fallback.to_dict()
 provider=create_ai_provider()
 try:
  current_names=', '.join(m.name for m in current[:80]) or 'empty pack'
  instruction=f'''Create a safe, approval-gated modpack change plan. User request: {prompt}\nCurrent mods: {current_names}\nReturn only the requested typed JSON fields. Never invent mod IDs. Use add_queries for catalog searches and remove_names only for exact current names.'''
  result=await provider.chat_json(system_prompt='You are a cautious Minecraft modpack change planner. Be explicit about uncertainty and never claim a change was applied.',user_prompt=instruction,schema=AIChangePlan)
  plan=result.model_dump(mode='json');plan['requires_approval']=True;ai_used=True
 except AIProviderError as exc:
  fallback_reason=f'AI unavailable: {exc}'
 finally:
  await provider.close()
 registry=create_default_registry()
 try:
  candidates=await discover(registry,plan.get('add_queries',[]),project)
  return {'plan':plan,'current_count':len(current),'recommendations':[m.model_dump(mode='json') for m in candidates],'alternatives':[m.name for m in candidates[1:4]],'ai_used':ai_used,'fallback_used':not ai_used,'fallback_reason':fallback_reason}
 finally:await registry.close()
async def apply(project,prompt,approved_plan,db):
 current=[ModEntry.model_validate(x) for x in json.loads(project.mods_json or '[]')];remove=set(approved_plan.get('remove_names',[]));kept=[m for m in current if m.name not in remove];registry=create_default_registry();resolver=None
 try:
  candidates=await discover(registry,approved_plan.get('add_queries',[]),project);existing={mod_identity(m) for m in kept};additions=[m for m in candidates if mod_identity(m) not in existing][:10];resolver=ModResolver(registry=registry);result=await DependencyResolver(resolver).resolve_pack(kept+additions,project.minecraft_version,LoaderType(project.loader))
  if not result.complete:raise ValueError('; '.join(f.message() for f in result.failures))
  project.mods_json=json.dumps([m.model_dump(mode='json') for m in result.mods]);project.mrpack_path=None;project.status=ProjectStatus.REVIEW.value
  return list(result.mods),additions,[m for m in current if m.name in remove]
 finally:
  if resolver is not None:await resolver.close()
  else:await registry.close()
