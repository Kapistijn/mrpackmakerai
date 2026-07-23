"""Automatic dependency resolution shared by generation, compatibility, and export."""
from __future__ import annotations
from dataclasses import dataclass
from app.models.enums import LoaderType
from app.schemas.mod import ModDependency, ModEntry
from app.services.mod_resolver import ModResolver, mod_identity
from app.services.source_registry import UnknownModSourceError

REQUIRED = "required"
OPTIONAL = "optional"
EMBEDDED = "embedded"
INCOMPATIBLE = "incompatible"

@dataclass(frozen=True)
class DependencyFailure:
    parent: str
    dependency: str
    reason: str
    def message(self) -> str: return f"Dependency resolution failed: Mod: {self.parent}; Missing: {self.dependency}; Reason: {self.reason}"

@dataclass(frozen=True)
class DependencyResolution:
    mods: tuple[ModEntry, ...]
    failures: tuple[DependencyFailure, ...] = ()
    optional_added: int = 0
    passes: int = 0
    @property
    def complete(self) -> bool: return not self.failures

class DependencyResolver:
    """Resolve a compatible dependency closure with bounded, instance-scoped caching."""
    def __init__(self, resolver: ModResolver, *, max_passes: int = 5) -> None:
        if max_passes < 1: raise ValueError("max_passes must be positive")
        self._resolver = resolver; self._max_passes = max_passes; self._metadata_cache: dict[tuple[str, str, str, str], ModEntry | None] = {}

    async def _lookup(self, source: str, project_id: str, mc: str, loader: LoaderType) -> ModEntry | None:
        key = (source.strip().lower(), project_id.strip(), mc.strip(), loader.value)
        if key not in self._metadata_cache:
            try: self._metadata_cache[key] = await self._resolver.resolve_mod(source, project_id, mc, loader)
            except UnknownModSourceError: self._metadata_cache[key] = None
        return self._metadata_cache[key]

    @staticmethod
    def _key(mod: ModEntry) -> str: return f"{mod.source}:{mod.id}"
    @staticmethod
    def _dep_key(dep: ModDependency, parent: ModEntry) -> str: return f"{dep.source or parent.source}:{dep.project_id}"
    @staticmethod
    def _has_identity(mods: list[ModEntry], candidate: ModEntry) -> bool: return any(mod_identity(item) == mod_identity(candidate) for item in mods)

    async def resolve_pack(self, selected: list[ModEntry], mc: str, loader: LoaderType, *, include_optional: bool = False) -> DependencyResolution:
        mods = list(ModResolver.deduplicate(selected)); unresolved: dict[tuple[str, str], DependencyFailure] = {}; optional_total = 0
        for pass_number in range(1, self._max_passes + 1):
            additions: list[ModEntry] = []; pass_failures: dict[tuple[str, str], DependencyFailure] = {}
            for parent in tuple(mods):
                for dep in parent.dependencies:
                    kind = dep.dependency_type.strip().casefold(); dep_key = self._dep_key(dep, parent); failure_key = (self._key(parent), dep_key)
                    if kind == INCOMPATIBLE:
                        if any(self._key(item) == dep_key for item in mods): pass_failures[failure_key] = DependencyFailure(*failure_key, "declared incompatible dependency is present")
                        continue
                    if kind == EMBEDDED or (kind == OPTIONAL and not include_optional): continue
                    if any(self._key(item) == dep_key for item in mods + additions): continue
                    candidate = await self._lookup(dep.source or parent.source, dep.project_id, mc, loader)
                    if candidate is None:
                        pass_failures[failure_key] = DependencyFailure(*failure_key, f"No compatible {loader.value} {mc} version found"); continue
                    if not candidate.file_name or not candidate.download_url:
                        pass_failures[failure_key] = DependencyFailure(*failure_key, "Resolved metadata has no downloadable file"); continue
                    if not self._has_identity(mods + additions, candidate): additions.append(candidate); optional_total += int(kind == OPTIONAL)
            unresolved = pass_failures
            if not additions: return DependencyResolution(tuple(ModResolver.deduplicate(mods)), tuple(unresolved.values()), optional_total, pass_number)
            mods = ModResolver.deduplicate(mods + additions)
        return DependencyResolution(tuple(mods), tuple(unresolved.values()) or (DependencyFailure("pack", "dependency graph", f"Resolution exceeded {self._max_passes} passes"),), optional_total, self._max_passes)
