from __future__ import annotations

from dataclasses import dataclass
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
        object.__setattr__(self, "requested", tuple(str(item) for item in self.requested))
        object.__setattr__(self, "decisions", tuple(str(item) for item in self.decisions))
        object.__setattr__(self, "assumptions", tuple(str(item) for item in self.assumptions))
        object.__setattr__(self, "follow_up_questions", tuple(str(item) for item in self.follow_up_questions))

    def to_dict(self) -> dict[str, object]:
        return to_json_safe({"requested": self.requested, "decisions": self.decisions, "assumptions": self.assumptions, "follow_up_questions": self.follow_up_questions})


@dataclass(frozen=True)
class RequirementAnalysis:
    profile: RequirementProfile
    confidence: ConfidenceLevel
    explanation: RequirementExplanation = RequirementExplanation()

    def __post_init__(self) -> None:
        if not isinstance(self.confidence, ConfidenceLevel):
            object.__setattr__(self, "confidence", ConfidenceLevel(str(self.confidence).lower()))
        if self.confidence is ConfidenceLevel.MISSING_INFORMATION and not self.explanation.follow_up_questions:
            raise ValueError("missing information requires a follow-up question")

    def to_dict(self) -> dict[str, object]:
        return to_json_safe({"profile": self.profile, "confidence": self.confidence, "explanation": self.explanation})


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
        return profile.evolve(
            raw_prompt=self.replacement_prompt or profile.raw_prompt,
            features=(profile.features | self.add_features) - self.remove_features,
            exclusions=(profile.exclusions | self.add_exclusions) - self.remove_exclusions,
        )

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
