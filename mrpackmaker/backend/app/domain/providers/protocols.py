from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence, runtime_checkable

from app.domain.common import Loader, to_json_safe
from app.domain.mods.models import ModCandidate
from app.domain.requirements.models import GenerationBrief, RequirementProfile


@dataclass(frozen=True)
class SelectionResult:
    candidate: ModCandidate
    score: float
    reason: str

    def __post_init__(self) -> None:
        if not 0 <= self.score <= 1 or not self.reason.strip():
            raise ValueError("invalid selection result")

    def to_dict(self) -> dict[str, object]:
        return to_json_safe({"candidate": self.candidate, "score": self.score, "reason": self.reason})


@dataclass(frozen=True)
class DependencyResolutionResult:
    resolved: tuple[ModCandidate, ...] = ()
    missing: tuple[str, ...] = ()
    conflicts: tuple[str, ...] = ()
    cycles: tuple[tuple[str, ...], ...] = ()
    version_conflicts: tuple[str, ...] = ()
    success: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "resolved", tuple(self.resolved))
        object.__setattr__(self, "missing", tuple(str(item) for item in self.missing))
        object.__setattr__(self, "conflicts", tuple(str(item) for item in self.conflicts))
        object.__setattr__(self, "cycles", tuple(tuple(str(item) for item in cycle) for cycle in self.cycles))
        object.__setattr__(self, "version_conflicts", tuple(str(item) for item in self.version_conflicts))
        has_errors = bool(self.missing or self.conflicts or self.cycles or self.version_conflicts)
        if self.success == has_errors:
            raise ValueError("success must be true exactly when no resolution errors exist")

    @property
    def is_complete(self) -> bool:
        return self.success and not self.missing and not self.conflicts and not self.cycles and not self.version_conflicts

    def to_dict(self) -> dict[str, object]:
        return to_json_safe({"resolved": self.resolved, "missing": self.missing, "conflicts": self.conflicts, "cycles": self.cycles, "version_conflicts": self.version_conflicts, "success": self.success})


@runtime_checkable
class RequirementAnalyzer(Protocol):
    async def analyze_requirements(self, raw_prompt: str) -> RequirementProfile: ...


@runtime_checkable
class PromptOptimizer(Protocol):
    async def build_brief(self, profile: RequirementProfile) -> GenerationBrief: ...


@runtime_checkable
class CandidateSelector(Protocol):
    async def select(self, brief: GenerationBrief, candidates: Sequence[ModCandidate]) -> Sequence[SelectionResult]: ...


@runtime_checkable
class AIProvider(RequirementAnalyzer, PromptOptimizer, CandidateSelector, Protocol):
    """Runtime-checkable composition of the three AI capabilities.

    ``name`` is a method rather than a protocol property because Python's
    runtime_checkable structural checks support method-only protocols reliably.
    """

    def name(self) -> str: ...


@runtime_checkable
class ModCatalogProvider(Protocol):
    async def search(self, query: str, *, minecraft_version: str, loader: Loader, limit: int = 50, offset: int = 0) -> Sequence[ModCandidate]: ...
    async def get(self, project_id: str) -> ModCandidate | None: ...


@runtime_checkable
class ModrinthProvider(ModCatalogProvider, Protocol): ...


@runtime_checkable
class CurseForgeProvider(ModCatalogProvider, Protocol): ...


@runtime_checkable
class DependencyResolver(Protocol):
    async def resolve(self, selected: Sequence[ModCandidate], *, minecraft_version: str, loader: Loader) -> DependencyResolutionResult: ...
