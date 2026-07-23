"""Deterministic, inspectable prompt pipeline for AI generation."""

from __future__ import annotations

import re
from dataclasses import dataclass


DUPLICATE_CONSTRAINT = "deduplicate by project identity, slug, name, file and hashes"
CONTENT_INTENT_CONSTRAINTS = {
    "bosses": "prefer content with bosses when compatible",
    "monsters": "prefer new hostile mobs when compatible",
    "zombies": "prefer zombie and undead content when compatible",
    "automation": "prefer automation and progression content when compatible",
    "questing": "prefer structured quests and progression when compatible",
    "immersive": "prefer immersion and atmosphere over raw popularity",
    "psychological": "prefer psychological horror and atmosphere when compatible",
}


@dataclass(frozen=True)
class IntentProfile:
    themes: tuple[str, ...]
    gameplay_styles: tuple[str, ...]
    explicit_preferences: tuple[str, ...]
    forbidden_features: tuple[str, ...]
    minimum_mods: int | None = None
    maximum_mods: int | None = None
    multiplayer: bool | None = None
    server_support: bool | None = None
    performance_profile: str | None = None


@dataclass(frozen=True)
class PromptBrief:
    original: str
    normalized_request: str
    system_prompt: str
    constraints: tuple[str, ...]
    priorities: tuple[str, ...]
    intent: IntentProfile

    def as_user_prompt(self) -> str:
        constraints = "\n".join(f"- {item}" for item in self.constraints)
        priorities = ", ".join(self.priorities)
        return f"Request:\n{self.normalized_request}\n\nConstraints:\n{constraints}\n\nPriorities: {priorities}"


_THEME_TERMS = ("horror", "technology", "magic", "adventure", "survival", "exploration", "rpg", "medieval", "sci-fi", "farming", "building", "pvp", "apocalypse", "skyblock", "create", "cobblemon")
_STYLE_TERMS = ("hardcore", "immersive", "psychological", "bosses", "monsters", "zombies", "automation", "questing", "multiplayer", "vanilla+")


def _contains(text: str, term: str) -> bool:
    return re.search(rf"(?<![a-z]){re.escape(term)}(?![a-z])", text, re.I) is not None


def extract_intent(prompt: str) -> IntentProfile:
    text = (prompt or "").strip().casefold()
    themes = tuple(term for term in _THEME_TERMS if _contains(text, term))
    styles = tuple(term for term in _STYLE_TERMS if _contains(text, term))
    forbidden: list[str] = []
    if re.search(r"no magic|geen magie", text): forbidden.append("magic")
    if re.search(r"no technology|geen technologie", text): forbidden.append("technology")
    if re.search(r"no storage|geen storage", text): forbidden.append("storage")
    minimum = _number_near(text, ("at least", "minimaal", "minstens"))
    maximum = _number_near(text, ("at most", "maximaal", "maximum"))
    multiplayer = True if re.search(r"multiplayer|server|samen spelen", text) else None
    performance = "low-end" if re.search(r"low.?end|zwakke pc", text) else "high-end" if re.search(r"high.?end|extreme", text) else None
    return IntentProfile(themes, styles, tuple(styles), tuple(forbidden), minimum, maximum, multiplayer, multiplayer, performance)


def _number_near(text: str, markers: tuple[str, ...]) -> int | None:
    for marker in markers:
        match = re.search(rf"{re.escape(marker)}\s+(\d+)", text, re.I)
        if match:
            return int(match.group(1))
    return None


def validate_intent(intent: IntentProfile) -> list[str]:
    errors: list[str] = []
    if intent.minimum_mods is not None and intent.maximum_mods is not None and intent.minimum_mods > intent.maximum_mods:
        errors.append("minimum mod count cannot exceed maximum mod count")
    if intent.maximum_mods is not None and intent.maximum_mods > 250:
        errors.append("maximum mod count exceeds the safe export limit of 250")
    if len(intent.themes) > 3:
        errors.append("too many competing themes; choose at most three")
    return errors


def optimize_prompt(prompt: str, *, minecraft_version: str, loader: str, theme: str, difficulty: str, performance_preference: str) -> PromptBrief:
    original = (prompt or "").strip()
    request = original or f"Create a {theme} Minecraft modpack."
    intent = extract_intent(original)
    errors = validate_intent(intent)
    constraints: list[str] = [
        f"Minecraft {minecraft_version} with {loader} only",
        "use stable compatible releases where available",
        "resolve required dependencies transitively without cycles",
        "compare Modrinth and CurseForge without duplicate projects",
        DUPLICATE_CONSTRAINT,
        "reject incompatible, missing-file or unsafe-download entries",
        f"target {difficulty} gameplay and a {performance_preference} profile",
    ]
    if intent.minimum_mods is not None: constraints.append(f"select at least {intent.minimum_mods} compatible mods")
    if intent.maximum_mods is not None: constraints.append(f"never exceed {intent.maximum_mods} total mods")
    if intent.forbidden_features: constraints.append(f"avoid: {', '.join(intent.forbidden_features)}")
    if intent.multiplayer: constraints.append("prefer multiplayer and server-compatible content")
    # Derive from both the parsed profile and the raw prompt. The second path
    # makes the contract robust to a future parser that normalizes or filters a
    # term while the user's explicit content requirement is still present.
    raw_content_signals = {term for term in CONTENT_INTENT_CONSTRAINTS if _contains(original.casefold(), term)}
    content_signals = set(intent.gameplay_styles) | raw_content_signals
    constraints.extend(CONTENT_INTENT_CONSTRAINTS[item] for item in CONTENT_INTENT_CONSTRAINTS if item in content_signals)
    constraints.extend(f"intent: {item}" for item in intent.themes + intent.gameplay_styles)
    constraints.extend(f"resolve ambiguity: {error}" for error in errors)
    priorities = tuple(dict.fromkeys((performance_preference, "compatibility", "stability", "user intent")))
    normalized = f"Create a {theme} Minecraft modpack for Minecraft {minecraft_version} ({loader}). Interpret the user's intent as: {request}"
    system = ("You are a senior Minecraft modpack architect. The original user text is unavailable to you. "
              "Select complete stable compatible projects, never invent IDs, use only supplied candidates, "
              "preserve version and loader, deduplicate sources, resolve required dependencies, and explain trade-offs.")
    return PromptBrief(original, normalized, system, tuple(dict.fromkeys(constraints)), priorities, intent)
