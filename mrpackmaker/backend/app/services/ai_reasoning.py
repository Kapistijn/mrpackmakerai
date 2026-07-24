"""Deterministic reasoning primitives for large, explainable modpacks.

The AI provider can enrich the plan, but catalog facts and safety decisions stay
local and reproducible. This module turns a flat candidate list into evidence,
role coverage, alternatives, performance warnings, and actionable feedback.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable

from app.schemas.mod import ModEntry
from app.services.pack_intelligence import (
    performance_estimate,
    quality_report,
    synergy_report,
)


MAX_ALTERNATIVES = 3

_ROLE_ALIASES = {
    "worldgen": "world_generation",
    "world generation": "world_generation",
    "world-generation": "world_generation",
    "world_generation": "world_generation",
    "biomes": "world_generation",
    "mobs": "combat",
    "bosses": "combat",
    "monsters": "combat",
    "spells": "magic",
    "tech": "technology",
    "machines": "automation",
    "farming": "farming",
}

_ROLE_SIGNALS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("create", "automation", "factory", "technology", "engineering", "machine", "energy"), "automation"),
    (("technology", "tech", "machine", "energy"), "technology"),
    (("storage", "inventory", "backpack", "chest"), "storage"),
    (("transport", "rail", "aircraft", "vehicle", "travel"), "transport"),
    (("food", "farm", "farming", "agriculture", "crop", "cooking"), "farming"),
    (("worldgen", "world generation", "terrain", "biome", "dimension", "structures"), "world_generation"),
    (("quest", "progression", "advancement", "skill", "level"), "progression"),
    (("magic", "spell", "arcane", "ritual"), "magic"),
    (("boss", "combat", "mob", "monster", "enemy"), "combat"),
    (("weather", "season", "temperature", "survival", "hunger", "thirst"), "survival"),
    (("sound", "ambient", "atmosphere", "immersion", "lighting"), "immersion"),
)


@dataclass(frozen=True)
class ModMemory:
    """The explainable memory record attached to one selected mod."""

    name: str
    source: str
    categories: tuple[str, ...]
    roles: tuple[str, ...]
    dependencies: tuple[str, ...]
    downloads: int
    performance_impact: str
    compatibility: str
    reason: str
    confidence: int
    alternatives: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()
    intent_match: int = 0
    risk_flags: tuple[str, ...] = ()


def normalize_role(value: str) -> str:
    """Normalize AI and catalog vocabulary to one coverage vocabulary."""
    cleaned = " ".join((value or "").casefold().replace("-", " ").split())
    return _ROLE_ALIASES.get(cleaned, cleaned.replace(" ", "_"))


def _text(mod: ModEntry) -> str:
    return " ".join(
        (mod.name or "", mod.slug or "", mod.summary or "", *mod.categories)
    ).casefold()


def roles_for(mod: ModEntry) -> tuple[str, ...]:
    """Infer stable gameplay roles from catalog metadata."""
    text = _text(mod)
    roles: list[str] = []
    for signals, role in _ROLE_SIGNALS:
        if any(signal in text for signal in signals) and role not in roles:
            roles.append(role)
    return tuple(roles or ("general",))


def _mod_key(mod: ModEntry) -> str:
    source = str(mod.source).casefold()
    return f"{source}:{mod.id or mod.slug or mod.name}".casefold()


def _evidence_for(mod: ModEntry) -> tuple[str, ...]:
    evidence: list[str] = []
    if mod.name and mod.slug:
        evidence.append("catalog identity")
    if mod.categories:
        evidence.append(f"{len(mod.categories)} catalog categories")
    if mod.downloads > 0:
        evidence.append(f"{mod.downloads:,} recorded downloads")
    if mod.file_name and mod.download_url:
        evidence.append("compatible downloadable file")
    if mod.hashes.sha1 or mod.hashes.sha512:
        evidence.append("verified file hash")
    if mod.dependencies:
        evidence.append(f"{len(mod.dependencies)} dependency records")
    return tuple(evidence)


def _risk_flags_for(mod: ModEntry) -> tuple[str, ...]:
    text = _text(mod)
    risks: list[str] = []
    if any(term in text for term in ("worldgen", "world generation", "dimension", "terrain")):
        risks.append("world-generation overlap")
    if any(term in text for term in ("shader", "particle", "ray tracing", "volumetric")):
        risks.append("visual performance cost")
    if len(mod.dependencies) >= 5:
        risks.append("large dependency surface")
    if not mod.file_name or not mod.download_url:
        risks.append("downloadable file needs validation")
    return tuple(risks)


def _performance_impact(mod: ModEntry) -> str:
    text = _text(mod)
    if any(term in text for term in ("worldgen", "world generation", "dimension", "shader", "particle")):
        return "high"
    if any(term in text for term in ("mob", "monster", "entity", "structure", "dungeon")):
        return "medium"
    return "low"


def _compatibility(mod: ModEntry) -> str:
    if mod.file_name and mod.download_url and (mod.hashes.sha1 or mod.hashes.sha512):
        return "excellent"
    if mod.file_name and mod.download_url:
        return "good, hash pending"
    return "needs validation"


def build_mod_memory(
    mod: ModEntry,
    reason: str = "",
    confidence: int = 70,
    alternatives: Iterable[str] = (),
    requested_roles: Iterable[str] = (),
) -> dict[str, Any]:
    """Build a JSON-safe, evidence-backed memory record for a mod."""
    requested = {normalize_role(role) for role in requested_roles if role}
    roles = roles_for(mod)
    match = len(set(roles).intersection(requested))
    evidence = _evidence_for(mod)
    if not reason:
        reason = (
            f"Matches requested roles: {', '.join(roles)}"
            if match
            else "Selected as a compatible supporting mod"
        )
    evidence_bonus = min(15, len(evidence) * 2)
    bounded_confidence = max(0, min(99, int(confidence) + evidence_bonus))
    return asdict(
        ModMemory(
            name=mod.name,
            source=str(mod.source),
            categories=tuple(mod.categories),
            roles=roles,
            dependencies=tuple(dep.project_id for dep in mod.dependencies),
            downloads=mod.downloads,
            performance_impact=_performance_impact(mod),
            compatibility=_compatibility(mod),
            reason=reason,
            confidence=bounded_confidence,
            alternatives=tuple(dict.fromkeys(name for name in alternatives if name))[:MAX_ALTERNATIVES],
            evidence=evidence,
            intent_match=min(100, match * 25),
            risk_flags=_risk_flags_for(mod),
        )
    )


def missing_categories(mods: list[ModEntry], requested: Iterable[str]) -> list[str]:
    """Return requested roles not represented by the current selection."""
    covered = {role for mod in mods for role in roles_for(mod)}
    missing: list[str] = []
    for value in requested:
        role = normalize_role(value)
        if role and role not in covered and role not in missing:
            missing.append(role)
    return missing


def coverage_report(mods: list[ModEntry], requested: Iterable[str]) -> dict[str, Any]:
    normalized = list(dict.fromkeys(normalize_role(value) for value in requested if value))
    covered = sorted({role for mod in mods for role in roles_for(mod)})
    missing = missing_categories(mods, normalized)
    ratio = 1.0 if not normalized else (len(normalized) - len(missing)) / len(normalized)
    return {
        "requested": normalized,
        "covered": covered,
        "missing": missing,
        "coverage_percent": round(ratio * 100),
    }


def recommendation_score(mod: ModEntry, requested_roles: Iterable[str]) -> float:
    """Rank alternatives without letting downloads erase intent match."""
    requested = {normalize_role(value) for value in requested_roles if value}
    match = len(set(roles_for(mod)).intersection(requested))
    popularity = min(1.0, max(0.0, mod.downloads / 10_000_000))
    artifact = 1.0 if mod.file_name and mod.download_url else 0.0
    hashed = 1.0 if mod.hashes.sha1 or mod.hashes.sha512 else 0.0
    return round(match * 0.45 + artifact * 0.25 + hashed * 0.15 + popularity * 0.15, 6)


def alternatives_for(
    mod: ModEntry,
    candidates: list[ModEntry],
    limit: int = MAX_ALTERNATIVES,
) -> list[str]:
    """Find same-role alternatives while excluding the selected identity."""
    roles = set(roles_for(mod))
    ranked = [
        candidate
        for candidate in candidates
        if _mod_key(candidate) != _mod_key(mod)
        and roles.intersection(roles_for(candidate))
    ]
    ranked.sort(
        key=lambda candidate: (
            recommendation_score(candidate, roles),
            candidate.downloads,
            candidate.name.casefold(),
        ),
        reverse=True,
    )
    return list(dict.fromkeys(candidate.name for candidate in ranked if candidate.name))[: max(0, limit)]


def build_alternative_map(
    selected: list[ModEntry], candidates: list[ModEntry], limit: int = MAX_ALTERNATIVES
) -> dict[str, list[str]]:
    return {
        _mod_key(mod): alternatives_for(mod, candidates, limit=limit)
        for mod in selected
    }


def confidence_for(mod: ModEntry, requested_roles: Iterable[str]) -> int:
    requested = {normalize_role(value) for value in requested_roles if value}
    match = len(set(roles_for(mod)).intersection(requested))
    evidence = len(_evidence_for(mod))
    risk = len(_risk_flags_for(mod))
    return max(20, min(99, 35 + match * 18 + min(20, evidence * 3) - risk * 3))


def _redundancy_report(mods: list[ModEntry]) -> list[dict[str, Any]]:
    by_role: dict[str, list[str]] = {}
    for mod in mods:
        for role in roles_for(mod):
            by_role.setdefault(role, []).append(mod.name)
    return [
        {
            "role": role,
            "mods": names,
            "reason": "Several mods serve the same role; review overlap and configuration conflicts.",
        }
        for role, names in sorted(by_role.items())
        if len(names) > 3
    ]


def critique_pack(
    mods: list[ModEntry],
    requested: Iterable[str],
    *,
    ram_gb: int | None = None,
    fps_target: int | None = None,
    shader_support: str | None = None,
) -> dict[str, Any]:
    """Produce a deterministic self-critique after candidate selection."""
    quality = quality_report(mods)
    synergy = synergy_report(mods)
    performance = performance_estimate(
        mods,
        ram_gb=ram_gb,
        fps_target=fps_target,
        shader_support=shader_support,
    )
    coverage = coverage_report(mods, requested)
    redundancy = _redundancy_report(mods)
    problems: list[dict[str, Any]] = []
    for category in coverage["missing"]:
        problems.append(
            {
                "type": "missing_category",
                "category": category,
                "severity": "medium",
                "recommendation": f"Search for more {category.replace('_', ' ')} content.",
            }
        )
    for conflict in synergy.get("conflicts", []):
        problems.append(
            {
                "type": "worldgen_overlap",
                "mods": conflict.get("mods", []),
                "severity": "high",
                "recommendation": "Review world-generation configs before export.",
            }
        )
    for item in redundancy:
        problems.append(
            {
                "type": "redundancy",
                "role": item["role"],
                "mods": item["mods"],
                "severity": "low",
                "recommendation": item["reason"],
            }
        )
    expected_fps = performance.get("expected_fps", {})
    if fps_target and expected_fps.get("low", fps_target) < fps_target:
        problems.append(
            {
                "type": "fps_risk",
                "severity": "high",
                "recommendation": "Reduce heavy world-generation, entity, or shader content.",
            }
        )
    if ram_gb and performance.get("ram_gb", ram_gb) > ram_gb:
        problems.append(
            {
                "type": "ram_risk",
                "severity": "high",
                "recommendation": "Increase allocated RAM or choose a lighter variant.",
            }
        )
    return {
        "quality": quality,
        "performance": performance,
        "synergy": synergy,
        "coverage": coverage,
        "missing_categories": coverage["missing"],
        "redundancy": redundancy,
        "problems": problems,
        "recommendations": list(dict.fromkeys(problem["recommendation"] for problem in problems)),
    }


def selection_feedback(
    selected: list[ModEntry],
    candidates: list[ModEntry],
    requested: Iterable[str],
    *,
    ram_gb: int | None = None,
    fps_target: int | None = None,
    shader_support: str | None = None,
) -> dict[str, Any]:
    """Summarize why the selected set won and what the next round should do."""
    requested_values = tuple(requested)
    alternatives = build_alternative_map(selected, candidates)
    reasons: dict[str, str] = {}
    confidence: dict[str, int] = {}
    for mod in selected:
        roles = roles_for(mod)
        overlap = sorted(set(roles).intersection({normalize_role(value) for value in requested_values}))
        reasons[_mod_key(mod)] = (
            f"Covers {', '.join(overlap)} with catalog-backed compatibility evidence."
            if overlap
            else "Adds a compatible supporting role while preserving category diversity."
        )
        confidence[_mod_key(mod)] = confidence_for(mod, requested_values)
    return {
        "selected_count": len(selected),
        "candidate_count": len(candidates),
        "coverage": coverage_report(selected, requested_values),
        "reasons": reasons,
        "confidence": confidence,
        "alternatives": alternatives,
        "critique": critique_pack(
            selected,
            requested_values,
            ram_gb=ram_gb,
            fps_target=fps_target,
            shader_support=shader_support,
        ),
    }
