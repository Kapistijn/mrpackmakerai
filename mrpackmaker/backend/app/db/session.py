"""Database session management."""
from __future__ import annotations
import logging
from collections.abc import AsyncGenerator
from sqlalchemy import inspect,text,update
from sqlalchemy.ext.asyncio import AsyncSession,async_sessionmaker,create_async_engine
from sqlalchemy.orm import DeclarativeBase
from app.config import config
logger=logging.getLogger(__name__)
class Base(DeclarativeBase):pass
DATABASE_URL=f"sqlite+aiosqlite:///{config.db_path.as_posix()}"
engine=create_async_engine(DATABASE_URL,echo=False,connect_args={'check_same_thread':False})
AsyncSessionLocal=async_sessionmaker(engine,class_=AsyncSession,expire_on_commit=False)
async def get_db()->AsyncGenerator[AsyncSession,None]:
 async with AsyncSessionLocal() as session:
  try:yield session;await session.commit()
  except Exception:await session.rollback();raise
async def init_db():
 config.data_dir.mkdir(parents=True,exist_ok=True);config.output_dir.mkdir(parents=True,exist_ok=True)
 from app import models
 async with engine.begin() as conn:
  await conn.run_sync(Base.metadata.create_all);await conn.run_sync(_apply_compatible_migrations)
async def reset_orphaned_generations():
 from app.models.enums import ProjectStatus
 from app.models.generation import GenerationRun
 from app.models.project import Project
 async with AsyncSessionLocal() as session:
  result=await session.execute(update(Project).where(Project.status==ProjectStatus.GENERATING.value).values(status=ProjectStatus.DRAFT.value));await session.execute(update(GenerationRun).where(GenerationRun.status=='running').values(status='failed',error='Interrupted by a server restart'));await session.commit()
  if result.rowcount:logger.warning('Reset %s orphaned generating project(s) to draft',result.rowcount)
def _apply_compatible_migrations(connection):
 columns={c['name'] for c in inspect(connection).get_columns('projects')}
 additions={'difficulty':"VARCHAR(32) NOT NULL DEFAULT 'normal'",'performance_preference':"VARCHAR(32) NOT NULL DEFAULT 'balanced'",'loader_version':'VARCHAR(64) NULL','minimum_mods':'INTEGER NULL','maximum_mods':'INTEGER NULL','minimum_downloads':"INTEGER NOT NULL DEFAULT 0",'target_ram_gb':'INTEGER NULL','target_fps':'INTEGER NULL','shader_support':"VARCHAR(16) NOT NULL DEFAULT 'off'",'shader_quality':'VARCHAR(16) NULL','resourcepack_support':'BOOLEAN NOT NULL DEFAULT 0','required_mods_json':"TEXT NOT NULL DEFAULT '[]'",'forbidden_mods_json':"TEXT NOT NULL DEFAULT '[]'",'ai_creativity':"VARCHAR(16) NOT NULL DEFAULT 'balanced'",'ai_strictness':"VARCHAR(16) NOT NULL DEFAULT 'balanced'",'discovery_depth':"VARCHAR(16) NOT NULL DEFAULT 'standard'"}
 for column,definition in additions.items():
  if column not in columns:connection.execute(text(f'ALTER TABLE projects ADD COLUMN {column} {definition}'))
