from __future__ import annotations
from app.schemas.mod import ModEntry

def _issue(kind,cause,affected,fixes,confidence):return {'type':kind,'cause':cause,'affected_mods':affected,'recommended_fixes':fixes,'confidence':confidence}
def analyze_dependencies(mods:list[ModEntry],minecraft_version:str|None=None,loader:str|None=None)->dict:
 by_key={f'{m.source}:{m.id}':m for m in mods};issues=[];edges=[];optional=[];recommended=[];reverse={}
 for parent in mods:
  pkey=f'{parent.source}:{parent.id}'
  for dep in parent.dependencies:
   dkey=f'{dep.source or parent.source}:{dep.project_id}';kind=dep.dependency_type.casefold();edges.append((pkey,dkey,kind));reverse.setdefault(dkey,[]).append(pkey)
   if kind=='optional':optional.append({'parent':pkey,'dependency':dkey,'reason':'Optional edge is available but not required'})
   if kind in {'recommended','suggested'}:recommended.append({'parent':pkey,'dependency':dkey,'reason':'Recommended edge is available but not required'})
   if kind=='incompatible' and dkey in by_key:issues.append(_issue('incompatible','An incompatible dependency is selected',[pkey,dkey],['Remove one mod','Use a compatible version'],0.98))
   if kind=='required' and dkey not in by_key:issues.append(_issue('missing','A required dependency is absent',[pkey,dkey],['Resolve a compatible dependency','Remove the parent mod'],0.9))
   if dep.loaders and loader and loader.casefold() not in {x.casefold() for x in dep.loaders}:issues.append(_issue('loader_conflict',f'Dependency metadata excludes loader {loader}',[pkey,dkey],['Choose a matching loader variant','Remove the dependency'],0.95))
   if dep.minecraft_versions and minecraft_version and minecraft_version not in dep.minecraft_versions:issues.append(_issue('minecraft_conflict',f'Dependency metadata excludes Minecraft {minecraft_version}',[pkey,dkey],['Choose a matching Minecraft version','Pin a compatible dependency'],0.95))
   if dep.version_range and not dep.version_range.strip():issues.append(_issue('version_range','Dependency version range is empty or invalid',[pkey,dkey],['Pin a valid version range'],0.8))
 missing_libraries=[x for x in issues if x['type']=='missing' and any(t in x['affected_mods'][1].split(':',1)[-1].casefold() for t in ('lib','library'))]
 cycles=[];state={};stack=[]
 def visit(key):
  if state.get(key)==1:
   if key in stack:cycles.append(stack[stack.index(key):]+[key])
   return
  if state.get(key)==2 or key not in by_key:return
  state[key]=1;stack.append(key)
  for parent,dep,_ in edges:
   if parent==key:visit(dep)
  stack.pop();state[key]=2
 for key in by_key:visit(key)
 for cycle in cycles:issues.append(_issue('cycle','Dependency chain contains a cycle',cycle,['Break the cycle with a compatible version','Remove one dependency edge'],0.99))
 names={};
 for mod in mods:
  key=f'{mod.source}:{mod.id}';name=mod.name.casefold()
  if name in names:issues.append(_issue('duplicate_library','Duplicate dependency/library identity',[names[name],key],['Keep one canonical provider'],0.95))
  names[name]=key
 unused=[f'{m.source}:{m.id}' for m in mods if f'{m.source}:{m.id}' not in reverse and any(k in {'required','optional','recommended','suggested'} for _,_,k in edges) and m.name.casefold() in {'library','lib'}]
 return {'graph':{'nodes':list(by_key),'edges':[{'parent':a,'dependency':b,'kind':c} for a,b,c in edges]},'issues':issues,'cycles':cycles,'missing_libraries':missing_libraries,'optional':optional,'recommended':recommended,'unused_libraries':unused,'dependency_chains':[{'parent':a,'dependency':b,'kind':c} for a,b,c in edges],'risk_count':len(issues)}