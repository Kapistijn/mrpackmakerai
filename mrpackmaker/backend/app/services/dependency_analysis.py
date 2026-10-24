from __future__ import annotations
from app.schemas.mod import ModEntry

def _mod_key(mod): return f'{str(mod.source).strip().casefold()}:{str(mod.id).strip()}'
def _dep_key(dep, parent): return f'{str(dep.source or parent.source).strip().casefold()}:{str(dep.project_id).strip()}'

def _issue(kind,cause,affected,fixes,confidence):return {'type':kind,'cause':cause,'affected_mods':affected,'recommended_fixes':fixes,'confidence':confidence}
def analyze_dependencies(mods:list[ModEntry],minecraft_version:str|None=None,loader:str|None=None)->dict:
 by_key={_mod_key(m):m for m in mods};issues=[];edges=[];optional=[];recommended=[];reverse={}
 for parent in mods:
  pkey=_mod_key(parent)
  for dep in parent.dependencies:
   dkey=_dep_key(dep, parent);kind=str(dep.dependency_type or 'required').strip().casefold();edges.append((pkey,dkey,kind));reverse.setdefault(dkey,[]).append(pkey)
   if kind=='optional':optional.append({'parent':pkey,'dependency':dkey,'reason':'Optional edge is available but not required'})
   if kind in {'recommended','suggested'}:recommended.append({'parent':pkey,'dependency':dkey,'reason':'Recommended edge is available but not required'})
   if kind=='incompatible' and dkey in by_key:issues.append(_issue('incompatible','An incompatible dependency is selected',[pkey,dkey],['Remove one mod','Use a compatible version'],0.98))
   if kind=='required' and dkey not in by_key:issues.append(_issue('missing','A required dependency is absent',[pkey,dkey],['Resolve a compatible dependency','Remove the parent mod'],0.9))
   if dep.loaders and loader and str(loader).casefold() not in {str(x).casefold() for x in dep.loaders if x}:issues.append(_issue('loader_conflict',f'Dependency metadata excludes loader {loader}',[pkey,dkey],['Choose a matching loader variant','Remove the dependency'],0.95))
   if dep.minecraft_versions and minecraft_version and minecraft_version not in dep.minecraft_versions:issues.append(_issue('minecraft_conflict',f'Dependency metadata excludes Minecraft {minecraft_version}',[pkey,dkey],['Choose a matching Minecraft version','Pin a compatible dependency'],0.95))
   if dep.version_range and not dep.version_range.strip():issues.append(_issue('version_range','Dependency version range is empty or invalid',[pkey,dkey],['Pin a valid version range'],0.8))
 missing_libraries=[x for x in issues if x['type']=='missing' and any(t in x['affected_mods'][1].split(':',1)[-1].casefold() for t in ('lib','library'))]
 cycles=[];state={};adj={key:[] for key in by_key}
 for parent,dep,_ in edges:
  if parent in adj:adj[parent].append(dep)
 for root in by_key:
  if state.get(root):continue
  active=[];active_set=set();work=[(root,False)]
  while work:
   key,leaving=work.pop()
   if key not in by_key:continue
   if leaving:
    state[key]=2
    if active and active[-1]==key:active.pop();active_set.discard(key)
    continue
   if state.get(key)==2:continue
   if state.get(key)==1:
    if key in active_set:
     cycle=active[active.index(key):]+[key]
     if cycle not in cycles:cycles.append(cycle)
    continue
   state[key]=1;active.append(key);active_set.add(key);work.append((key,True))
   for dep in reversed(adj.get(key,())):
    if state.get(dep)==1:
     if dep in active_set:
      cycle=active[active.index(dep):]+[dep]
      if cycle not in cycles:cycles.append(cycle)
    elif state.get(dep)!=2:work.append((dep,False))
 for cycle in cycles:issues.append(_issue('cycle','Dependency chain contains a cycle',cycle,['Break the cycle with a compatible version','Remove one dependency edge'],0.99))
 names={};
 for mod in mods:
  key=_mod_key(mod);name=str(mod.name).casefold()
  if name in names:issues.append(_issue('duplicate_library','Duplicate dependency/library identity',[names[name],key],['Keep one canonical provider'],0.95))
  names[name]=key
 unused=[_mod_key(m) for m in mods if _mod_key(m) not in reverse and any(k in {'required','optional','recommended','suggested'} for _,_,k in edges) and str(m.name).casefold() in {'library','lib'}]
 return {'graph':{'nodes':list(by_key),'edges':[{'parent':a,'dependency':b,'kind':c} for a,b,c in edges]},'issues':issues,'cycles':cycles,'missing_libraries':missing_libraries,'optional':optional,'recommended':recommended,'unused_libraries':unused,'dependency_chains':[{'parent':a,'dependency':b,'kind':c} for a,b,c in edges],'risk_count':len(issues)}
