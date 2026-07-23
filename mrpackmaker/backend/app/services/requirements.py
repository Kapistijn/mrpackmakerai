"""Requirement parsing and hard theme policy for generation.

This module turns user prose into enforceable constraints before catalog search.
It deliberately has no network or model dependency, so the contract is fast,
deterministic, and testable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


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


THEME_RULES: dict[str, dict[str, tuple[str, ...]]] = {
    "horror": {
        "include": ("horror", "mobs", "worldgen", "sound", "atmosphere", "lighting", "survival"),
        "exclude": ("cobblemon", "pokemon", "technology", "magic", "farming"),
    },
    "technology": {"include": ("technology", "automation", "storage", "utility"), "exclude": ("magic",)},
    "magic": {"include": ("magic", "adventure", "mobs"), "exclude": ("technology",)},
    "adventure": {"include": ("adventure", "worldgen", "mobs", "structures"), "exclude": ()},
}


def _number(text: str, markers: tuple[str, ...]) -> int | None:
    for marker in markers:
        match = re.search(rf"(?:{marker})\s*(\d+)", text, re.I)
        if match:
            return int(match.group(1))
    return None


def parse_requirements(prompt: str, *, theme: str | None = None) -> Requirements:
    text = (prompt or "").casefold()
    detected_themes = [name for name in THEME_RULES if re.search(rf"\b{re.escape(name)}\b", text)]
    if theme and theme in THEME_RULES and theme not in detected_themes:
        detected_themes.insert(0, theme)
    active = THEME_RULES.get(detected_themes[0], {}) if detected_themes else {}
    required = list(active.get("include", ()))
    forbidden = list(active.get("exclude", ()))
    if re.search(r"qol|quality of life", text):
        required.extend(("qol", "inventory", "ui", "sound"))
    if re.search(r"boss|bazen", text):
        required.append("bosses")
    if re.search(r"monster|mob|zombie", text):
        required.append("mobs")
    if re.search(r"no magic|geen magie", text):
        forbidden.append("magic")
    if re.search(r"no technology|geen technologie", text):
        forbidden.append("technology")
    minimum = _number(text, (r"at least", r"minimum", r"minimaal", r"minstens"))
    maximum = _number(text, (r"at most", r"maximum", r"maximaal"))
    if minimum and maximum and minimum > maximum:
        warnings = ("minimum_mods exceeds maximum_mods",)
    else:
        warnings = ()
    if re.search(r"multiplayer|server|samen spelen", text):
        multiplayer = True
    else:
        multiplayer = False
    downloads = _number(text, (r"downloads?\s*[:=]?", r"min(?:imum)?\s*downloads?")) or 0
    return Requirements(
        themes=tuple(dict.fromkeys(detected_themes)),
        required_features=tuple(dict.fromkeys(required)),
        forbidden_features=tuple(dict.fromkeys(forbidden)),
        minimum_mods=minimum,
        maximum_mods=maximum,
        minimum_downloads=downloads,
        multiplayer=multiplayer,
        warnings=warnings,
    )


def theme_matches(mod_text: str, requirements: Requirements) -> bool:
    text = (mod_text or "").casefold()
    return not any(re.search(rf"\b{re.escape(term)}\b", text) for term in requirements.forbidden_features)
