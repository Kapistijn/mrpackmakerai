"""Machine-readable intent analysis for modpack generation.

The AI planning stage used to rely on keyword matching alone, which meant a
request like "make a modpack that is as close to real life as possible"
produced generic popular/performance mods. This module turns a free-text
request into a structured, inspectable :class:`IntentAnalysis` (goal +
categories + avoid list) *before* any provider search happens, so the whole
pipeline can reason about what the player actually asked for.

The analysis is deterministic on its own; an AI provider may enrich it, but the
deterministic result is always a valid, machine-readable fallback.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Categories that describe a "realistic / immersive survival" experience. These
# are intentionally broad, human-readable tags that the scoring engine and the
# self-check both understand.
REALISM_CATEGORIES: tuple[str, ...] = (
    "weather", "seasons", "temperature", "food", "farming", "animals",
    "physics", "sound", "lighting", "survival", "world_generation", "immersion",
)
REALISM_AVOID: tuple[str, ...] = ("magic", "anime", "fantasy", "space", "sci-fi")

THEME_CATEGORIES: dict[str, tuple[str, ...]] = {
    "horror": ("horror", "atmosphere", "sound", "lighting", "mobs", "survival", "world_generation", "immersion"),
    "technology": ("technology", "automation", "storage", "energy", "progression", "utility"),
    "magic": ("magic", "spells", "rituals", "progression", "adventure"),
    "adventure": ("adventure", "exploration", "structures", "bosses", "world_generation", "quests"),
    "exploration": ("exploration", "world_generation", "structures", "biomes", "adventure"),
    "survival": ("survival", "food", "farming", "utility", "storage", "world_generation"),
}

_REALISM_PATTERNS = (
    r"real ?life", r"realistic", r"realism", r"lifelike",
    r"zo dicht mogelijk bij .*(?:echt|real)", r"echt(?:e)? leven", r"levensecht",
)

# category -> synonyms used to detect an explicit mention in the request text
_CATEGORY_SIGNALS: dict[str, tuple[str, ...]] = {
    "weather": ("weather", "storm", "rain", "weer"),
    "seasons": ("season", "seizoen", "seasons"),
    "temperature": ("temperature", "thirst", "cold", "heat", "temperatuur", "dorst"),
    "food": ("food", "hunger", "cooking", "eten", "honger"),
    "farming": ("farm", "farming", "agriculture", "landbouw", "boer"),
    "animals": ("animal", "wildlife", "creature", "dier"),
    "physics": ("physics", "gravity", "realistic movement", "natuurkunde", "zwaartekracht"),
    "sound": ("sound", "audio", "ambience", "geluid"),
    "lighting": ("lighting", "shadow", "light", "verlichting"),
    "survival": ("survival", "hardcore", "overleven"),
    "world_generation": ("worldgen", "world generation", "terrain", "biome", "wereldgeneratie"),
    "immersion": ("immers", "atmosphere", "immersie", "sfeer"),
    "technology": ("tech", "technology", "machine", "automation"),
    "magic": ("magic", "spell", "arcane", "magie"),
    "adventure": ("adventure", "dungeon", "quest", "avontuur"),
    "exploration": ("explore", "exploration", "verkennen"),
}


@dataclass(frozen=True)
class IntentAnalysis:
    """Structured, machine-readable interpretation of a generation request."""

    goal: str
    categories: tuple[str, ...] = field(default_factory=tuple)
    avoid: tuple[str, ...] = field(default_factory=tuple)
    realism_focus: bool = False

    def to_dict(self) -> dict:
        return {
            "goal": self.goal,
            "categories": list(self.categories),
            "avoid": list(self.avoid),
            "realism_focus": self.realism_focus,
        }


def _dedupe(values) -> tuple[str, ...]:
    return tuple(dict.fromkeys(v for v in values if v))


def analyze_intent(prompt: str, *, theme: str | None = None, forbidden: tuple[str, ...] = ()) -> IntentAnalysis:
    text = (prompt or "").casefold()
    realism = any(re.search(p, text) for p in _REALISM_PATTERNS)

    categories: list[str] = []
    for category, signals in _CATEGORY_SIGNALS.items():
        if any(signal in text for signal in signals):
            categories.append(category)

    avoid: list[str] = list(forbidden)
    if re.search(r"no magic|geen magie|zonder magie", text):
        avoid.append("magic")
    if re.search(r"no tech|geen technologie", text):
        avoid.append("technology")

    if realism:
        goal = "realism survival"
        categories = list(REALISM_CATEGORIES) + categories
        avoid = list(REALISM_AVOID) + avoid
    else:
        selected_theme = (theme or "").casefold()
        theme_cats = THEME_CATEGORIES.get(selected_theme, ())
        categories = list(theme_cats) + categories
        goal = f"{selected_theme or 'custom'} experience"

    # A category can never be both requested and avoided.
    avoid_set = set(avoid)
    categories = [c for c in categories if c not in avoid_set]
    return IntentAnalysis(goal=goal, categories=_dedupe(categories), avoid=_dedupe(avoid), realism_focus=realism)


def merge_ai_intent(base: IntentAnalysis, *, goal: str | None, categories, avoid, realism_focus: bool | None) -> IntentAnalysis:
    """Combine the deterministic analysis with an AI-provided enrichment.

    The AI can add categories and refine the goal, but it can never remove the
    deterministic guarantees (a realism request stays realism-focused).
    """
    merged_categories = _dedupe([*base.categories, *(categories or [])])
    merged_avoid = _dedupe([*base.avoid, *(avoid or [])])
    avoid_set = set(merged_avoid)
    merged_categories = tuple(c for c in merged_categories if c not in avoid_set)
    return IntentAnalysis(
        goal=(goal or base.goal).strip() or base.goal,
        categories=merged_categories,
        avoid=merged_avoid,
        realism_focus=base.realism_focus or bool(realism_focus),
    )
