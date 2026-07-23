"""Multi-factor mod quality scoring for intent-driven selection.

This replaces pure keyword/download ranking with an explainable score built
from several independent signals. Each mod is scored against the analyzed
intent and the pack profile, and pure-performance mods are only selected when
the profile actually justifies them.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from app.schemas.mod import ModEntry
from app.services.intent_analysis import IntentAnalysis
from app.services.pack_profile import PackProfile

# Signals used to recognise the intent of a mod from its metadata.
_REALISM_TERMS = (
    "realistic", "realism", "immers", "weather", "season", "temperature",
    "thirst", "hunger", "farm", "animal", "physics", "gravity", "ambient",
    "ambience", "sound", "light", "shadow", "survival", "terrain", "biome", "nature",
)
_PERFORMANCE_TERMS = (
    "sodium", "lithium", "modernfix", "ferritecore", "embeddium", "rubidium",
    "performance", "optimization", "optimisation", "fps", "memory", "lag",
)
_HEAVY_TERMS = (
    "shader", "iris", "oculus", "high quality", "hd", "realistic", "volumetric",
    "ray", "worldgen", "world generation", "structures", "dungeon", "dimension",
)

_CATEGORY_SYNONYMS: dict[str, tuple[str, ...]] = {
    "weather": ("weather", "storm", "rain"),
    "seasons": ("season",),
    "temperature": ("temperature", "thirst", "cold", "heat"),
    "food": ("food", "hunger", "cook", "diet"),
    "farming": ("farm", "crop", "agriculture"),
    "animals": ("animal", "wildlife", "creature", "mob"),
    "physics": ("physics", "gravity", "ragdoll"),
    "sound": ("sound", "audio", "ambience", "ambient"),
    "lighting": ("light", "shadow", "lamp"),
    "survival": ("survival", "hardcore"),
    "world_generation": ("worldgen", "world generation", "terrain", "biome", "structure"),
    "immersion": ("immers", "atmosphere", "ambient"),
    "technology": ("tech", "machine", "automation", "energy"),
    "magic": ("magic", "spell", "arcane"),
    "adventure": ("adventure", "dungeon", "quest", "boss"),
    "exploration": ("explore", "exploration", "biome"),
}


@dataclass(frozen=True)
class ModQualityScore:
    mod: ModEntry
    intent_match: float
    realism_score: float
    popularity: float
    maintenance_score: float
    compatibility_score: float
    performance_cost: float
    dependency_quality: float
    is_performance_mod: bool
    reasons: tuple[str, ...]

    @property
    def total(self) -> float:
        # performance_cost is a penalty, every other factor is a benefit.
        return round(
            0.34 * self.intent_match
            + 0.16 * self.realism_score
            + 0.12 * self.popularity
            + 0.10 * self.maintenance_score
            + 0.14 * self.compatibility_score
            + 0.08 * self.dependency_quality
            - 0.16 * self.performance_cost,
            5,
        )


def _text(mod: ModEntry) -> str:
    return " ".join((mod.name, mod.slug, mod.summary, *mod.categories)).casefold()


def _popularity(downloads: int) -> float:
    return min(1.0, math.log10(max(downloads, 1)) / 8.0)


def _category_match(text: str, intent: IntentAnalysis) -> float:
    if not intent.categories:
        return 0.5
    hits = 0
    for category in intent.categories:
        synonyms = _CATEGORY_SYNONYMS.get(category, (category.replace("_", " "),))
        if any(s in text for s in synonyms):
            hits += 1
    return min(1.0, hits / max(1, len(intent.categories)) * 2.0)


def score_mod_quality(mod: ModEntry, intent: IntentAnalysis, profile: PackProfile, *, minimum_downloads: int = 0) -> ModQualityScore:
    text = _text(mod)
    reasons: list[str] = []

    intent_match = _category_match(text, intent)
    realism = sum(term in text for term in _REALISM_TERMS)
    realism_score = min(1.0, realism / 4.0)
    popularity = _popularity(mod.downloads) if mod.downloads >= minimum_downloads else 0.0
    # No registry timestamp is available here; a resolvable, hashed,
    # downloadable file is our proxy for an actively maintained release.
    maintenance_score = 1.0 if (mod.file_name and mod.download_url) else 0.3
    compatibility_score = 1.0 if (mod.file_name and mod.download_url and (mod.hashes.sha1 or mod.hashes.sha512)) else 0.0
    dependency_quality = 1.0 if not mod.dependencies else max(0.4, 1.0 - 0.1 * len(mod.dependencies))

    is_perf = any(term in text for term in _PERFORMANCE_TERMS)
    heavy = any(term in text for term in _HEAVY_TERMS)
    performance_cost = 0.0
    if heavy:
        performance_cost = 0.8
    if is_perf:
        performance_cost = 0.0  # performance mods reduce, not add, cost

    if intent_match >= 0.5:
        reasons.append(f"matches intent categories ({intent.goal})")
    if intent.realism_focus and realism_score > 0.3:
        reasons.append("adds realism/immersion signals")
    if is_perf:
        reasons.append("performance/optimization mod")
    if heavy:
        reasons.append("heavy visual/worldgen mod")

    return ModQualityScore(
        mod=mod, intent_match=intent_match, realism_score=realism_score,
        popularity=popularity, maintenance_score=maintenance_score,
        compatibility_score=compatibility_score, performance_cost=performance_cost,
        dependency_quality=dependency_quality, is_performance_mod=is_perf,
        reasons=tuple(reasons),
    )


def rank_by_quality(mods, intent: IntentAnalysis, profile: PackProfile, *, minimum_downloads: int = 0) -> list[ModQualityScore]:
    scored = [score_mod_quality(m, intent, profile, minimum_downloads=minimum_downloads) for m in mods]
    return sorted(scored, key=lambda s: s.total, reverse=True)


def is_blocked(score: ModQualityScore, profile: PackProfile) -> bool:
    # Performance mods only when justified.
    if score.is_performance_mod and not profile.needs_performance_mods:
        return True
    # Heavy mods must clear the performance floor set by RAM/FPS.
    if score.performance_cost >= 0.8 and profile.performance_floor >= 0.7:
        return True
    # Heavy worldgen not allowed on a small memory budget.
    if not profile.allow_heavy_worldgen and score.performance_cost >= 0.8 and any(
        t in _text(score.mod) for t in ("worldgen", "world generation", "terrain", "dimension")
    ):
        return True
    return False


def select_quality(ranked: list[ModQualityScore], count: int, profile: PackProfile) -> list[ModEntry]:
    if count <= 0:
        return []
    selected: list[ModEntry] = []
    used: set[str] = set()
    categories: set[str] = set()
    # First pass: diverse, non-blocked, category-expanding.
    for score in ranked:
        if is_blocked(score, profile):
            continue
        key = f"{score.mod.source}:{score.mod.id}"
        if key in used:
            continue
        cats = {c.casefold() for c in score.mod.categories}
        if cats - categories or not selected:
            selected.append(score.mod)
            used.add(key)
            categories.update(cats)
        if len(selected) >= count:
            return selected
    # Second pass: fill remaining slots with any non-blocked mod.
    for score in ranked:
        if is_blocked(score, profile):
            continue
        key = f"{score.mod.source}:{score.mod.id}"
        if key not in used:
            selected.append(score.mod)
            used.add(key)
        if len(selected) >= count:
            break
    return selected
