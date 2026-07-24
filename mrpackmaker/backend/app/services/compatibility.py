"""Compatibility report builder and export gate."""
from __future__ import annotations
import json
from app.models.enums import LoaderType
from app.models.project import Project
from app.schemas.compatibility import CompatCheckItem,CompatStatus,CompatibilityMetrics,CompatibilityReport
from app.schemas.mod import ModEntry
from app.services.curseforge import CurseForgeClient
from app.services.dependency_graph import DependencyGraph
from app.services.mod_resolver import ModResolver,mod_identity
from app.services.mrpack_validation import validate_export_inputs
from app.services.source_registry import UnknownModSourceError
from app.services.dependency_analysis import analyze_dependencies
class CompatibilityService:
 def __init__(self,modrinth:ModrinthClient,curseforge:CurseForgeClient)->None:self.resolver=ModResolver(modrinth,curseforge)
 async def check_project(self,project:Project)->CompatibilityReport:
  selected=[ModEntry.model_validate(data) for data in json.loads(project.mods_json or '[]')];loader=LoaderType(project.loader);graph=DependencyGraph();mod_items=[];errors=[];resolved=[]
  for mod in selected:
   try:fresh=await self.resolver.resolve_mod(mod.source,mod.id,project.minecraft_version,loader)
   except UnknownModSourceError:fresh=None
   local_import=fresh is None and mod.source=='imported' and bool(mod.file_name and mod.download_url and (mod.hashes.sha1 or mod.hashes.sha512));effective=fresh or mod
   if (fresh and fresh.file_name and fresh.download_url) or local_import:resolved.append(effective);graph.add_mod(effective);mod_items.append(CompatCheckItem(name=effective.name,status=CompatStatus.OK,message='Imported artifact metadata accepted' if local_import else 'Version and loader match'))
   else:errors.append(f'{mod.name} has no compatible {project.minecraft_version} {loader.value} file');mod_items.append(CompatCheckItem(name=mod.name,status=CompatStatus.ERROR,message='No compatible file'))
  dependency_report=analyze_dependencies(resolved,project.minecraft_version,loader.value);errors.extend(issue['cause'] for issue in dependency_report['issues']);identities=[mod_identity(mod) for mod in selected];duplicate_count=len(identities)-len(set(identities))
  if duplicate_count:errors.append(f'{duplicate_count} duplicate project(s) detected across catalog sources')
  deps=[];missing=[]
  for library in ('fabric-api',) if loader==LoaderType.FABRIC else ():
   if not any(library in m.slug.lower() or library in m.name.lower() for m in resolved):missing.append(library);errors.append(f'Missing required library: {library}');deps.append(CompatCheckItem(name=library,status=CompatStatus.ERROR,message='Missing required library'))
  for key in graph.get_missing_required():errors.append(f'Missing required dependency: {key}');deps.append(CompatCheckItem(name=key,status=CompatStatus.ERROR,message='Missing required dependency'))
  present=set(graph.nodes)
  for key in sorted(graph.get_all_dependency_keys()&present):deps.append(CompatCheckItem(name=key,status=CompatStatus.OK,message='Present'))
  conflicts=[]
  for left,right in graph.get_conflicts():errors.append(f'Incompatible mods: {left} and {right}');conflicts.append(CompatCheckItem(name=f'{left} ↔ {right}',status=CompatStatus.ERROR,message='Declared incompatible'))
  if not conflicts:conflicts=[CompatCheckItem(name='none',status=CompatStatus.OK,message='No declared conflicts')]
  errors.extend(issue.message for issue in validate_export_inputs(project,resolved));warnings=[]
  if len(resolved)>80:warnings.append(f'Large modpack ({len(resolved)} mods) may need extra memory.')
  if not project.loader_version and not project.resolved_loader_version:warnings.append('Loader version has not been pinned or resolved.')
  download_size=sum(mod.file_size or 0 for mod in resolved);metrics=CompatibilityMetrics(minecraft_version=project.minecraft_version,loader=loader.value,loader_version=project.loader_version or project.resolved_loader_version,dependency_count=sum(len(mod.dependencies) for mod in resolved),duplicate_count=duplicate_count,missing_mod_count=sum(item.status==CompatStatus.ERROR for item in mod_items),missing_library_count=len(missing),incompatible_count=0 if conflicts and conflicts[0].name=='none' else len(conflicts),performance_score=max(0,min(100,100-len(resolved)*2)),estimated_ram_mb=2048+len(resolved)*64,estimated_cpu_load_percent=min(100,10+len(resolved)),estimated_startup_seconds=10+len(resolved)//2,download_size_bytes=download_size,installed_size_bytes=download_size)
  unique=list(dict.fromkeys(errors));status=CompatStatus.ERROR if unique else CompatStatus.WARN if warnings else CompatStatus.OK
  return CompatibilityReport(status=status,mods=mod_items,dependencies=deps,conflicts=conflicts,warnings=warnings,missing_libraries=missing,export_ready=not unique,errors=unique,metrics=metrics,)
 async def close(self)->None:await self.resolver.close()
