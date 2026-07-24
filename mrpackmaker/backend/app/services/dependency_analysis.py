from __future__ import annotations
from app.schemas.mod import ModEntry

def analyze_dependencies(mods:list[ModEntry])->dict:
 by_key={f'{m.source}:{m.id}':m for m in mods};issues=[];edges=[];optional=[];recommended=[];reverse={}
 for parent in mods:
  pkey=f'{parent.source}:{parent.id}'
  for dep in parent.dependencies:
   dkey=f'{dep.source or parent.source}:{dep.project_id}';kind=dep.dependency_type.casefold();edges.append((pkey,dkey,kind));reverse.setdefault(dkey,[]).append(pkey)
   if kind=='optional':optional.append({'parent':pkey,'dependency':dkey})
   if kind in {'recommended','suggested'}:recommended.append({'parent':pkey,'dependency':dkey})
   if kind=='incompatible' and dkey in by_key:issues.append({'type':'incompatible','cause':'An incompatible dependency is selected','affected_mods':[pkey,dkey],'recommended_fixes':['Remove one mod','Use a compatible version'],'confidence':0.98})
   if kind=='required' and dkey not in by_key:issues.append({'type':'missing','cause':'A required dependency is absent','affected_mods':[pkey,dkey],'recommended_fixes':['Resolve a compatible dependency','Remove the parent mod'],'confidence':0.9})
 missing_libraries=[x for x in issues if x['type']=='missing' and (x['affected_mods'][1].split(':',1)[-1].startswith(('lib','library')))]
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
 for cycle in cycles:issues.append({'type':'cycle','cause':'Dependency chain contains a cycle','affected_mods':cycle,'recommended_fixes':['Break the cycle with a compatible version','Remove one dependency edge'],'confidence':0.99})
 counts={}
 for mod in mods:
  if mod.name.casefold() in counts:issues.append({'type':'duplicate_library','cause':'Duplicate dependency/library identity','affected_mods':[counts[mod.name.casefold()],f'{mod.source}:{mod.id}'],'recommended_fixes':['Keep one canonical provider'],'confidence':0.95})
  counts[mod.name.casefold()]=f'{mod.source}:{mod.id}'
 unused=[f'{m.source}:{m.id}' for m in mods if f'{m.source}:{m.id}' not in reverse and any(k=='library' for _,_,k in edges)]
 return {'graph':{'nodes':list(by_key),'edges':[{'parent':a,'dependency':b,'kind':c} for a,b,c in edges]},'issues':issues,'cycles':cycles,'missing_libraries':missing_libraries,'optional':optional,'recommended':recommended,'unused_libraries':unused,'dependency_chains':edges,'risk_count':len(issues)}
