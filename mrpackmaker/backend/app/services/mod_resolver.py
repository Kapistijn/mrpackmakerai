"""Source-agnostic mod and loader resolution."""

from __future__ import annotations

from app.models.enums import LoaderType
from app.schemas.mod import ModEntry
from app.services.curseforge import CurseForgeClient
from app.services.modrinth import ModrinthClient
from app.services.source_registry import ModSourceRegistry, UnknownModSourceError


LIBRARY_MODS: dict[LoaderType, list[tuple[str, str, str]]] = {
    LoaderType.FABRIC: [
        ("modrinth", "fabric-api", "Fabric API"),
        ("modrinth", "fabric-language-kotlin", "Fabric Language Kotlin"),
    ],
    LoaderType.FORGE: [],
    LoaderType.NEOFORGE: [("modrinth", "neoforge", "NeoForge")],
}


class ModResolver:
    """Resolve source-qualified mod IDs through a catalog registry.

    The two optional concrete clients keep the original constructor compatible
    while new callers can pass any registry, including a registry with custom
    or enterprise catalog plugins.
    """

    def __init__(
        self,
        modrinth: ModrinthClient | None = None,
        curseforge: CurseForgeClient | None = None,
        *,
        registry: ModSourceRegistry | None = None,
    ) -> None:
        if registry is None:
            if modrinth is None:
                raise ValueError("A source registry or Modrinth client is required")
            providers = [modrinth]
            if curseforge is not None:
                providers.append(curseforge)
            registry = ModSourceRegistry(providers)
        self.registry = registry
        # Compatibility properties for the pre-registry compatibility service.
        self.modrinth = modrinth
        self.curseforge = curseforge

    async def close(self) -> None:
        await self.registry.close()

    async def resolve_loader_version(self, loader: LoaderType, mc_version: str) -> str | None:
        # Loader metadata is published by Modrinth today.  Other catalog
        # plugins can add a loader resolver without affecting the selection
        # pipeline; until then we do not emit an unsafe "latest" value.
        try:
            provider = self.registry.get("modrinth")
        except UnknownModSourceError:
            return None
        search_loader_version = getattr(provider, "search_loader_version", None)
        if search_loader_version is None:
            return None
        return await search_loader_version(loader, mc_version)

    async def resolve_mod(
        self,
        source: str,
        mod_id: str,
        mc_version: str,
        loader: LoaderType,
    ) -> ModEntry | None:
        return await self.registry.get(source).get_mod_detail(mod_id, mc_version, loader)

    async def resolve_mod_by_key(
        self,
        mod_key: str,
        mc_version: str,
        loader: LoaderType,
    ) -> ModEntry | None:
        """Resolve a ``source:id`` key; old unqualified keys mean Modrinth."""
        source_id, separator, mod_id = mod_key.partition(":")
        if not separator:
            source_id, mod_id = "modrinth", source_id
        if not source_id or not mod_id:
            return None
        return await self.resolve_mod(source_id, mod_id, mc_version, loader)

    async def inject_library_mods(
        self,
        mods: list[ModEntry],
        mc_version: str,
        loader: LoaderType,
    ) -> list[ModEntry]:
        existing_ids = {self.mod_key(mod) for mod in mods}
        result = list(mods)
        for source_id, mod_id, _name in LIBRARY_MODS.get(loader, []):
            key = f"{source_id}:{mod_id}"
            if key in existing_ids:
                continue
            try:
                entry = await self.resolve_mod(source_id, mod_id, mc_version, loader)
            except UnknownModSourceError:
                entry = None
            if entry:
                result.append(entry)
                existing_ids.add(key)
        return result

    @staticmethod
    def mod_key(mod: ModEntry) -> str:
        return f"{mod.source}:{mod.id}"
