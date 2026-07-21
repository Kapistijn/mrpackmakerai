"""Server-side settings updates without ever serialising secrets to clients.

The browser sends secrets in to the backend (over the local connection) but a
GET response only ever returns a masked preview.  Every secret is persisted in
the encrypted :class:`SecretStore`, never in ``config.json``.
"""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import NamedTemporaryFile

from app.config import AIConfig, VoiceConfig, config
from app.schemas.settings import (
    AISettingsPublic,
    AdminSettingsResponse,
    AdminSettingsUpdate,
    SettingsOverview,
    UnifiedSettingsUpdate,
    VoiceSettingsPublic,
)
from app.services.secret_store import SecretStore
from app.services.source_registry import create_default_registry

# Public secret name -> encrypted store key.
SECRET_KEYS: dict[str, str] = {
    "modrinth": "modrinth_key",
    "curseforge": "curseforge_key",
    "ai": "ai_api_key",
    "tts": "tts_api_key",
}


def _mask(value: str) -> str:
    if not value:
        return "not configured"
    if len(value) <= 4:
        return "*" * len(value)
    return f"{value[:2]}{'*' * max(8, len(value) - 4)}{value[-2:]}"


def _public_ai() -> AISettingsPublic:
    return AISettingsPublic(
        provider=config.ai.provider,
        base_url=config.ai.base_url,
        model=config.ai.model,
        timeout_seconds=config.ai.timeout_seconds,
        max_tokens=config.ai.max_tokens,
        temperature=config.ai.temperature,
        configured=True,
        api_key_configured=bool(config.ai.api_key),
    )


def _public_voice() -> VoiceSettingsPublic:
    return VoiceSettingsPublic(
        whisper_url=config.voice.whisper_url,
        tts_provider=config.voice.tts_provider,
        tts_base_url=config.voice.tts_base_url,
        tts_model=config.voice.tts_model,
        tts_voice=config.voice.tts_voice,
        tts_enabled=config.voice.tts_enabled,
        tts_api_key_configured=bool(config.voice.tts_api_key),
    )


class SettingsService:
    async def overview(self) -> SettingsOverview:
        registry = create_default_registry()
        try:
            sources = {source_id: registry.is_available(source_id) for source_id in registry.ids()}
        finally:
            await registry.close()
        return SettingsOverview(
            ai=_public_ai(),
            voice=_public_voice(),
            mod_sources=sources,
            modrinth_key_configured=bool(config.apis.modrinth_key),
            curseforge_key_configured=bool(config.apis.curseforge_key),
            modrinth_key_masked=_mask(config.apis.modrinth_key),
            curseforge_key_masked=_mask(config.apis.curseforge_key),
            admin_locked=bool(config.security.admin_token),
        )

    def set_model(self, model: str) -> AISettingsPublic:
        """Persist the active AI model without requiring admin credentials.

        An empty string re-enables auto-selection of the first available model.
        """
        public_config = self._read_public_config()
        ai_data = self._ai_data(public_config)
        ai_data["model"] = model.strip()
        new_ai = AIConfig(**ai_data)
        public_config["ai"] = new_ai.model_dump(exclude={"api_key"})
        self._write_public_config(public_config)
        config.ai = new_ai
        return _public_ai()

    async def update_settings(self, update: UnifiedSettingsUpdate) -> SettingsOverview:
        """Apply a unified, browser-facing settings update.

        Validation happens before anything is written so a bad value cannot
        leave a half-applied configuration behind.
        """
        public_config = self._read_public_config()
        ai_data = self._ai_data(public_config)
        voice_data = self._voice_data(public_config)
        secret_set: dict[str, str] = {}
        secret_clear: list[str] = []

        if update.ai is not None:
            for name in ("provider", "base_url", "model", "timeout_seconds", "max_tokens", "temperature"):
                value = getattr(update.ai, name)
                if value is not None:
                    ai_data[name] = value
            if update.ai.api_key is not None:
                key = update.ai.api_key.strip()
                ai_data["api_key"] = key
                (secret_set.__setitem__("ai_api_key", key) if key else secret_clear.append("ai_api_key"))

        if update.voice is not None:
            for name in ("whisper_url", "tts_provider", "tts_base_url", "tts_model", "tts_voice"):
                value = getattr(update.voice, name)
                if value is not None:
                    voice_data[name] = value
            if update.voice.tts_api_key is not None:
                key = update.voice.tts_api_key.strip()
                voice_data["tts_api_key"] = key
                (secret_set.__setitem__("tts_api_key", key) if key else secret_clear.append("tts_api_key"))

        for field_name, store_key in (("modrinth_key", "modrinth_key"), ("curseforge_key", "curseforge_key")):
            value = getattr(update, field_name)
            if value is not None:
                stripped = value.strip()
                if stripped:
                    secret_set[store_key] = stripped
                else:
                    secret_clear.append(store_key)

        # Validate the whole configuration first.
        new_ai = AIConfig(**ai_data)
        new_voice = VoiceConfig(**voice_data)

        store = SecretStore(config.data_dir)
        if secret_set:
            store.update(secret_set)
        if secret_clear:
            store.remove(secret_clear)

        public_config["ai"] = new_ai.model_dump(exclude={"api_key"})
        public_config["voice"] = new_voice.model_dump(exclude={"tts_api_key"})
        public_config.setdefault("apis", {})
        public_config["apis"].pop("modrinth_key", None)
        public_config["apis"].pop("curseforge_key", None)
        self._write_public_config(public_config)

        config.ai = new_ai
        config.voice = new_voice
        if "modrinth_key" in secret_set:
            config.apis.modrinth_key = secret_set["modrinth_key"]
        elif "modrinth_key" in secret_clear:
            config.apis.modrinth_key = ""
        if "curseforge_key" in secret_set:
            config.apis.curseforge_key = secret_set["curseforge_key"]
        elif "curseforge_key" in secret_clear:
            config.apis.curseforge_key = ""
        return await self.overview()

    async def delete_secret(self, name: str) -> SettingsOverview:
        store_key = SECRET_KEYS.get(name.strip().lower())
        if not store_key:
            raise KeyError(name)
        SecretStore(config.data_dir).remove([store_key])
        if store_key == "modrinth_key":
            config.apis.modrinth_key = ""
        elif store_key == "curseforge_key":
            config.apis.curseforge_key = ""
        elif store_key == "ai_api_key":
            config.ai.api_key = ""
        elif store_key == "tts_api_key":
            config.voice.tts_api_key = ""
        return await self.overview()

    def admin_view(self) -> AdminSettingsResponse:
        return AdminSettingsResponse(
            ai=_public_ai(),
            modrinth_key=_mask(config.apis.modrinth_key),
            curseforge_key=_mask(config.apis.curseforge_key),
            admin_token_configured=bool(config.security.admin_token),
        )

    def update(self, update: AdminSettingsUpdate) -> AdminSettingsResponse:
        public_config = self._read_public_config()
        ai_data = self._ai_data(public_config)
        secret_updates: dict[str, str | None] = {
            "modrinth_key": update.modrinth_key,
            "curseforge_key": update.curseforge_key,
            "admin_token": update.admin_token,
        }
        if update.ai:
            for name in ("provider", "base_url", "model", "timeout_seconds", "max_tokens", "temperature"):
                value = getattr(update.ai, name)
                if value is not None:
                    ai_data[name] = value
            secret_updates["ai_api_key"] = update.ai.api_key
            if update.ai.api_key is not None:
                ai_data["api_key"] = update.ai.api_key

        new_ai = AIConfig(**ai_data)
        SecretStore(config.data_dir).update(secret_updates)
        public_config["ai"] = new_ai.model_dump(exclude={"api_key"})
        public_config.setdefault("apis", {})
        public_config["apis"].pop("modrinth_key", None)
        public_config["apis"].pop("curseforge_key", None)
        public_config.setdefault("security", {})
        public_config["security"].pop("admin_token", None)
        self._write_public_config(public_config)

        config.ai = new_ai
        if update.modrinth_key is not None:
            config.apis.modrinth_key = update.modrinth_key
        if update.curseforge_key is not None:
            config.apis.curseforge_key = update.curseforge_key
        if update.admin_token is not None:
            config.security.admin_token = update.admin_token
        return self.admin_view()

    @staticmethod
    def _ai_data(public_config: dict) -> dict:
        ai_data = dict(public_config.get("ai", {}))
        if "base_url" not in ai_data and "url" in ai_data:
            ai_data["base_url"] = ai_data.pop("url")
        # Preserve the live key so validation passes; excluded before writing.
        ai_data["api_key"] = config.ai.api_key
        return ai_data

    @staticmethod
    def _voice_data(public_config: dict) -> dict:
        voice_data = dict(public_config.get("voice", {}))
        voice_data["tts_api_key"] = config.voice.tts_api_key
        return voice_data

    @staticmethod
    def _read_public_config() -> dict:
        path = config.repo_root / "config.json"
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _write_public_config(contents: dict) -> None:
        path = config.repo_root / "config.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=path.parent) as temporary:
            json.dump(contents, temporary, indent=2)
            temporary.write("\n")
            temporary_path = Path(temporary.name)
        temporary_path.replace(path)


settings_service = SettingsService()
