"""Explainable, deterministic pack intelligence used by the AI and UI."""
from __future__ import annotations
import re
from dataclasses import dataclass
from itertools import combinations
from typing import Any
from app.schemas.mod import ModEntry

_REALISM = {"season", "weather", "temperature", "thirst", "hunger", "terrain", "ambient", "realistic", "survival"}
_IMMERSION = {"ambient", "sound", "biome", "weather", "season", "lighting", "atmosphere", "realistic"}
_PERFORMANCE = {"sodium", "lithium", "modernfix", "ferritecore", "embeddium", "optimization", "performance", "fps"}
_WORLDGEN = {"worldgen", "world generation", "terrain", "biome", "dimension", "structures"}
_ENTITIES = {"mob", "animal", "creature", "entity", "boss"}
_PARTICLES = {"particle", "visual", "magic", "spell", "shader"}


def _text(mod: ModEntry) -> str:
    return " ".join((mod.name, mod.slug, mod.summary, *mod.categories)).casefold()

def _hits(text: str, terms: set[str]) -> int:
    return sum(term in text for term in terms)

def _pct(value: float) -> int:
    return max(0, min(100, round(value * 100)))

def _bar(value: int, width: int = 10) -> str:
    filled = round(value / 100 * width)
    return "█" * filled + "░" * (width - filled)

def quality_report(mods: list[ModEntry]) -> dict[str, Any]:
    if not mods:
        return {"scores": {k: 0 for k in ("realism", "immersion", "performance", "compatibility", "content_balance")}, "explanation": "No mods available to score."}
    texts = [_text(mod) for mod in mods]
    realism = sum(min(1, _hits(text, _REALISM) / 4) for text in texts) / len(texts)
    immersion = sum(min(1, _hits(text, _IMMERSION) / 3) for text in texts) / len(texts)
    performance = sum(1 if _hits(text, _PERFORMANCE) else (0.45 if _hits(text, _WORLDGEN | _PARTICLES) else 0.8) for text in texts) / len(texts)
    compatibility = sum(bool(mod.file_name and mod.download_url and (mod.hashes.sha1 or mod.hashes.sha512)) for mod in mods) / len(mods)
    categories = [category.casefold() for mod in mods for category in mod.categories]
    balance = min(1, len(set(categories)) / max(1, min(10, len(mods) / 3)))
    scores = {"realism": _pct(realism), "immersion": _pct(immersion), "performance": _pct(performance), "compatibility": _pct(compatibility), "content_balance": _pct(balance)}
    explanation = "The pack could use more food, farming, or survival variety." if scores["content_balance"] < 60 else "Content categories are reasonably balanced."
    return {"scores": scores, "bars": {key: _bar(value) for key, value in scores.items()}, "explanation": explanation}

def synergy_report(mods: list[ModEntry]) -> dict[str, Any]:
    synergies: list[dict[str, Any]] = []; conflicts: list[dict[str, Any]] = []
    for left, right in combinations(mods, 2):
        a, b = _text(left), _text(right)
        shared = [term for term in sorted(_REALISM | _WORLDGEN | _PERFORMANCE) if term in a and term in b]
        if shared:
            synergies.append({"mods": [left.name, right.name], "score": min(95, 55 + len(shared) * 12), "signals": shared, "explanation": f"{left.name} and {right.name} reinforce {', '.join(shared[:3])}."})
        if _hits(a, _WORLDGEN) and _hits(b, _WORLDGEN):
            conflicts.append({"mods": [left.name, right.name], "risk": "high", "type": "world_generation_overlap", "explanation": "Both mods modify terrain, biomes, dimensions, or structures. Check configs before export."})
    return {"synergies": sorted(synergies, key=lambda item: item["score"], reverse=True)[:25], "conflicts": conflicts[:25]}

def performance_estimate(mods: list[ModEntry], *, ram_gb: int | None = None, fps_target: int | None = None, shader_support: str | None = None) -> dict[str, Any]:
    texts = [_text(mod) for mod in mods]; worldgen = sum(bool(_hits(text, _WORLDGEN)) for text in texts); entities = sum(bool(_hits(text, _ENTITIES)) for text in texts); particles = sum(bool(_hits(text, _PARTICLES)) for text in texts); shaders = 1 if shader_support in {"enabled", "required", "recommended"} else 0
    estimated_ram = max(4, round(4 + len(mods) * 0.018 + worldgen * 0.12 + entities * 0.04 + shaders * 2))
    vram = max(2, round(2 + shaders * 2 + particles * 0.015))
    cores = max(4, min(16, round(4 + worldgen / 30 + entities / 50)))
    fps_low = max(30, round(180 - len(mods) * 0.12 - worldgen * 1.4 - entities * 0.25 - particles * 0.2 - shaders * 35))
    fps_high = max(fps_low + 10, fps_low + 50 - shaders * 10)
    return {"ram_gb": estimated_ram, "vram_gb": vram, "cpu_cores": cores, "gpu_recommendation": "RTX 3060 or better" if vram >= 6 else "GTX 1660 / RX 5600 XT or better", "expected_fps": {"low": fps_low, "high": fps_high}, "inputs": {"mods": len(mods), "worldgen": worldgen, "entities": entities, "particles": particles, "shaders": bool(shaders), "ram_preference": ram_gb, "fps_target": fps_target}}

def reputation_report(mod: ModEntry) -> dict[str, Any]:
    text = _text(mod); downloads = min(5, max(1, round((__import__('math').log10(max(mod.downloads, 1)) / 2))))
    compatibility = 5 if mod.file_name and mod.download_url and (mod.hashes.sha1 or mod.hashes.sha512) else 2
    maintenance = 5 if mod.file_name and mod.download_url else 2
    performance = 3 if _hits(text, _WORLDGEN | _PARTICLES) else 4
    return {"mod": mod.name, "stability": downloads, "maintenance": maintenance, "compatibility": compatibility, "performance": performance, "evidence": ["downloads", "downloadable release", "hash availability", "metadata complexity"]}

def variant_plan(base_name: str, mods: list[ModEntry]) -> list[dict[str, Any]]:
    return [{"name": f"{base_name} Lite", "tier": "lite", "mods": min(50, len(mods)), "ram_gb": 8, "shaders": False}, {"name": f"{base_name} Balanced", "tier": "balanced", "mods": min(150, len(mods)), "ram_gb": 12, "shaders": False}, {"name": f"{base_name} Ultimate", "tier": "ultimate", "mods": min(350, len(mods)), "ram_gb": 24, "shaders": True}]

def natural_language_plan(prompt: str, mods: list[ModEntry]) -> dict[str, Any]:
    text = prompt.casefold(); additions: list[str] = []; removals: list[str] = []; rationale = ""
    if any(word in text for word in ("enger", "horror", "scary")):
        additions = ["horror ambience", "harder mobs", "darkness mechanics"]; rationale = "Adds atmosphere and threat without removing existing content."
    elif any(word in text for word in ("echte wereld", "realistic", "realistisch")):
        additions = ["seasons", "temperature", "thirst", "realistic terrain"]; rationale = "Adds survival systems and terrain realism."
    else:
        additions = [prompt.strip()[:120]] if prompt.strip() else []; rationale = "The request needs a catalog search pass before changes are applied."
    return {"prompt": prompt, "add_queries": additions, "remove_names": removals, "rationale": rationale, "approval_required": True, "current_mod_count": len(mods)}
