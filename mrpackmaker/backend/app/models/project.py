"""SQLAlchemy project model."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.enums import LoaderType, ProjectStatus, ThemeType


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    minecraft_version: Mapped[str] = mapped_column(String(32), nullable=False)
    loader: Mapped[str] = mapped_column(String(32), nullable=False)
    loader_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    theme: Mapped[str] = mapped_column(String(32), nullable=False)
    theme_custom: Mapped[str | None] = mapped_column(String(255), nullable=True)
    difficulty: Mapped[str] = mapped_column(String(32), nullable=False, default="normal")
    performance_preference: Mapped[str] = mapped_column(String(32), nullable=False, default="balanced")
    generation_prompt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    minimum_mods: Mapped[int | None] = mapped_column(Integer, nullable=True)
    maximum_mods: Mapped[int | None] = mapped_column(Integer, nullable=True)
    minimum_downloads: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=ProjectStatus.DRAFT.value)
    mods_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    resolved_loader_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    mrpack_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    settings_locked: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    def loader_enum(self) -> LoaderType:
        return LoaderType(self.loader)

    def theme_enum(self) -> ThemeType:
        return ThemeType(self.theme)

    def status_enum(self) -> ProjectStatus:
        return ProjectStatus(self.status)
