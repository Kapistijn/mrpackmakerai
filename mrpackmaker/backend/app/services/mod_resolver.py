"""Source-agnostic mod and loader resolution."""

from __future__ import annotations

import re
from collections.abc import Iterable

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


def _identity_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (value or "").casefold())


def mod_identity(mod: ModEntry) -> str:
    """Return a cross-catalog identity for a compatible project.

    Slugs are the strongest shared signal between Modrinth and CurseForge;
    normalized names are the fallback. Source-qualified IDs are deliberately
    not used here because they are different for the same project.
    """
    slug = _identity_text(mod.slug)
    if slug:
        return f"slug:{slug}"
    name = _identity_text(mod.name)
    return f"name:{name}" if name else f"source:{mod.source}:{mod.id}"


def _quality(mod: ModEntry) -> tuple[int, int, int]:
    return (
        int(bool(mod.file_name and mod.download_url)),
        int(bool(mod.hashes.sha1 or mod.hashes.sha512)),
        mod.downloads,
    )


class ModResolver:
    """Resolve source-qualified mod IDs through a catalog registry."""

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
        self.modrinth = modrinth
        self.curseforge = curseforge

    async def close(self) -> None:
        await self.registry.close()

    async def resolve_loader_version(self, loader: LoaderType, mc_version: str) -> str | None:
        try:
            provider = self.registry.get("modrinth")
        except UnknownModSourceError:
            return None
        search_loader_version = getattr(provider, "search_loader_version", None)
        if search_loader_version is None:
            return None
        return await search_loader_version(loader, mc_version)

    async def resolve_mod(self, source: str, mod_id: str, mc_version: str, loader: LoaderType) -> ModEntry | None:
        return await self.registry.get(source).get_mod_detail(mod_id, mc_version, loader)

    async def resolve_mod_by_key(self, mod_key: str, mc_version: str, loader: LoaderType) -> ModEntry | None:
        source_id, separator, mod_id = mod_key.partition(":")
        if not separator:
            source_id, mod_id = "modrinth", source_id
        if not source_id or not mod_id:
            return None
        return await self.resolve_mod(source_id, mod_id, mc_version, loader)

    @staticmethod
    def deduplicate(mods: Iterable[ModEntry]) -> list[ModEntry]:
        """Collapse cross-source duplicates, retaining the best entry."""
        selected: dict[str, ModEntry] = {}
        for mod in mods:
            identity = mod_identity(mod)
            current = selected.get(identity)
            if current is None or _quality(mod) > _quality(current):
                selected[identity] = mod
        return list(selected.values())

    async def inject_library_mods(self, mods: list[ModEntry], mc_version: str, loader: LoaderType) -> list[ModEntry]:
        result = self.deduplicate(mods)
        existing_ids = {self.mod_key(mod) for mod in result}
        for source_id, mod_id, _name in LIBRARY_MODS.get(loader, []):
            key = f"{source_id}:{mod_id}"
            if key in existing_ids:
                continue
            try:
                entry = await self.resolve_mod(source_id, mod_id, mc_version, loader)
            except UnknownModSourceError:
                entry = None
            if entry and mod_identity(entry) not in {mod_identity(mod) for mod in result}:
                result.append(entry)
                existing_ids.add(key)
        return result

    @staticmethod
    def mod_key(mod: ModEntry) -> str:
        return f"{mod.source}:{mod.id}"
