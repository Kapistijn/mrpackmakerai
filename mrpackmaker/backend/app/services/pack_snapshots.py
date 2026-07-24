from __future__ import annotations
import json
from sqlalchemy import select
from app.models.pack_snapshot import PackSnapshot
async def create_snapshot(db,project,reason,change=None):
 latest=(await db.execute(select(PackSnapshot).where(PackSnapshot.project_id==project.id).order_by(PackSnapshot.version.desc()))).scalars().first()
 version=(latest.version+1) if latest else 1
 row=PackSnapshot(project_id=project.id,version=version,mods_json=project.mods_json or '[]',reason=reason,change_json=json.dumps(change or {}));db.add(row);await db.flush();return row
async def list_snapshots(db,project_id):
 rows=(await db.execute(select(PackSnapshot).where(PackSnapshot.project_id==project_id).order_by(PackSnapshot.version.desc()))).scalars().all();return rows
async def restore_snapshot(db,project,snapshot):
 project.mods_json=snapshot.mods_json;project.mrpack_path=None
 return await create_snapshot(db,project,f'Restored snapshot v{snapshot.version}',{'restored_from':snapshot.version})
