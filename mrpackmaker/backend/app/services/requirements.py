"""Requirement parsing, structured targets, and deterministic quota planning."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Requirements:
    themes: tuple[str, ...] = ()
    required_features: tuple[str, ...] = ()
    forbidden_features: tuple[str, ...] = ()
    minimum_mods: int | None = None
    maximum_mods: int | None = None
    minimum_downloads: int = 0
    multiplayer: bool = False
    warnings: tuple[str, ...] = ()

    @property
    def target_count(self) -> int:
        return self.maximum_mods or self.minimum_mods or 40


def category_quotas(requirements: Requirements, target_count: int | None = None) -> dict[str, int]:
    """Return stable, non-overlapping category quotas for generation."""
    target = target_count or requirements.target_count
    target = max(requirements.minimum_mods or 0, target)
    if requirements.maximum_mods is not None:
        target = min(target, requirements.maximum_mods)
    categories: list[tuple[str, float]] = []
    feature_text = " ".join((*requirements.themes, *requirements.required_features)).casefold()
    if requirements.themes:
        categories.append((requirements.themes[0], 0.15))
    if any(term in feature_text for term in ("qol", "inventory", "utility", "storage")):
        categories.append(("qol", 0.20))
    if any(term in feature_text for term in ("performance", "fps", "optimization")):
        categories.append(("performance", 0.10))
    if any(term in feature_text for term in ("worldgen", "exploration", "adventure", "structures")):
        categories.append(("world", 0.15))
    if any(term in feature_text for term in ("boss", "combat", "mobs")):
        categories.append(("combat", 0.15))
    if not categories:
        categories.append(("requested", 0.50))
    quotas = {name: max(1, int(target * share)) for name, share in categories}
    assigned = sum(quotas.values())
    quotas["remaining"] = max(0, target - assigned)
    return quotas


THEME_RULES: dict[str, dict[str, tuple[str, ...]]] = {
    "horror": {"include": ("horror", "mobs", "worldgen", "sound", "atmosphere", "lighting", "survival"), "exclude": ("cobblemon", "pokemon", "technology", "magic", "farming")},
    "technology": {"include": ("technology", "automation", "storage", "utility"), "exclude": ("magic",)},
    "magic": {"include": ("magic", "adventure", "mobs"), "exclude": ("technology",)},
    "adventure": {"include": ("adventure", "worldgen", "mobs", "structures"), "exclude": ()},
}


def _number(text: str, markers: tuple[str, ...]) -> int | None:
    for marker in markers:
        match = re.search(rf"(?:{marker})\s*(\d+)", text, re.I)
        if match: return int(match.group(1))
    return None


def parse_requirements(prompt: str, *, theme: str | None = None, minimum_mods: int | None = None, maximum_mods: int | None = None, minimum_downloads: int | None = None) -> Requirements:
    text = (prompt or "").casefold()
    detected_themes = [name for name in THEME_RULES if re.search(rf"\b{re.escape(name)}\b", text)]
    if theme and theme in THEME_RULES and theme not in detected_themes: detected_themes.insert(0, theme)
    active = THEME_RULES.get(detected_themes[0], {}) if detected_themes else {}
    required = list(active.get("include", ()))
    forbidden = list(active.get("exclude", ()))
    if re.search(r"qol|quality of life", text): required.extend(("qol", "inventory", "ui", "sound"))
    if re.search(r"boss|bazen", text): required.append("bosses")
    if re.search(r"monster|mob|zombie", text): required.append("mobs")
    if re.search(r"no magic|geen magie", text): forbidden.append("magic")
    if re.search(r"no technology|geen technologie", text): forbidden.append("technology")
    parsed_min = _number(text, (r"at least", r"minimum", r"minimaal", r"minstens"))
    parsed_max = _number(text, (r"at most", r"maximum", r"maximaal"))
    parsed_downloads = _number(text, (r"minimum\s+downloads?", r"min(?:imum)?\s+downloads?", r"downloads?\s*[:=]"))
    effective_min = minimum_mods if minimum_mods is not None else parsed_min
    effective_max = maximum_mods if maximum_mods is not None else parsed_max
    effective_downloads = minimum_downloads if minimum_downloads else (parsed_downloads or 0)
    warnings = ("minimum_mods exceeds maximum_mods",) if effective_min and effective_max and effective_min > effective_max else ()
    return Requirements(themes=tuple(dict.fromkeys(detected_themes)), required_features=tuple(dict.fromkeys(required)), forbidden_features=tuple(dict.fromkeys(forbidden)), minimum_mods=effective_min, maximum_mods=effective_max, minimum_downloads=max(0, effective_downloads), multiplayer=bool(re.search(r"multiplayer|server|samen spelen", text)), warnings=warnings)


def theme_matches(mod_text: str, requirements: Requirements) -> bool:
    text = (mod_text or "").casefold()
    return not any(re.search(rf"\b{re.escape(term)}\b", text) for term in requirements.forbidden_features)
