"""Public and admin-only settings API contracts."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AISettingsPublic(BaseModel):
    provider: str
    base_url: str
    model: str
    timeout_seconds: float
    max_tokens: int
    temperature: float
    configured: bool


class SettingsOverview(BaseModel):
    ai: AISettingsPublic
    voice: dict[str, str]
    mod_sources: dict[str, bool]


class AIModelSelection(BaseModel):
    """Non-secret model choice. An empty value re-enables auto-selection."""

    model: str = ""


class AISettingsUpdate(BaseModel):
    provider: str | None = None
    base_url: str | None = None
    model: str | None = None
    timeout_seconds: float | None = Field(default=None, ge=1.0, le=300.0)
    max_tokens: int | None = Field(default=None, ge=128, le=32768)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    api_key: str | None = None


class AdminSettingsUpdate(BaseModel):
    ai: AISettingsUpdate | None = None
    modrinth_key: str | None = None
    curseforge_key: str | None = None
    admin_token: str | None = Field(default=None, min_length=16)


class AdminSettingsResponse(BaseModel):
    ai: AISettingsPublic
    modrinth_key: str
    curseforge_key: str
    admin_token_configured: bool
