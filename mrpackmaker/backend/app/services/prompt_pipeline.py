"""Prompt normalization used before AI modpack analysis.

The builder now has a stable, inspectable intermediate representation instead
of sending raw user prose directly to the model. This keeps user intent,
project settings, safety rules and selection priorities separate, which makes
provider swaps and future prompt-optimizer models much easier.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class PromptBrief:
    original: str
    normalized_request: str
    system_prompt: str
    constraints: tuple[str, ...]
    priorities: tuple[str, ...]

    def as_user_prompt(self) -> str:
        constraints = "\n".join(f"- {item}" for item in self.constraints)
        priorities = ", ".join(self.priorities)
        return f"Request:\n{self.normalized_request}\n\nConstraints:\n{constraints}\n\nPriorities: {priorities}"


def _extract_constraints(prompt: str) -> list[str]:
    constraints: list[str] = []
    text = prompt.strip()
    minimum = re.search(r"(?:at least|minimaal|minstens)\s+(\d+)\s+(?:mods?|modifications?)", text, re.I)
    maximum = re.search(r"(?:at most|maximaal|max)\s+(\d+)\s+(?:mods?|modifications?)", text, re.I)
    if minimum:
        constraints.append(f"select at least {minimum.group(1)} compatible mods")
    if maximum:
        constraints.append(f"never exceed {maximum.group(1)} total mods")
    if re.search(r"no duplicates|geen dubbele|zonder duplicaten", text, re.I):
        constraints.append("deduplicate by project identity, slug, name, file and hashes")
    if re.search(r"no magic|geen magie", text, re.I):
        constraints.append("avoid magic-themed content")
    if re.search(r"boss", text, re.I):
        constraints.append("prefer content with bosses when compatible")
    return constraints


def optimize_prompt(
    prompt: str,
    *,
    minecraft_version: str,
    loader: str,
    theme: str,
    difficulty: str,
    performance_preference: str,
) -> PromptBrief:
    """Expand sparse user intent into a deterministic generation brief.

    This first stage is intentionally deterministic and testable. A future
    provider-backed optimizer can replace only this function while keeping the
    downstream schema and safety constraints unchanged.
    """
    original = (prompt or "").strip()
    request = original or f"Create a {theme} Minecraft modpack."
    constraints = _extract_constraints(original)
    constraints.extend([
        f"Minecraft {minecraft_version} with {loader} only",
        "use stable compatible releases where available",
        "resolve required dependencies recursively",
        "compare Modrinth and CurseForge without duplicate projects",
        "reject incompatible, missing-file or unsafe-download entries",
        f"target {difficulty} gameplay and a {performance_preference} profile",
    ])
    priorities = [performance_preference, "compatibility", "stability", "user intent"]
    normalized = (
        f"Create a {theme} Minecraft modpack for {minecraft_version} ({loader}). "
        f"Interpret the user's intent as: {request}"
    )
    system = (
        "You are a senior Minecraft modpack architect. Select complete, stable, "
        "compatible projects, not merely popular search results. Never invent IDs. "
        "Use only candidates supplied by the catalog search, preserve the user's "
        "Minecraft version and loader, deduplicate projects across sources, resolve "
        "required dependencies, and explain trade-offs for every selected mod."
    )
    return PromptBrief(original, normalized, system, tuple(dict.fromkeys(constraints)), tuple(priorities))
