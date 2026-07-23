from __future__ import annotations
from app.schemas.mod import ModEntry
from app.services.mod_resolver import mod_identity
from app.services.quality_scoring import rank_by_quality
from app.services.intent_analysis import analyze_intent
from app.services.pack_profile import build_pack_profile
from app.services.requirements import parse_requirements
async def discover(registry,queries,project,limit=30):
 req=parse_requirements(project.generation_prompt or project.description,theme=project.theme,target_ram_gb=getattr(project,'target_ram_gb',None),target_fps=getattr(project,'target_fps',None),shader_support=getattr(project,'shader_support',None),performance_preference=project.performance_preference)
 intent=analyze_intent(' '.join(queries),theme=project.theme);profile=build_pack_profile(req);found={}
 for query in dict.fromkeys(queries):
  for source in registry.providers(available_only=True):
   try:hits,_=await source.search(query,project.minecraft_version,project.loader,limit=limit)
   except Exception:continue
   for hit in hits:found.setdefault(mod_identity(hit),hit)
 return [s.mod for s in rank_by_quality(list(found.values()),intent,profile)[:limit]]
