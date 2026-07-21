"""AI workflow schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class GameplayAnalysis(BaseModel):
    gameplay_goals: list[str] = Field(default_factory=list)
    must_have_features: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)


class CategoryPlan(BaseModel):
    categories: list[str] = Field(default_factory=list)
    search_queries: list[str] = Field(default_factory=list)
    target_mod_count: int = 40


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
