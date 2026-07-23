"""Pydantic schemas for projects."""
from __future__ import annotations
from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field, field_validator, model_validator
from app.models.enums import DifficultyType, LoaderType, PerformancePreference, ProjectStatus, ShaderSupport, ThemeType
from app.schemas.mod import ModEntry
MAX_MODS = 500
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
    minimum_mods: int | None = Field(default=None, ge=1, le=MAX_MODS)
    maximum_mods: int | None = Field(default=None, ge=1, le=MAX_MODS)
    minimum_downloads: int = Field(default=0, ge=0)
    target_ram_gb: int | None = Field(default=None, ge=1, le=128)
    target_fps: int | None = Field(default=None, ge=1, le=1000)
    shader_support: ShaderSupport = ShaderSupport.OFF
    shader_quality: str | None = None
    resourcepack_support: bool = False
    required_mods: list[str] = Field(default_factory=list)
    forbidden_mods: list[str] = Field(default_factory=list)
    ai_creativity: str = "balanced"
    ai_strictness: str = "balanced"
    discovery_depth: str = "standard"
    gameplay_style: list[str] = Field(default_factory=list)
    qol_level: str | None = None
    hardware_profile: str | None = None
    multiplayer_mode: str | None = None
    world_style: str | None = None
    progression: str | None = None
    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip(): raise ValueError("Name cannot be empty")
        return v.strip()
    @field_validator("loader_version")
    @classmethod
    def loader_version_clean(cls, v: str | None) -> str | None:
        value = v.strip() if v else None
        return value or None
    @model_validator(mode="after")
    def validate_mod_bounds(self):
        if self.minimum_mods and self.maximum_mods and self.minimum_mods > self.maximum_mods: raise ValueError("minimum_mods cannot exceed maximum_mods")
        return self
class ProjectCreate(ProjectSettings): generation_prompt: str = ""
class ProjectUpdate(BaseModel):
    generation_prompt: str | None = None
    loader_version: str | None = None
    minimum_mods: int | None = Field(default=None, ge=1, le=MAX_MODS)
    maximum_mods: int | None = Field(default=None, ge=1, le=MAX_MODS)
    minimum_downloads: int | None = Field(default=None, ge=0)
    target_ram_gb: int | None = Field(default=None, ge=1, le=128)
    target_fps: int | None = Field(default=None, ge=1, le=1000)
    shader_support: ShaderSupport | None = None
    shader_quality: str | None = None
    resourcepack_support: bool | None = None
    required_mods: list[str] | None = None
    forbidden_mods: list[str] | None = None
    ai_creativity: str | None = None
    ai_strictness: str | None = None
    discovery_depth: str | None = None
    gameplay_style: list[str] | None = None
    qol_level: str | None = None
    hardware_profile: str | None = None
    multiplayer_mode: str | None = None
    world_style: str | None = None
    progression: str | None = None
    mods: list[ModEntry] | None = None
class ProjectResponse(BaseModel):
    id: int; name: str; description: str; minecraft_version: str; loader: LoaderType; loader_version: str | None; theme: ThemeType; theme_custom: str | None; difficulty: DifficultyType; performance_preference: PerformancePreference; generation_prompt: str; minimum_mods: int | None; maximum_mods: int | None; minimum_downloads: int; target_ram_gb: int | None; target_fps: int | None; shader_support: ShaderSupport; shader_quality: str | None; resourcepack_support: bool; required_mods: list[str]; forbidden_mods: list[str]; ai_creativity: str; ai_strictness: str; discovery_depth: str; gameplay_style: list[str]; qol_level: str | None; hardware_profile: str | None; multiplayer_mode: str | None; world_style: str | None; progression: str | None; status: ProjectStatus; mods: list[dict[str, Any]]; resolved_loader_version: str | None; ai_summary: str | None; mrpack_path: str | None; settings_locked: bool; created_at: datetime; updated_at: datetime
    model_config = {"from_attributes": True}
class ProjectListItem(BaseModel):
    id: int; name: str; minecraft_version: str; loader: LoaderType; status: ProjectStatus; created_at: datetime; updated_at: datetime
    model_config = {"from_attributes": True}
class ErrorResponse(BaseModel): detail: str; code: str = "error"
