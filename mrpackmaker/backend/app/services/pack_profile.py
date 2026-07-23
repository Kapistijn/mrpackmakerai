"""Build a concrete profile from advanced modpack requirements.

This module is intentionally backwards-compatible with projects created before
1.8.7. It is the shared contract consumed by scoring, generation, export, and
compatibility checks.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.services.requirements import Requirements, parse_requirements

SHADER_OFF, SHADER_OPTIONAL, SHADER_ENABLED = "off", "optional", "enabled"
_SHADER_ALIASES = {
    "off": SHADER_OFF,
    "none": SHADER_OFF,
    "disabled": SHADER_OFF,
    "": SHADER_OFF,
    "optional": SHADER_OPTIONAL,
    "shader_compatible": SHADER_OPTIONAL,
    "compatible": SHADER_OPTIONAL,
    "enabled": SHADER_ENABLED,
    "on": SHADER_ENABLED,
    "required": SHADER_ENABLED,
    "yes": SHADER_ENABLED,
}


def normalize_shader(value: str | None) -> str:
    return _SHADER_ALIASES.get((value or "").strip().casefold(), SHADER_OFF)


def _ram_content_budget(ram_gb: int) -> int:
    """Bound content volume by the user's available memory budget."""
    if ram_gb <= 4:
        return 40
    if ram_gb <= 8:
        return 90
    if ram_gb <= 16:
        return 150
    return 300


@dataclass(frozen=True)
class PackProfile:
    recommended_ram_gb: int
    target_fps: int | None
    shader_mode: str
    shader_quality: str
    performance_profile: str
    performance_floor: float
    allow_heavy_worldgen: bool
    allow_heavy_mods: bool
    max_content_mods: int
    resourcepack_support: bool

    @property
    def needs_performance_mods(self) -> bool:
        return (
            self.performance_profile == "performance"
            or (self.target_fps is not None and self.target_fps >= 120)
            or self.recommended_ram_gb <= 4
        )

    def as_pack_info(self) -> dict:
        return {
            "recommended_ram": self.recommended_ram_gb,
            "shader_support": self.shader_mode != SHADER_OFF,
            "shader_mode": self.shader_mode,
            "shader_quality": self.shader_quality,
            "target_fps": self.target_fps,
            "performance_profile": self.performance_profile,
            "resourcepack_support": self.resourcepack_support,
        }


def _performance_profile(req: Requirements) -> str:
    explicit = (req.performance_preference or "").strip().casefold()
    if explicit in {"performance", "balanced", "visuals"}:
        return explicit
    if req.target_fps is not None and req.target_fps >= 120:
        return "performance"
    if req.target_fps is not None and req.target_fps <= 30:
        return "visuals"
    if req.shader_support and normalize_shader(req.shader_support) == SHADER_ENABLED:
        return "visuals"
    return "balanced"


def _performance_floor(ram_gb: int, target_fps: int | None, profile: str) -> float:
    floor = 0.6 if profile == "performance" else 0.0
    if target_fps is not None:
        if target_fps >= 240:
            floor = max(floor, 0.85)
        elif target_fps >= 144:
            floor = max(floor, 0.75)
        elif target_fps >= 120:
            floor = max(floor, 0.6)
    if ram_gb <= 4:
        floor = max(floor, 0.7)
    return round(floor, 3)


def build_pack_profile(req: Requirements) -> PackProfile:
    """Translate requirements into selection and export directives."""
    profile = _performance_profile(req)
    ram_gb = req.target_ram_gb or {"performance": 6, "balanced": 8, "visuals": 12}[profile]
    shader_mode = normalize_shader(req.shader_support)
    # Keep a 4GB pack launchable. Compatibility still reports the downgrade.
    if shader_mode == SHADER_ENABLED and ram_gb <= 4:
        shader_mode = SHADER_OPTIONAL

    explicit_quality = (req.visual_quality or "").strip().casefold()
    shader_quality = (
        explicit_quality
        if explicit_quality in {"low", "medium", "high"}
        else "high" if ram_gb >= 16 else "medium" if ram_gb >= 8 else "low"
    )
    budget = _ram_content_budget(ram_gb)
    if req.maximum_mods is not None:
        budget = min(budget, req.maximum_mods)
    if req.minimum_mods is not None:
        budget = max(budget, req.minimum_mods)

    return PackProfile(
        recommended_ram_gb=ram_gb,
        target_fps=req.target_fps,
        shader_mode=shader_mode,
        shader_quality=shader_quality,
        performance_profile=profile,
        performance_floor=_performance_floor(ram_gb, req.target_fps, profile),
        allow_heavy_worldgen=ram_gb >= 8,
        allow_heavy_mods=ram_gb >= 8,
        max_content_mods=budget,
        resourcepack_support=bool(req.resourcepack_support),
    )


def profile_from_project(project) -> PackProfile:
    """Recompute a profile while accepting legacy project objects and rows."""
    value = lambda name, default=None: getattr(project, name, default)
    prompt = value("generation_prompt", "") or value("description", "") or ""
    req = parse_requirements(
        prompt,
        theme=value("theme"),
        minimum_mods=value("minimum_mods"),
        maximum_mods=value("maximum_mods"),
        minimum_downloads=value("minimum_downloads", 0),
        target_ram_gb=value("target_ram_gb"),
        target_fps=value("target_fps"),
        shader_support=value("shader_support"),
        performance_preference=value("performance_preference"),
        visual_quality=value("shader_quality"),
        resourcepack_support=value("resourcepack_support", False),
        required_mods=value("required_mods_json", "[]"),
        forbidden_mods=value("forbidden_mods_json", "[]"),
    )
    return build_pack_profile(req)
