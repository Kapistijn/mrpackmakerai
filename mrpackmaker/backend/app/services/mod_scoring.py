"""Deterministic mod scoring that does not overfit to download counts."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from app.schemas.mod import ModEntry
from app.services.requirements import Requirements, theme_matches


@dataclass(frozen=True)
class ScoredMod:
    mod: ModEntry
    score: float
    reasons: tuple[str, ...]


def _download_score(downloads: int, minimum: int) -> float:
    if downloads < minimum:
        return 0.0
    return min(1.0, math.log10(max(downloads, 1)) / 8.0)


def score_mod(mod: ModEntry, requirements: Requirements, *, rng: random.Random | None = None) -> ScoredMod:
    rng = rng or random.Random(0)
    text = " ".join((mod.name, mod.slug, mod.summary, *mod.categories)).casefold()
    reasons: list[str] = []
    if not theme_matches(text, requirements):
        return ScoredMod(mod, -1.0, ("forbidden theme signal",))
    match = sum(1 for feature in requirements.required_features if feature.casefold() in text)
    match_score = min(1.0, match / max(1, len(requirements.required_features)))
    compatibility = 1.0 if mod.file_name and mod.download_url else 0.0
    quality = 1.0 if mod.hashes.sha1 or mod.hashes.sha512 else 0.5
    downloads = _download_score(mod.downloads, requirements.minimum_downloads)
    performance = 1.0 if any(term in text for term in ("optimization", "performance", "fps")) else 0.5
    novelty = 1.0 - downloads
    diversity_jitter = rng.random() * 0.03
    score = 0.40 * match_score + 0.20 * compatibility + 0.15 * quality + 0.10 * downloads + 0.10 * performance + 0.05 * novelty + diversity_jitter
    if match: reasons.append(f"matches {match} requested feature(s)")
    if compatibility: reasons.append("has a compatible downloadable file")
    if novelty > 0.5: reasons.append("adds catalog diversity")
    return ScoredMod(mod, score, tuple(reasons))


def rank_mods(mods: list[ModEntry], requirements: Requirements, *, seed: int) -> list[ScoredMod]:
    rng = random.Random(seed)
    ranked = [score_mod(mod, requirements, rng=rng) for mod in mods]
    return sorted(ranked, key=lambda item: item.score, reverse=True)


def _select_diverse_items(items: list[ScoredMod] | list[ModEntry], count: int) -> list[ScoredMod] | list[ModEntry]:
    if count <= 0:
        return []
    selected = []
    used: set[str] = set()
    categories: set[str] = set()
    for item in items:
        mod = item.mod if isinstance(item, ScoredMod) else item
        key = f"{mod.source}:{mod.id}"
        if key in used:
            continue
        item_categories = {category.casefold() for category in mod.categories}
        if item_categories - categories:
            selected.append(item)
            used.add(key)
            categories.update(item_categories)
        if len(selected) >= count:
            return selected
    for item in items:
        mod = item.mod if isinstance(item, ScoredMod) else item
        key = f"{mod.source}:{mod.id}"
        if key not in used:
            selected.append(item)
            used.add(key)
        if len(selected) >= count:
            break
    return selected


def select_diverse(ranked: list[ScoredMod], count: int) -> list[ScoredMod]:
    """Select ranked scored mods while covering distinct categories first."""
    return _select_diverse_items(ranked, count)  # type: ignore[return-value]


def select_diverse_candidates(candidates: list[ModEntry], count: int) -> list[ModEntry]:
    """Select already-ranked ModEntry candidates from the live generation path."""
    return _select_diverse_items(candidates, count)  # type: ignore[return-value]
