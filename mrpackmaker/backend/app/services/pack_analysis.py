from __future__ import annotations
import json
from sqlalchemy import select
from app.models.pack_analysis import PackAnalysis
from app.models.project import Project
from app.schemas.mod import ModEntry
from app.services.pack_intelligence import quality_report,synergy_report,performance_estimate,reputation_report

_HARDWARE_GPU={'low_end':4,'mid_range':6,'high_end':8,'extreme':12}
def _hardware(project):
 return {'cpu':getattr(project,'hardware_cpu',None),'gpu':getattr(project,'hardware_gpu',None),'ram_gb':getattr(project,'target_ram_gb',None),'resolution':getattr(project,'hardware_resolution',None),'refresh_rate':getattr(project,'hardware_refresh_rate',None),'target_fps':getattr(project,'target_fps',None),'shader_preference':getattr(project,'shader_support',None)}
def _dependency_risks(mods):
 missing=[];duplicates=[];seen=set()
 for mod in mods:
  key=(mod.source,mod.id)
  if key in seen:duplicates.append(mod.name)
  seen.add(key)
  for dep in mod.dependencies:
   if dep.dependency_type=='required' and not dep.project_id:missing.append(f'{mod.name}: missing dependency id')
 return {'missing':missing,'duplicates':duplicates,'count':len(missing)+len(duplicates)}
def _hardware_adjustment(project,performance):
 hw=_hardware(project);ram=hw['ram_gb'];gpu=hw['gpu'];expected=performance['expected_fps'];target=hw['target_fps']
 if ram and performance['ram_gb']>ram: return {'status':'over_budget','score':35,'reason':f"Estimated RAM {performance['ram_gb']}GB exceeds configured {ram}GB."}
 if target and expected['low']<target: return {'status':'below_target','score':65,'reason':f"Estimated low FPS {expected['low']} is below target {target}."}
 if gpu and _HARDWARE_GPU.get(gpu,0)<performance['vram_gb']: return {'status':'gpu_limited','score':55,'reason':'Shader and particle load exceeds the selected GPU profile.'}
 return {'status':'fit','score':95,'reason':'Pack fits the configured hardware targets.'}
def analyze_mods(project,mods,source='generation'):
 quality=quality_report(mods);synergy=synergy_report(mods);performance=performance_estimate(mods,ram_gb=project.target_ram_gb,fps_target=project.target_fps,shader_support=project.shader_support);deps=_dependency_risks(mods);hardware=_hardware_adjustment(project,performance)
 problems=deps['count']+len(synergy['conflicts'])+(1 if hardware['status']!='fit' else 0)
 overall=max(0,round(sum(quality['scores'].values())/len(quality['scores'])-problems*4))
 return {'overall_score':overall,'quality':quality,'performance':performance,'synergy':synergy,'dependency_risks':deps,'hardware':hardware,'hardware_profile':_hardware(project),'problems':problems,'recommendations':([hardware['reason']] if hardware['status']!='fit' else [])+([f"Review {len(synergy['conflicts'])} world-generation overlaps."] if synergy['conflicts'] else [])+([f"Resolve {deps['count']} dependency risks."] if deps['count'] else []),'reputation':[reputation_report(mod) for mod in mods],'source':source}
async def persist_analysis(db,project,source='generation'):
 mods=[ModEntry.model_validate(item) for item in json.loads(project.mods_json or '[]')]
 report=analyze_mods(project,mods,source)
 latest=(await db.execute(select(PackAnalysis).where(PackAnalysis.project_id==project.id).order_by(PackAnalysis.version.desc()))).scalars().first()
 version=(latest.version+1) if latest else 1
 row=PackAnalysis(project_id=project.id,version=version,overall_score=report['overall_score'],report_json=json.dumps(report),source=source);db.add(row);await db.flush()
 return report
