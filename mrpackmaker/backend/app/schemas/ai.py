"""AI workflow schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class RequirementAnalysisSchema(BaseModel):
    theme: str | None = None
    gameplay_style: list[str] = Field(default_factory=list)
    difficulty: str | None = None
    target_mod_count: int | None = Field(default=None, ge=1, le=300)
    qol_level: Literal["none", "normal", "high", "maximum"] | None = None
    performance_target: str | None = None
    shader_support: str | None = None
    ram_target_mb: int | None = Field(default=None, gt=0)
    fps_target: int | None = Field(default=None, gt=0)
    required_mods: list[str] = Field(default_factory=list)
    forbidden_mods: list[str] = Field(default_factory=list)
    confidence: Literal["understood", "uncertain", "missing_information"]
    missing_information: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def missing_information_requires_uncertainty(self):
        if self.missing_information and self.confidence == "understood":
            raise ValueError("missing_information requires uncertain or missing_information confidence")
        if self.confidence == "missing_information" and not self.missing_information:
            raise ValueError("missing_information confidence requires missing_information")
        return self


class IntentAnalysisSchema(BaseModel):
    """AI enrichment of the deterministic intent analysis.

    The deterministic :class:`app.services.intent_analysis.IntentAnalysis` is
    always produced first; this schema only lets a provider refine the goal and
    extend the category / avoid lists. It can never weaken the deterministic
    guarantees.
    """

    goal: str = ""
    categories: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)
    realism_focus: bool = False
    confidence: Literal["understood", "uncertain", "missing_information"] = "understood"
    missing_information: list[str] = Field(default_factory=list)


class GameplayAnalysis(BaseModel):
    gameplay_goals: list[str] = Field(default_factory=list)
    must_have_features: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)


class CategoryPlan(BaseModel):
    categories: list[str] = Field(default_factory=list)
    search_queries: list[str] = Field(default_factory=list)
    target_mod_count: int = Field(default=40, ge=1, le=300)


class ModCandidate(BaseModel):
    id: str
    source: str
    name: str


class ModRanking(BaseModel):
    selected_ids: list[str] = Field(default_factory=list)
    rejected_ids: list[str] = Field(default_factory=list)
    reasoning: str = ""


class FinalModList(BaseModel):
    mod_ids: list[str] = Field(default_factory=list)
    summary: str = ""


class AIProgressEvent(BaseModel):
    step: int
    total_steps: int = 7
    message: str
    status: str = "running"
    data: dict | None = None
