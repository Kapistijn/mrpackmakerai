"""Pydantic schemas for projects."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, field_validator

from app.models.enums import DifficultyType, LoaderType, PerformancePreference, ProjectStatus, ThemeType
from app.schemas.mod import ModEntry


class ProjectSettings(BaseModel):
    minecraft_version: str
    loader: LoaderType
    loader_version: str | None = None
    name: str
    description: str
    theme: ThemeType
    theme_custom: str | None = None
    difficulty: DifficultyType = DifficultyType.NORMAL
    performance_preference: PerformancePreference = PerformancePreference.BALANCED

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()

    @field_validator("loader_version")
    @classmethod
    def loader_version_clean(cls, v: str | None) -> str | None:
        value = v.strip() if v else None
        return value or None


class ProjectCreate(ProjectSettings):
    generation_prompt: str = ""


class ProjectUpdate(BaseModel):
    generation_prompt: str | None = None
    loader_version: str | None = None
    mods: list[ModEntry] | None = None


class ProjectResponse(BaseModel):
    id: int
    name: str
    description: str
    minecraft_version: str
    loader: LoaderType
    loader_version: str | None
    theme: ThemeType
    theme_custom: str | None
    difficulty: DifficultyType
    performance_preference: PerformancePreference
    generation_prompt: str
    status: ProjectStatus
    mods: list[dict[str, Any]]
    resolved_loader_version: str | None
    ai_summary: str | None
    mrpack_path: str | None
    settings_locked: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectListItem(BaseModel):
    id: int
    name: str
    minecraft_version: str
    loader: LoaderType
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ErrorResponse(BaseModel):
    detail: str
    code: str = "error"
