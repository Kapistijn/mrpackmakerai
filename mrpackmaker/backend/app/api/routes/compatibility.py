"""Compatibility check routes with automatic dependency repair."""
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import config
from app.db.session import get_db
from app.models.project import Project
from app.schemas.compatibility import CompatibilityReport
from app.services.compatibility import CompatibilityService
from app.services.curseforge import CurseForgeClient
from app.services.modrinth import ModrinthClient
from app.services.dependency_repair import repair_project_dependencies
router=APIRouter()
@router.post('/{project_id}',response_model=CompatibilityReport)
async def run_compatibility(project_id:int,db:AsyncSession=Depends(get_db)):
 project=await db.get(Project,project_id)
 if not project:raise HTTPException(status_code=404,detail='Project not found')
 await repair_project_dependencies(project,db)
 service=CompatibilityService(ModrinthClient(config.apis.modrinth_key),CurseForgeClient(config.apis.curseforge_key))
 try:return await service.check_project(project)
 finally:await service.close()
