"""Database session management."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import config


class Base(DeclarativeBase):
    pass


DATABASE_URL = f"sqlite+aiosqlite:///{config.db_path.as_posix()}"

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    config.data_dir.mkdir(parents=True, exist_ok=True)
    config.output_dir.mkdir(parents=True, exist_ok=True)
    from app import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_apply_compatible_migrations)


def _apply_compatible_migrations(connection) -> None:
    """Apply additive SQLite migrations for installs created before v2.

    A production deployment should replace this small bootstrap with Alembic,
    but this is intentionally safe for the single-file local application: it
    only adds missing nullable/defaulted columns and never drops user data.
    """
    columns = {column["name"] for column in inspect(connection).get_columns("projects")}
    additions = {
        "difficulty": "VARCHAR(32) NOT NULL DEFAULT 'normal'",
        "performance_preference": "VARCHAR(32) NOT NULL DEFAULT 'balanced'",
    }
    for column, definition in additions.items():
        if column not in columns:
            connection.execute(text(f"ALTER TABLE projects ADD COLUMN {column} {definition}"))
