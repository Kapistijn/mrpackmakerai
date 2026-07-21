"""Server-side settings updates without ever serialising secrets to clients."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import NamedTemporaryFile

from app.config import AIConfig, config
from app.schemas.settings import AISettingsPublic, AdminSettingsResponse, AdminSettingsUpdate, SettingsOverview
from app.services.secret_store import SecretStore
from app.services.source_registry import create_default_registry


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
            voice={
                "whisper_url": config.voice.whisper_url,
                "tts_provider": config.voice.tts_provider,
                "tts_base_url": config.voice.tts_base_url,
            },
            mod_sources=sources,
        )

    def set_model(self, model: str) -> AISettingsPublic:
        """Persist the active AI model without requiring admin credentials.

        The model name is not a secret, so choosing it is a normal user action.
        An empty string re-enables auto-selection of the first available model.
        Only the public ``ai`` block of ``config.json`` is rewritten; API keys
        stay in the encrypted secret store and are never touched here.
        """
        public_config = self._read_public_config()
        ai_data = dict(public_config.get("ai", {}))
        if "base_url" not in ai_data and "url" in ai_data:
            ai_data["base_url"] = ai_data.pop("url")
        ai_data["model"] = model.strip()
        # Preserve the in-memory key so validation passes; it is excluded again
        # before anything is written back to disk.
        ai_data["api_key"] = config.ai.api_key

        new_ai = AIConfig(**ai_data)
        public_config["ai"] = new_ai.model_dump(exclude={"api_key"})
        self._write_public_config(public_config)

        config.ai = new_ai
        return _public_ai()

    def admin_view(self) -> AdminSettingsResponse:
        return AdminSettingsResponse(
            ai=_public_ai(),
            modrinth_key=_mask(config.apis.modrinth_key),
            curseforge_key=_mask(config.apis.curseforge_key),
            admin_token_configured=bool(config.security.admin_token),
        )

    def update(self, update: AdminSettingsUpdate) -> AdminSettingsResponse:
        public_config = self._read_public_config()
        ai_data = dict(public_config.get("ai", {}))
        if "base_url" not in ai_data and "url" in ai_data:
            ai_data["base_url"] = ai_data.pop("url")
        ai_data["api_key"] = config.ai.api_key
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

        # Validation happens before either config file changes, avoiding a
        # half-applied configuration.
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
