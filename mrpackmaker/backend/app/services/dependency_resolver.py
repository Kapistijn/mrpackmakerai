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
_METADATA_CACHE: dict[tuple[str, str, str, str], ModEntry | None] = {}

@dataclass(frozen=True)
class DependencyFailure:
    parent: str
    dependency: str
    reason: str
    def message(self) -> str:
        return f"Dependency resolution failed: Mod: {self.parent}; Missing: {self.dependency}; Reason: {self.reason}"

@dataclass(frozen=True)
class DependencyResolution:
    mods: tuple[ModEntry, ...]
    failures: tuple[DependencyFailure, ...] = ()
    optional_added: int = 0
    passes: int = 0
    @property
    def complete(self) -> bool:
        return not self.failures

class DependencyResolver:
    """Resolve a compatible dependency closure with bounded, cached passes."""
    def __init__(self, resolver: ModResolver, *, max_passes: int = 5) -> None:
        if max_passes < 1: raise ValueError("max_passes must be positive")
        self._resolver = resolver
        self._max_passes = max_passes

    async def _lookup(self, source: str, project_id: str, mc: str, loader: LoaderType) -> ModEntry | None:
        key = (source.strip().lower(), project_id.strip(), mc.strip(), loader.value)
        if key not in _METADATA_CACHE:
            try: _METADATA_CACHE[key] = await self._resolver.resolve_mod(source, project_id, mc, loader)
            except UnknownModSourceError: _METADATA_CACHE[key] = None
        return _METADATA_CACHE[key]

    @staticmethod
    def _key(mod: ModEntry) -> str: return f"{mod.source}:{mod.id}"
    @staticmethod
    def _dep_key(dep: ModDependency, parent: ModEntry) -> str: return f"{dep.source or parent.source}:{dep.project_id}"
    @staticmethod
    def _has_identity(mods: list[ModEntry], candidate: ModEntry) -> bool: return any(mod_identity(item) == mod_identity(candidate) for item in mods)

    async def resolve_pack(self, selected: list[ModEntry], mc: str, loader: LoaderType, *, include_optional: bool = False) -> DependencyResolution:
        mods = list(ModResolver.deduplicate(selected))
        for pass_number in range(1, self._max_passes + 1):
            failures: list[DependencyFailure] = []
            additions: list[ModEntry] = []
            optional_added = 0
            for parent in tuple(mods):
                for dep in parent.dependencies:
                    kind = dep.dependency_type.casefold()
                    dep_key = self._dep_key(dep, parent)
                    if kind == INCOMPATIBLE:
                        if any(self._key(item) == dep_key for item in mods): failures.append(DependencyFailure(self._key(parent), dep_key, "declared incompatible dependency is present"))
                        continue
                    if kind == EMBEDDED or (kind == OPTIONAL and not include_optional): continue
                    if any(self._key(item) == dep_key for item in mods + additions): continue
                    candidate = await self._lookup(dep.source or parent.source, dep.project_id, mc, loader)
                    if candidate is None:
                        failures.append(DependencyFailure(self._key(parent), dep_key, f"No compatible {loader.value} {mc} version found")); continue
                    if not candidate.file_name or not candidate.download_url:
                        failures.append(DependencyFailure(self._key(parent), dep_key, "Resolved metadata has no downloadable file")); continue
                    if not self._has_identity(mods + additions, candidate):
                        additions.append(candidate); optional_added += int(kind == OPTIONAL)
            if failures: return DependencyResolution(tuple(ModResolver.deduplicate(mods + additions)), tuple(failures), optional_added, pass_number)
            if not additions: return DependencyResolution(tuple(ModResolver.deduplicate(mods)), (), optional_added, pass_number)
            mods = ModResolver.deduplicate(mods + additions)
        return DependencyResolution(tuple(mods), (DependencyFailure("pack", "dependency graph", f"Resolution exceeded {self._max_passes} passes"),), 0, self._max_passes)
