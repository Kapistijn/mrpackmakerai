"""Pre-export self-check: does the pack actually satisfy the intent?

Before a pack is considered done the generator verifies that every requested
intent category is represented by at least one selected mod. Missing categories
produce targeted re-search queries so generation can try again instead of
silently shipping an incomplete pack.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.schemas.mod import ModEntry
from app.services.intent_analysis import IntentAnalysis
from app.services.quality_scoring import _CATEGORY_SYNONYMS, is_blocked, rank_by_quality
from app.services.pack_profile import PackProfile


@dataclass(frozen=True)
class RequirementCheck:
    satisfied: tuple[str, ...]
    missing: tuple[str, ...]

    @property
    def complete(self) -> bool:
        return not self.missing

    def to_dict(self) -> dict:
        return {"satisfied": list(self.satisfied), "missing": list(self.missing), "complete": self.complete}


def _covers(text: str, category: str) -> bool:
    synonyms = _CATEGORY_SYNONYMS.get(category, (category.replace("_", " "),))
    return any(s in text for s in synonyms)


def verify_requirements(mods: list[ModEntry], intent: IntentAnalysis) -> RequirementCheck:
    joined = " ".join(" ".join((m.name, m.slug, m.summary, *m.categories)) for m in mods).casefold()
    satisfied: list[str] = []
    missing: list[str] = []
    for category in intent.categories:
        (satisfied if _covers(joined, category) else missing).append(category)
    return RequirementCheck(tuple(satisfied), tuple(missing))


def missing_queries(check: RequirementCheck) -> list[str]:
    return [category.replace("_", " ") for category in check.missing]


def fill_missing(candidates, selected, check: RequirementCheck, intent: IntentAnalysis, profile: PackProfile):
    """Pick additional candidates that satisfy still-missing categories.

    Deterministic: it draws from the already-gathered candidate pool, so it can
    run without another network round-trip while still improving coverage.
    """
    if check.complete:
        return []
    selected_keys = {f"{m.source}:{m.id}" for m in selected}
    additions = []
    ranked = rank_by_quality(candidates, intent, profile)
    for category in check.missing:
        for score in ranked:
            key = f"{score.mod.source}:{score.mod.id}"
            if key in selected_keys:
                continue
            text = " ".join((score.mod.name, score.mod.slug, score.mod.summary, *score.mod.categories)).casefold()
            if _covers(text, category) and not is_blocked(score, profile):
                additions.append(score.mod)
                selected_keys.add(key)
                break
    return additions
