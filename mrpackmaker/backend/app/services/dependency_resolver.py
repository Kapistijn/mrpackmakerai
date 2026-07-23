"""Automatic dependency closure with bounded repair diagnostics."""
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
    def message(self) -> str: return f'Dependency resolution failed: Mod: {self.parent}; Missing: {self.dependency}; Reason: {self.reason}'
@dataclass(frozen=True)
class DependencyResolution:
    mods: tuple[ModEntry, ...]
    failures: tuple[DependencyFailure, ...] = ()
    optional_added: int = 0
    passes: int = 0
    events: tuple[DependencyEvent, ...] = ()
    @property
    def complete(self) -> bool: return not self.failures
class DependencyResolver:
    def __init__(self, resolver: ModResolver, *, max_passes: int = 5) -> None:
        if max_passes < 1: raise ValueError('max_passes must be positive')
        self._resolver=resolver; self._max_passes=max_passes; self._cache: dict[tuple[str,str,str,str], ModEntry|None]={}
    async def _lookup(self, source: str, project_id: str, mc: str, loader: LoaderType) -> ModEntry|None:
        key=(source.strip().lower(), project_id.strip(), mc.strip(), loader.value)
        if key not in self._cache:
            try: self._cache[key]=await self._resolver.resolve_mod(source, project_id, mc, loader)
            except UnknownModSourceError: self._cache[key]=None
        return self._cache[key]
    @staticmethod
    def _key(mod: ModEntry) -> str: return f'{mod.source}:{mod.id}'
    @staticmethod
    def _dep_key(dep: ModDependency, parent: ModEntry) -> str: return f'{dep.source or parent.source}:{dep.project_id}'
    @staticmethod
    def _has_identity(mods: list[ModEntry], candidate: ModEntry) -> bool: return any(mod_identity(item)==mod_identity(candidate) for item in mods)
    async def resolve_pack(self, selected: list[ModEntry], mc: str, loader: LoaderType, *, include_optional: bool=False) -> DependencyResolution:
        mods=list(ModResolver.deduplicate(selected)); failures={}; events=[]; optional_added=0
        for pass_number in range(1,self._max_passes+1):
            events.append(DependencyEvent(pass_number,'scan','', 'checking dependencies')); additions=[]; pass_failures={}
            for parent in tuple(mods):
                for dep in parent.dependencies:
                    kind=dep.dependency_type.strip().casefold(); dep_key=self._dep_key(dep,parent); fk=(self._key(parent),dep_key)
                    if kind==INCOMPATIBLE:
                        if any(self._key(item)==dep_key for item in mods): pass_failures[fk]=DependencyFailure(*fk,'declared incompatible dependency is present')
                        continue
                    if kind==EMBEDDED or (kind==OPTIONAL and not include_optional): continue
                    if any(self._key(item)==dep_key for item in mods+additions): continue
                    events.append(DependencyEvent(pass_number,'search',dep_key,'searching compatible version'))
                    candidate=await self._lookup(dep.source or parent.source,dep.project_id,mc,loader)
                    if candidate is None: pass_failures[fk]=DependencyFailure(*fk,f'No compatible {loader.value} {mc} version exists'); events.append(DependencyEvent(pass_number,'reject',dep_key,'wrong loader or Minecraft version')); continue
                    if not candidate.file_name or not candidate.download_url: pass_failures[fk]=DependencyFailure(*fk,'Resolved metadata has no downloadable file'); continue
                    if not self._has_identity(mods+additions,candidate): additions.append(candidate); optional_added += int(kind==OPTIONAL); events.append(DependencyEvent(pass_number,'add',dep_key,'added dependency'))
            failures=pass_failures
            if not additions: events.append(DependencyEvent(pass_number,'complete',None,'repair complete' if not failures else 'repair blocked')); return DependencyResolution(tuple(ModResolver.deduplicate(mods)),tuple(failures.values()),optional_added,pass_number,tuple(events))
            mods=ModResolver.deduplicate(mods+additions)
        return DependencyResolution(tuple(mods),tuple(failures.values()) or (DependencyFailure('pack','dependency graph',f'Resolution exceeded {self._max_passes} passes'),),optional_added,self._max_passes,tuple(events))
