from __future__ import annotations
import asyncio,json
from sqlalchemy import select
from app.models.pack_snapshot import PackSnapshot
from app.models.pack_analysis import PackAnalysis
_lock=asyncio.Lock()
_PROJECT_FIELDS=('name','description','minecraft_version','loader','loader_version','theme','theme_custom','difficulty','performance_preference','generation_prompt','minimum_mods','maximum_mods','minimum_downloads','target_ram_gb','target_fps','shader_support','shader_quality','resourcepack_support','required_mods_json','forbidden_mods_json','ai_creativity','ai_strictness','discovery_depth','gameplay_style_json','qol_level','hardware_profile','hardware_cpu','hardware_gpu','hardware_resolution','hardware_refresh_rate','multiplayer_mode','world_style','progression','status','mods_json','resolved_loader_version','ai_summary','mrpack_path','settings_locked')
def _project_state(project):return {field:getattr(project,field,None) for field in _PROJECT_FIELDS}
def _hardware_state(project):return {key:getattr(project,key,None) for key in ('hardware_cpu','hardware_gpu','target_ram_gb','hardware_resolution','hardware_refresh_rate','target_fps','shader_support','hardware_profile')}
async def create_snapshot(db,project,reason,change=None):
 async with _lock:
  latest=(await db.execute(select(PackSnapshot).where(PackSnapshot.project_id==project.id).order_by(PackSnapshot.version.desc()).limit(1))).scalars().first();version=(latest.version+1) if latest else 1
  analysis=(await db.execute(select(PackAnalysis).where(PackAnalysis.project_id==project.id).order_by(PackAnalysis.version.desc()).limit(1))).scalars().first()
  report=json.loads(analysis.report_json) if analysis else {}
  row=PackSnapshot(project_id=project.id,version=version,project_json=json.dumps(_project_state(project)),mods_json=project.mods_json or '[]',analysis_json=json.dumps(report),hardware_json=json.dumps(_hardware_state(project)),pack_metadata_json=json.dumps({'mrpack_path':project.mrpack_path}),generated_files_json=json.dumps({'mrpack_path':project.mrpack_path}),reason=reason,change_json=json.dumps(change or {}));db.add(row);await db.flush();return row
async def list_snapshots(db,project_id):return (await db.execute(select(PackSnapshot).where(PackSnapshot.project_id==project_id).order_by(PackSnapshot.version.desc()))).scalars().all()
async def restore_snapshot(db,project,snapshot):
 state=json.loads(snapshot.project_json or '{}')
 for field in _PROJECT_FIELDS:
  if field in state and field!='id':setattr(project,field,state[field])
 project.mods_json=snapshot.mods_json;project.mrpack_path=None
 return await create_snapshot(db,project,f'Restored snapshot v{snapshot.version}',{'restored_from':snapshot.version})
