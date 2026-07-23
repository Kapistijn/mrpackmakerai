"""Graph-first dependency closure resolution with deterministic repair diagnostics."""
from __future__ import annotations
from dataclasses import dataclass
from app.models.enums import LoaderType
from app.schemas.mod import ModDependency, ModEntry
from app.services.mod_resolver import ModResolver, mod_identity
from app.services.source_registry import UnknownModSourceError

REQUIRED, OPTIONAL, EMBEDDED, INCOMPATIBLE = 'required','optional','embedded','incompatible'

@dataclass(frozen=True)
class DependencyEvent:
    pass_number: int
    action: str
    dependency: str | None = None
    result: str | None = None

@dataclass(frozen=True)
class DependencyFailure:
    parent: str
    dependency: str
    reason: str
    suggestion: str | None = None
    def message(self) -> str:
        suffix = f" Suggestion: {self.suggestion}" if self.suggestion else ""
        return f"Dependency resolution failed: Mod: {self.parent}; Missing: {self.dependency}; Reason: {self.reason}.{suffix}"

@dataclass(frozen=True)
class DependencyResolution:
    mods: tuple[ModEntry, ...]
    failures: tuple[DependencyFailure, ...] = ()
    optional_added: int = 0
    passes: int = 0
    events: tuple[DependencyEvent, ...] = ()
    cycles: tuple[tuple[str, ...], ...] = ()
    @property
    def complete(self) -> bool: return not self.failures and not self.cycles

class DependencyResolver:
    """Resolve the complete closure once, stopping when a pass makes no change."""
    def __init__(self, resolver: ModResolver, *, max_passes: int = 5) -> None:
        if max_passes < 1: raise ValueError('max_passes must be positive')
        self._resolver = resolver
        self._max_passes = max_passes
        self._cache: dict[tuple[str,str,str,str], ModEntry | None] = {}

    @staticmethod
    def _key(mod: ModEntry) -> str: return f'{mod.source}:{mod.id}'
    @staticmethod
    def _dep_key(dep: ModDependency, parent: ModEntry) -> str: return f'{dep.source or parent.source}:{dep.project_id}'
    @staticmethod
    def _has_identity(mods: list[ModEntry], candidate: ModEntry) -> bool: return any(mod_identity(m) == mod_identity(candidate) for m in mods)

    async def _lookup(self, source: str, project_id: str, mc: str, loader: LoaderType) -> ModEntry | None:
        key = (source.strip().lower(), project_id.strip(), mc.strip(), loader.value)
        if key not in self._cache:
            try: self._cache[key] = await self._resolver.resolve_mod(source, project_id, mc, loader)
            except UnknownModSourceError: self._cache[key] = None
        return self._cache[key]

    @staticmethod
    def _cycles(mods: list[ModEntry]) -> tuple[tuple[str, ...], ...]:
        by_key = {f'{m.source}:{m.id}': m for m in mods}; found: set[tuple[str, ...]] = set(); active: list[str] = []
        def canonical(ring: list[str]) -> tuple[str, ...]: return min(tuple(ring[i:]+ring[:i]) for i in range(len(ring)))
        def visit(key: str) -> None:
            if key in active:
                found.add(canonical(active[active.index(key):])); return
            if key not in by_key: return
            active.append(key)
            for dep in by_key[key].dependencies:
                if dep.dependency_type.casefold() != INCOMPATIBLE:
                    visit(f'{dep.source or by_key[key].source}:{dep.project_id}')
            active.pop()
        for key in sorted(by_key): visit(key)
        return tuple(sorted(found))

    def _unresolved_required(self, mods: list[ModEntry]) -> list[tuple[str, str]]:
        """Required dependency edges whose target is still absent from the pack."""
        present = {self._key(m) for m in mods}
        missing: list[tuple[str, str]] = []
        for parent in mods:
            for dep in parent.dependencies:
                if dep.dependency_type.strip().casefold() == REQUIRED:
                    dep_key = self._dep_key(dep, parent)
                    if dep_key not in present:
                        missing.append((self._key(parent), dep_key))
        return missing

    async def resolve_pack(self, selected: list[ModEntry], mc: str, loader: LoaderType, *, include_optional: bool = False) -> DependencyResolution:
        mods = list(ModResolver.deduplicate(selected)); events: list[DependencyEvent] = []; failures: dict[tuple[str,str], DependencyFailure] = {}; optional_added = 0
        for pass_number in range(1, self._max_passes + 1):
            before = tuple(self._key(m) for m in mods); additions: list[ModEntry] = []; pass_failures: dict[tuple[str,str], DependencyFailure] = {}
            events.append(DependencyEvent(pass_number, 'scan', None, f'checking {len(mods)} mods'))
            for parent in tuple(mods):
                for dep in parent.dependencies:
                    kind = dep.dependency_type.strip().casefold(); dep_key = self._dep_key(dep, parent); failure_key = (self._key(parent), dep_key)
                    if kind == INCOMPATIBLE:
                        if any(self._key(m) == dep_key for m in mods): pass_failures[failure_key] = DependencyFailure(*failure_key, 'declared incompatible dependency is present', 'remove one of the conflicting mods')
                        continue
                    if kind == EMBEDDED or (kind == OPTIONAL and not include_optional): continue
                    if any(self._key(m) == dep_key for m in mods + additions): continue
                    events.append(DependencyEvent(pass_number, 'search', dep_key, 'searching compatible version'))
                    candidate = await self._lookup(dep.source or parent.source, dep.project_id, mc, loader)
                    if candidate is None:
                        pass_failures[failure_key] = DependencyFailure(*failure_key, f'No compatible {loader.value} {mc} version exists', f'install a {loader.value} {mc} variant or remove {self._key(parent)}')
                        events.append(DependencyEvent(pass_number, 'reject', dep_key, 'no compatible version'))
                    elif not candidate.file_name or not candidate.download_url:
                        pass_failures[failure_key] = DependencyFailure(*failure_key, 'metadata has no downloadable file')
                    elif not self._has_identity(mods + additions, candidate):
                        additions.append(candidate); optional_added += int(kind == OPTIONAL); events.append(DependencyEvent(pass_number, 'add', dep_key, 'dependency added'))
            mods = ModResolver.deduplicate(mods + additions); failures = pass_failures
            cycles = self._cycles(mods)
            if cycles: return DependencyResolution(tuple(mods), tuple(failures.values()), optional_added, pass_number, tuple(events), cycles)
            after = tuple(self._key(m) for m in mods)
            if not additions or after == before:
                events.append(DependencyEvent(pass_number, 'complete', None, 'repair complete' if not failures else 'no further changes possible'))
                return DependencyResolution(tuple(mods), tuple(failures.values()), optional_added, pass_number, tuple(events))
        events.append(DependencyEvent(self._max_passes, 'complete', None, 'repair limit reached'))
        remaining = self._unresolved_required(mods)
        if remaining:
            detailed = tuple(
                DependencyFailure(parent, dep, f'still unresolved after {self._max_passes} repair passes', 'confirm a compatible version exists on Modrinth/CurseForge, or remove the parent mod')
                for parent, dep in remaining
            )
        else:
            detailed = tuple(failures.values())
        return DependencyResolution(tuple(mods), detailed, optional_added, self._max_passes, tuple(events))
