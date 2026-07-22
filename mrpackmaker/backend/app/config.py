"""Typed application configuration with safe environment overrides.

``config.json`` deliberately contains only non-sensitive settings.  API keys and
admin credentials are supplied through environment variables or an encrypted
local secret store (managed from the browser settings page).  This keeps secrets
out of the frontend, logs and source control from the beginning.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.services.secret_store import SecretStore


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


# Known OpenAI-compatible provider presets.  Selecting one of these as the AI
# provider supplies a sensible default ``base_url`` when the user has not set
# one explicitly, so switching to Ollama is a one-word change instead of having
# to remember the port.  Unknown providers keep whatever ``base_url`` is given.
PROVIDER_PRESETS: dict[str, str] = {
    "lmstudio": "http://localhost:1234/v1",
    "ollama": "http://localhost:11434/v1",
    "litellm": "http://localhost:4000/v1",
}


def default_base_url_for(provider: str) -> str | None:
    """Return the preset ``base_url`` for a known provider, else ``None``."""
    return PROVIDER_PRESETS.get((provider or "").strip().lower())


class AIConfig(BaseModel):
    """Settings shared by every OpenAI-compatible AI provider.

    LM Studio, Ollama and LiteLLM are all OpenAI-compatible, so switching
    between them is purely a matter of ``provider`` + ``base_url`` (+ optional
    ``api_key`` for LiteLLM). Only one provider is active at a time. Selecting a
    known provider (see :data:`PROVIDER_PRESETS`) fills in the default
    ``base_url`` automatically when one is not set explicitly.
    """

    provider: str = "lmstudio"
    base_url: str = "http://localhost:1234/v1"
    model: str = ""
    api_key: str = Field(default="", repr=False)
    timeout_seconds: float = Field(default=45.0, ge=1.0, le=300.0)
    max_tokens: int = Field(default=4096, ge=128, le=32768)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    # Informational context window the model is configured with. Not sent as a
    # chat-completions parameter (providers reject unknown fields); surfaced in
    # the UI so users can align it with their loaded model.
    context_size: int = Field(default=4096, ge=512, le=131072)

    @field_validator("provider")
    @classmethod
    def normalise_provider(cls, value: str) -> str:
        value = value.strip().lower()
        if not value:
            raise ValueError("AI provider cannot be empty")
        return value

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        value = value.strip().rstrip("/")
        if not value.startswith(("http://", "https://")):
            raise ValueError("AI base_url must use http or https")
        return value

    @property
    def url(self) -> str:
        """Compatibility alias for the original local configuration format."""
        return self.base_url


class APIConfig(BaseModel):
    modrinth_key: str = Field(default="", repr=False)
    curseforge_key: str = Field(default="", repr=False)


class MinecraftConfig(BaseModel):
    """Non-secret defaults used to pre-fill the New Project form."""

    default_version: str = "1.21.1"
    default_loader: str = "neoforge"

    @field_validator("default_loader")
    @classmethod
    def normalise_loader(cls, value: str) -> str:
        return (value or "neoforge").strip().lower()


class SourcesConfig(BaseModel):
    """Which mod catalogs the pipeline is allowed to query."""

    modrinth_enabled: bool = True
    curseforge_enabled: bool = True


class VoiceConfig(BaseModel):
    """Connection settings for optional local/remote voice services.

    STT (whisper.cpp) and TTS run independently of the web process.  TTS is
    OpenAI-compatible (``POST {tts_base_url}/audio/speech``) so a LiteLLM proxy
    can serve it; both the address and model are entered manually because a
    proxy exposes provider-specific model names that cannot be auto-discovered.
    """

    whisper_url: str = "http://localhost:9000"
    tts_provider: str = "disabled"  # disabled | litellm | openai
    tts_base_url: str = ""
    tts_model: str = ""
    tts_voice: str = "alloy"
    tts_api_key: str = Field(default="", repr=False)

    @field_validator("tts_provider")
    @classmethod
    def normalise_tts_provider(cls, value: str) -> str:
        return (value or "disabled").strip().lower()

    @property
    def tts_enabled(self) -> bool:
        return self.tts_provider not in {"", "disabled", "none", "off"}


class SecurityConfig(BaseModel):
    admin_token: str = Field(default="", repr=False)


class AppConfig(BaseModel):
    ai: AIConfig = Field(default_factory=AIConfig)
    apis: APIConfig = Field(default_factory=APIConfig)
    minecraft: MinecraftConfig = Field(default_factory=MinecraftConfig)
    sources: SourcesConfig = Field(default_factory=SourcesConfig)
    voice: VoiceConfig = Field(default_factory=VoiceConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)

    @property
    def repo_root(self) -> Path:
        return _repo_root()

    @property
    def data_dir(self) -> Path:
        return self.repo_root / "data"

    @property
    def output_dir(self) -> Path:
        return self.repo_root / "output"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "mrpackmaker.db"

    @property
    def logs_dir(self) -> Path:
        return self.data_dir / "logs"


def _environment_or(data: dict[str, Any], env_name: str, fallback: Any = "") -> Any:
    value = os.getenv(env_name)
    return value if value is not None else fallback


def load_config() -> AppConfig:
    """Load public config, honouring legacy ``ai.url`` on existing installs."""
    config_path = _repo_root() / "config.json"
    data: dict[str, Any] = {}
    if config_path.exists():
        with config_path.open("r", encoding="utf-8") as file:
            data = json.load(file)

    ai_data = dict(data.get("ai", {}))
    # v1 used ``url``.  Reading it here makes upgrades non-breaking while all
    # new configuration and API responses use the unambiguous ``base_url``.
    if "base_url" not in ai_data and "url" in ai_data:
        ai_data["base_url"] = ai_data.pop("url")
    # Remember whether the address was pinned by the user before we start
    # applying defaults, so a provider preset only ever fills an *unset* one.
    base_url_explicit = ("base_url" in ai_data) or (os.getenv("MRPACK_AI_BASE_URL") is not None)

    apis_data = dict(data.get("apis", {}))
    minecraft_data = dict(data.get("minecraft", {}))
    sources_data = dict(data.get("sources", {}))
    voice_data = dict(data.get("voice", {}))
    security_data = dict(data.get("security", {}))
    stored_secrets = SecretStore(_repo_root() / "data").load()

    resolved_provider = _environment_or(ai_data, "MRPACK_AI_PROVIDER", ai_data.get("provider", "lmstudio"))
    ai_data["provider"] = resolved_provider
    # A known provider preset supplies the default base_url only when the user
    # did not set one explicitly (config.json / legacy ``url`` / the env var).
    preset_base_url = default_base_url_for(resolved_provider)
    if not base_url_explicit and preset_base_url:
        ai_data["base_url"] = preset_base_url
    else:
        ai_data["base_url"] = _environment_or(
            ai_data, "MRPACK_AI_BASE_URL", ai_data.get("base_url", "http://localhost:1234/v1")
        )
    ai_data["model"] = _environment_or(ai_data, "MRPACK_AI_MODEL", ai_data.get("model", ""))
    ai_data["api_key"] = _environment_or(
        ai_data,
        "MRPACK_AI_API_KEY",
        stored_secrets.get("ai_api_key", ai_data.get("api_key", "")),
    )

    apis_data["modrinth_key"] = _environment_or(
        apis_data, "MRPACK_MODRINTH_KEY", stored_secrets.get("modrinth_key", apis_data.get("modrinth_key", ""))
    )
    apis_data["curseforge_key"] = _environment_or(
        apis_data, "MRPACK_CURSEFORGE_KEY", stored_secrets.get("curseforge_key", apis_data.get("curseforge_key", ""))
    )

    voice_data["whisper_url"] = _environment_or(voice_data, "MRPACK_WHISPER_URL", voice_data.get("whisper_url", "http://localhost:9000"))
    voice_data["tts_provider"] = _environment_or(voice_data, "MRPACK_TTS_PROVIDER", voice_data.get("tts_provider", "disabled"))
    voice_data["tts_base_url"] = _environment_or(voice_data, "MRPACK_TTS_BASE_URL", voice_data.get("tts_base_url", ""))
    voice_data["tts_model"] = _environment_or(voice_data, "MRPACK_TTS_MODEL", voice_data.get("tts_model", ""))
    voice_data["tts_voice"] = _environment_or(voice_data, "MRPACK_TTS_VOICE", voice_data.get("tts_voice", "alloy"))
    voice_data["tts_api_key"] = _environment_or(
        voice_data, "MRPACK_TTS_API_KEY", stored_secrets.get("tts_api_key", voice_data.get("tts_api_key", ""))
    )

    security_data["admin_token"] = _environment_or(
        security_data, "MRPACK_ADMIN_TOKEN", stored_secrets.get("admin_token", security_data.get("admin_token", ""))
    )

    return AppConfig(
        ai=AIConfig(**ai_data),
        apis=APIConfig(**apis_data),
        minecraft=MinecraftConfig(**minecraft_data),
        sources=SourcesConfig(**sources_data),
        voice=VoiceConfig(**voice_data),
        security=SecurityConfig(**security_data),
    )


config = load_config()
