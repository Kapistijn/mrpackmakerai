"""Public and unified settings API contracts.

GET responses never contain a raw secret: API keys are represented by a masked
preview plus a ``*_configured`` boolean so the UI can offer a delete action.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class AISettingsPublic(BaseModel):
    provider: str
    base_url: str
    model: str
    timeout_seconds: float
    max_tokens: int
    temperature: float
    context_size: int = 4096
    configured: bool
    api_key_configured: bool = False


class VoiceSettingsPublic(BaseModel):
    whisper_url: str
    tts_provider: str
    tts_base_url: str
    tts_model: str
    tts_voice: str
    tts_enabled: bool = False
    tts_api_key_configured: bool = False


class MinecraftSettingsPublic(BaseModel):
    default_version: str
    default_loader: str


class SourcesSettingsPublic(BaseModel):
    modrinth_enabled: bool
    curseforge_enabled: bool


class SettingsOverview(BaseModel):
    ai: AISettingsPublic
    voice: VoiceSettingsPublic
    minecraft: MinecraftSettingsPublic
    sources: SourcesSettingsPublic
    mod_sources: dict[str, bool]
    modrinth_key_configured: bool = False
    curseforge_key_configured: bool = False
    modrinth_key_masked: str = "not configured"
    curseforge_key_masked: str = "not configured"
    admin_locked: bool = False
    # provider id -> suggested base_url, so the UI can offer a provider picker
    # (LM Studio / Ollama / LiteLLM) that pre-fills the correct local address.
    provider_presets: dict[str, str] = Field(default_factory=dict)


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
    context_size: int | None = Field(default=None, ge=512, le=131072)
    # Empty string clears the stored key; None leaves it unchanged.
    api_key: str | None = None


class VoiceSettingsUpdate(BaseModel):
    whisper_url: str | None = None
    tts_provider: str | None = None
    tts_base_url: str | None = None
    tts_model: str | None = None
    tts_voice: str | None = None
    # Empty string clears the stored key; None leaves it unchanged.
    tts_api_key: str | None = None


class MinecraftSettingsUpdate(BaseModel):
    default_version: str | None = None
    default_loader: str | None = None


class SourcesSettingsUpdate(BaseModel):
    modrinth_enabled: bool | None = None
    curseforge_enabled: bool | None = None


class UnifiedSettingsUpdate(BaseModel):
    """Single browser-facing update for every non-admin setting."""

    ai: AISettingsUpdate | None = None
    voice: VoiceSettingsUpdate | None = None
    minecraft: MinecraftSettingsUpdate | None = None
    sources: SourcesSettingsUpdate | None = None
    # Empty string clears the stored key; None leaves it unchanged.
    modrinth_key: str | None = None
    curseforge_key: str | None = None


class TTSTestRequest(BaseModel):
    text: str = Field(default="MrPackMaker text to speech is working.", max_length=500)


class ApiTestResult(BaseModel):
    """Uniform result for the AI / Modrinth / CurseForge test buttons."""

    ok: bool
    service: str
    status_code: int | None = None
    latency_ms: int | None = None
    detail: str | None = None
    # Free-form extras, e.g. {"provider": ..., "model": ...} or {"mods_found": ...}.
    info: dict[str, str] = Field(default_factory=dict)


# --- Legacy admin contracts kept for backward compatibility ------------------


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
