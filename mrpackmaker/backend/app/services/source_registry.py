"""Extensible registry for Minecraft mod catalog integrations.

The rest of the application talks to this registry instead of checking
``if source == modrinth``.  A new catalog only has to implement
``ModCatalogProvider`` and be registered during application startup.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from app.models.enums import LoaderType
from app.schemas.mod import ModEntry


class UnknownModSourceError(ValueError):
    pass


class ModCatalogProvider(Protocol):
    source_id: str

    @property
    def available(self) -> bool: ...

    async def search(
        self,
        query: str,
        mc_version: str,
        loader: LoaderType,
        category: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[ModEntry], int]: ...

    async def get_mod_detail(
        self, mod_id: str, mc_version: str, loader: LoaderType
    ) -> ModEntry | None: ...

    async def close(self) -> None: ...


class ModSourceRegistry:
    def __init__(self, providers: Iterable[ModCatalogProvider] = ()) -> None:
        self._providers: dict[str, ModCatalogProvider] = {}
        for provider in providers:
            self.register(provider)

    def register(self, provider: ModCatalogProvider) -> None:
        source_id = provider.source_id.strip().lower()
        if not source_id:
            raise ValueError("Mod source provider must have a source_id")
        if source_id in self._providers:
            raise ValueError(f"A provider for '{source_id}' is already registered")
        self._providers[source_id] = provider

    def get(self, source_id: str) -> ModCatalogProvider:
        try:
            return self._providers[source_id.strip().lower()]
        except KeyError as exc:
            available = ", ".join(sorted(self._providers)) or "none"
            raise UnknownModSourceError(
                f"Unknown mod source '{source_id}'. Configured sources: {available}"
            ) from exc

    def ids(self, *, available_only: bool = False) -> list[str]:
        return [
            source_id
            for source_id, provider in self._providers.items()
            if not available_only or provider.available
        ]

    def providers(self, *, available_only: bool = False) -> tuple[ModCatalogProvider, ...]:
        return tuple(
            provider
            for provider in self._providers.values()
            if not available_only or provider.available
        )

    def is_available(self, source_id: str) -> bool:
        return self.get(source_id).available

    async def close(self) -> None:
        for provider in self._providers.values():
            await provider.close()


def create_default_registry() -> ModSourceRegistry:
    """Wire built-in catalog adapters; deployments may register more adapters.

    The imports stay local to avoid coupling provider implementations to the
    registry's public protocol.
    """
    from app.config import config
    from app.services.curseforge import CurseForgeClient
    from app.services.modrinth import ModrinthClient

    return ModSourceRegistry(
        [
            ModrinthClient(config.apis.modrinth_key),
            CurseForgeClient(config.apis.curseforge_key),
        ]
    )
