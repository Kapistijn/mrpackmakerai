from __future__ import annotations

from dataclasses import dataclass, field, replace

from app.domain.common import FrozenMap, Loader, PerformanceTarget


def _strings(values: object) -> frozenset[str]:
    if not values:
        return frozenset()
    return frozenset(str(value).strip().lower() for value in values if str(value).strip())


@dataclass(frozen=True)
class RequirementProfile:
    raw_prompt: str
    minecraft_version: str
    loader: Loader
    theme: str | None = None
    subthemes: frozenset[str] = field(default_factory=frozenset)
    features: frozenset[str] = field(default_factory=frozenset)
    exclusions: frozenset[str] = field(default_factory=frozenset)
    min_mods: int = 0
    max_mods: int | None = None
    min_downloads: int = 0
    multiplayer: bool = False
    server: bool = False
    performance_target: PerformanceTarget = PerformanceTarget.BALANCED
    loader_version: str | None = None
    language: str = "en"

    def __post_init__(self) -> None:
        if not self.raw_prompt.strip() or not self.minecraft_version.strip():
            raise ValueError("raw_prompt and minecraft_version are required")
        if not isinstance(self.loader, Loader):
            object.__setattr__(self, "loader", Loader.from_str(str(self.loader)))
        if self.min_mods < 0 or self.min_downloads < 0:
            raise ValueError("mod counts and downloads cannot be negative")
        if self.max_mods is not None and (self.max_mods < 0 or self.max_mods < self.min_mods):
            raise ValueError("max_mods must be >= min_mods")
        object.__setattr__(self, "subthemes", _strings(self.subthemes))
        object.__setattr__(self, "features", _strings(self.features))
        object.__setattr__(self, "exclusions", _strings(self.exclusions))
        overlap = self.exclusions & (self.subthemes | self.features)
        if overlap:
            raise ValueError(f"values cannot be both included and excluded: {sorted(overlap)}")

    def is_excluded(self, category: str) -> bool:
        return category.strip().lower() in self.exclusions

    def evolve(self, **changes: object) -> "RequirementProfile":
        return replace(self, **changes)

    def to_dict(self) -> dict[str, object]:
        return {
            "raw_prompt": self.raw_prompt,
            "minecraft_version": self.minecraft_version,
            "loader": self.loader.value,
            "theme": self.theme,
            "subthemes": sorted(self.subthemes),
            "features": sorted(self.features),
            "exclusions": sorted(self.exclusions),
            "min_mods": self.min_mods,
            "max_mods": self.max_mods,
            "min_downloads": self.min_downloads,
            "multiplayer": self.multiplayer,
            "server": self.server,
            "performance_target": self.performance_target.value,
            "loader_version": self.loader_version,
            "language": self.language,
        }


@dataclass(frozen=True)
class GenerationBrief:
    profile: RequirementProfile
    enriched_intent: str
    category_quotas: FrozenMap[int]
    seed: int

    def __post_init__(self) -> None:
        if not self.enriched_intent.strip():
            raise ValueError("enriched_intent is required")
        quotas = self.category_quotas if isinstance(self.category_quotas, FrozenMap) else FrozenMap.from_mapping(self.category_quotas)
        if any(value < 0 for value in quotas.values()):
            raise ValueError("category quotas cannot be negative")
        if sum(quotas.values()) < self.profile.min_mods:
            raise ValueError("category quotas do not satisfy min_mods")
        object.__setattr__(self, "category_quotas", quotas)

    @property
    def target_count(self) -> int:
        return max(self.profile.min_mods, sum(self.category_quotas.values()))

    def with_seed(self, seed: int) -> "GenerationBrief":
        return replace(self, seed=seed)

    def to_dict(self) -> dict[str, object]:
        return {"profile": self.profile.to_dict(), "enriched_intent": self.enriched_intent, "category_quotas": self.category_quotas.to_dict(), "seed": self.seed}
