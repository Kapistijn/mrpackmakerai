"""Compatibility report builder and export gate."""
from __future__ import annotations
import json,logging
from app.models.enums import LoaderType
from app.models.project import Project
from app.schemas.compatibility import CompatCheckItem,CompatStatus,CompatibilityMetrics,CompatibilityReport
from app.schemas.mod import ModEntry
from app.services.advanced_compatibility import check_advanced
from app.services.curseforge import CurseForgeClient
from app.services.dependency_graph import DependencyGraph
from app.services.mod_resolver import ModResolver,mod_identity
from app.services.modrinth import ModrinthClient
from app.services.mrpack_validation import validate_export_inputs
from app.services.source_registry import UnknownModSourceError
logger=logging.getLogger(__name__)
REQUIRED_LIBRARIES={LoaderType.FABRIC:['fabric-api'],LoaderType.FORGE:[],LoaderType.NEOFORGE:[]}
class CompatibilityService:
 def __init__(self,modrinth:ModrinthClient,curseforge:CurseForgeClient)->None:self.resolver=ModResolver(modrinth,curseforge)
 async def check_project(self,project:Project)->CompatibilityReport:
  selected=[ModEntry.model_validate(x) for x in json.loads(project.mods_json or '[]')];loader=LoaderType(project.loader);graph=DependencyGraph();mod_items=[];errors=[];resolved=[]
  for mod in selected:
   try:fresh=await self.resolver.resolve_mod(mod.source,mod.id,project.minecraft_version,loader)
   except UnknownModSourceError:fresh=None;errors.append(f'{mod.name} uses an unknown source: {mod.source}')
   if fresh and fresh.file_name and fresh.download_url:resolved.append(fresh);graph.add_mod(fresh);mod_items.append(CompatCheckItem(name=fresh.name,status=CompatStatus.OK,message='Version and loader match'))
   else:errors.append(f'{mod.name} has no compatible {project.minecraft_version} {loader.value} file');mod_items.append(CompatCheckItem(name=mod.name,status=CompatStatus.ERROR,message='No compatible file'))
  identities=[mod_identity(x) for x in selected];duplicate_count=len(identities)-len(set(identities))
  if duplicate_count:errors.append(f'{duplicate_count} duplicate project(s) detected across catalog sources')
  deps=[];missing=[]
  for library in REQUIRED_LIBRARIES[loader]:
   if not any(library in m.slug.lower() or library in m.name.lower() for m in resolved):missing.append(library);errors.append(f'Missing required library: {library}');deps.append(CompatCheckItem(name=library,status=CompatStatus.ERROR,message='Missing required library'))
  for key in graph.get_missing_required():errors.append(f'Missing required dependency: {key}');deps.append(CompatCheckItem(name=key,status=CompatStatus.ERROR,message='Missing required dependency'))
  present=set(graph.nodes)
  for key in sorted(graph.get_all_dependency_keys()&present):deps.append(CompatCheckItem(name=key,status=CompatStatus.OK,message='Present'))
  conflicts=[]
  for left,right in graph.get_conflicts():errors.append(f'Incompatible mods: {left} and {right}');conflicts.append(CompatCheckItem(name=f'{left} ↔ {right}',status=CompatStatus.ERROR,message='Declared incompatible'))
  if not conflicts:conflicts=[CompatCheckItem(name='none',status=CompatStatus.OK,message='No declared conflicts')]
  errors.extend(i.message for i in validate_export_inputs(project,resolved));configuration,advanced_errors,warnings=check_advanced(project,resolved);errors.extend(advanced_errors)
  download_size=sum(m.file_size or 0 for m in resolved);metrics=CompatibilityMetrics(minecraft_version=project.minecraft_version,loader=loader.value,loader_version=project.loader_version or project.resolved_loader_version,dependency_count=sum(len(m.dependencies) for m in resolved),duplicate_count=duplicate_count,missing_mod_count=sum(i.status==CompatStatus.ERROR for i in mod_items),missing_library_count=len(missing),incompatible_count=0 if conflicts and conflicts[0].name=='none' else len(conflicts),performance_score=max(0,min(100,100-len(resolved)*2)),estimated_ram_mb=2048+len(resolved)*64,estimated_cpu_load_percent=min(100,10+len(resolved)),estimated_startup_seconds=10+len(resolved)//2,download_size_bytes=download_size,installed_size_bytes=download_size)
  unique=list(dict.fromkeys(errors));status=CompatStatus.ERROR if unique else CompatStatus.WARN if warnings else CompatStatus.OK
  return CompatibilityReport(status=status,mods=mod_items,dependencies=deps,conflicts=conflicts,configuration=[CompatCheckItem.model_validate(i) for i in configuration],warnings=warnings,missing_libraries=missing,export_ready=not unique,errors=unique,metrics=metrics)
 async def close(self)->None:await self.resolver.close()
