from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from app.domain.common import to_json_safe
from app.domain.requirements.models import GenerationBrief, RequirementProfile


class ConfidenceLevel(str, Enum):
    UNDERSTOOD = "understood"
    UNCERTAIN = "uncertain"
    MISSING_INFORMATION = "missing_information"


@dataclass(frozen=True)
class RequirementExplanation:
    requested: tuple[str, ...] = ()
    decisions: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    follow_up_questions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in ("requested", "decisions", "assumptions", "follow_up_questions"):
            object.__setattr__(self, name, tuple(str(item).strip() for item in getattr(self, name) if str(item).strip()))

    def to_dict(self) -> dict[str, object]:
        return to_json_safe({"requested": self.requested, "decisions": self.decisions, "assumptions": self.assumptions, "follow_up_questions": self.follow_up_questions})


@dataclass(frozen=True)
class RequirementAnalysis:
    profile: RequirementProfile
    confidence: ConfidenceLevel
    # Keep this third for backwards-compatible positional construction from 1.8.2.
    explanation: RequirementExplanation = field(default_factory=RequirementExplanation)
    theme: str | None = None
    gameplay_style: tuple[str, ...] = ()
    difficulty: str | None = None
    target_mod_count: int | None = None
    qol_level: str | None = None
    performance_target: str | None = None
    shader_support: str | None = None
    ram_target_mb: int | None = None
    fps_target: int | None = None
    required_mods: frozenset[str] = field(default_factory=frozenset)
    forbidden_mods: frozenset[str] = field(default_factory=frozenset)
    missing_information: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.confidence, ConfidenceLevel):
            object.__setattr__(self, "confidence", ConfidenceLevel(str(self.confidence).lower()))
        if not isinstance(self.explanation, RequirementExplanation):
            raise TypeError("explanation must be a RequirementExplanation")
        object.__setattr__(self, "theme", self.theme.strip().lower() if self.theme else None)
        object.__setattr__(self, "gameplay_style", tuple(str(item).strip().lower() for item in self.gameplay_style if str(item).strip()))
        object.__setattr__(self, "required_mods", frozenset(str(item).strip().lower() for item in self.required_mods if str(item).strip()))
        object.__setattr__(self, "forbidden_mods", frozenset(str(item).strip().lower() for item in self.forbidden_mods if str(item).strip()))
        missing = tuple(str(item).strip() for item in self.missing_information if str(item).strip())
        # 1.8.2 represented missing information only in the explanation. Normalize
        # that legacy form into the new machine-readable field.
        if not missing and self.confidence is ConfidenceLevel.MISSING_INFORMATION:
            missing = self.explanation.follow_up_questions
        object.__setattr__(self, "missing_information", missing)
        if self.required_mods & self.forbidden_mods:
            raise ValueError("a mod cannot be both required and forbidden")
        if self.confidence is ConfidenceLevel.UNDERSTOOD and missing:
            raise ValueError("understood analysis cannot have missing_information")
        if self.confidence is ConfidenceLevel.MISSING_INFORMATION and not missing:
            raise ValueError("missing_information confidence requires missing_information")
        if missing and not self.explanation.follow_up_questions:
            object.__setattr__(self, "explanation", RequirementExplanation(self.explanation.requested, self.explanation.decisions, self.explanation.assumptions, missing))

    def to_dict(self) -> dict[str, object]:
        return to_json_safe({name: getattr(self, name) for name in self.__dataclass_fields__})


@dataclass(frozen=True)
class RequirementUpdate:
    add_features: frozenset[str] = frozenset()
    remove_features: frozenset[str] = frozenset()
    add_exclusions: frozenset[str] = frozenset()
    remove_exclusions: frozenset[str] = frozenset()
    replacement_prompt: str | None = None

    def __post_init__(self) -> None:
        for name in ("add_features", "remove_features", "add_exclusions", "remove_exclusions"):
            object.__setattr__(self, name, frozenset(str(item).strip().lower() for item in getattr(self, name) if str(item).strip()))
        if self.add_features & self.remove_features or self.add_exclusions & self.remove_exclusions:
            raise ValueError("a requirement cannot be added and removed in the same update")
        if self.replacement_prompt is not None and not self.replacement_prompt.strip():
            raise ValueError("replacement_prompt cannot be blank")

    def apply(self, profile: RequirementProfile) -> RequirementProfile:
        return profile.evolve(raw_prompt=self.replacement_prompt or profile.raw_prompt, features=(profile.features | self.add_features) - self.remove_features, exclusions=(profile.exclusions | self.add_exclusions) - self.remove_exclusions)

    def to_dict(self) -> dict[str, object]:
        return to_json_safe({name: getattr(self, name) for name in self.__dataclass_fields__})


@dataclass(frozen=True)
class GenerationRevision:
    base_brief: GenerationBrief
    update: RequirementUpdate
    reason: str

    def __post_init__(self) -> None:
        if not self.reason.strip():
            raise ValueError("revision reason is required")

    @property
    def revised_profile(self) -> RequirementProfile:
        return self.update.apply(self.base_brief.profile)

    def to_dict(self) -> dict[str, object]:
        return to_json_safe({"base_brief": self.base_brief, "update": self.update, "reason": self.reason})
