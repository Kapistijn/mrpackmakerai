from __future__ import annotations

from dataclasses import dataclass, field, replace

from app.domain.common import FrozenMap, Loader, PerformanceTarget, to_json_safe


def _strings(values: object) -> frozenset[str]:
    if not values:
        return frozenset()
    return frozenset(str(value).strip().lower() for value in values if str(value).strip())


def _optional_string(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip().lower()
    return value or None


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
    desired_categories: frozenset[str] = field(default_factory=frozenset)
    forbidden_categories: frozenset[str] = field(default_factory=frozenset)
    gameplay_loop: str | None = None
    difficulty: str | None = None
    progression_style: str | None = None
    playstyle_preferences: frozenset[str] = field(default_factory=frozenset)
    pack_styles: frozenset[str] = field(default_factory=frozenset)
    hardware_profile: str | None = None
    fps_priority: int | None = None
    shaders: bool | None = None
    ram_budget_mb: int | None = None
    client_server_preference: str | None = None
    required_mods: frozenset[str] = field(default_factory=frozenset)
    forbidden_mods: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if not self.raw_prompt.strip() or not self.minecraft_version.strip():
            raise ValueError("raw_prompt and minecraft_version are required")
        if not isinstance(self.loader, Loader):
            object.__setattr__(self, "loader", Loader.from_str(str(self.loader)))
        if not isinstance(self.performance_target, PerformanceTarget):
            try:
                object.__setattr__(self, "performance_target", PerformanceTarget(str(self.performance_target).lower()))
            except ValueError as exc:
                raise ValueError(f"invalid performance_target: {self.performance_target!r}") from exc
        if self.min_mods < 0 or self.min_downloads < 0:
            raise ValueError("mod counts and downloads cannot be negative")
        if self.max_mods is not None and (self.max_mods < 0 or self.max_mods < self.min_mods):
            raise ValueError("max_mods must be >= min_mods")
        if self.fps_priority is not None and not 0 <= self.fps_priority <= 100:
            raise ValueError("fps_priority must be between 0 and 100")
        if self.ram_budget_mb is not None and self.ram_budget_mb <= 0:
            raise ValueError("ram_budget_mb must be positive")
        for name in ("subthemes", "features", "exclusions", "desired_categories", "forbidden_categories", "playstyle_preferences", "pack_styles", "required_mods", "forbidden_mods"):
            object.__setattr__(self, name, _strings(getattr(self, name)))
        for name in ("theme", "gameplay_loop", "difficulty", "progression_style", "hardware_profile", "client_server_preference"):
            object.__setattr__(self, name, _optional_string(getattr(self, name)))
        overlap = self.exclusions & (self.subthemes | self.features)
        overlap |= self.forbidden_categories & self.desired_categories
        if overlap:
            raise ValueError(f"values cannot be both included and excluded: {sorted(overlap)}")
        if self.required_mods & self.forbidden_mods:
            raise ValueError("a mod cannot be both required and forbidden")

    def is_excluded(self, category: str) -> bool:
        return category.strip().lower() in self.exclusions or category.strip().lower() in self.forbidden_categories

    def evolve(self, **changes: object) -> "RequirementProfile":
        return replace(self, **changes)

    def to_dict(self) -> dict[str, object]:
        return to_json_safe({name: getattr(self, name) for name in self.__dataclass_fields__})


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
        return to_json_safe({"profile": self.profile, "enriched_intent": self.enriched_intent, "category_quotas": self.category_quotas, "seed": self.seed})
