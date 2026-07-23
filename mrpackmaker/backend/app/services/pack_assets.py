"""Deterministic non-mod pack assets: configs, options, shader metadata.

The MRPack writer uses these to populate the ``overrides/`` tree and the
``pack_info.json`` descriptor, so an exported pack reflects the chosen RAM,
FPS, shader and performance settings instead of shipping mods alone.
"""

from __future__ import annotations

import json

from app.schemas.mod import ModEntry
from app.services.pack_profile import PackProfile, SHADER_ENABLED, SHADER_OFF


def build_pack_info(profile: PackProfile) -> dict:
    return profile.as_pack_info()


def _render_distance(profile: PackProfile) -> int:
    if profile.recommended_ram_gb >= 16:
        return 16
    if profile.recommended_ram_gb >= 8:
        return 12
    return 8


def default_options_txt(profile: PackProfile) -> str:
    # 1 = fancy graphics, 0 = fast graphics
    graphics = "0" if profile.performance_profile == "performance" else "1"
    lines = [
        f"renderDistance:{_render_distance(profile)}",
        f"graphicsMode:{graphics}",
        "maxFps:%d" % (profile.target_fps or 120),
        "entityShadows:%s" % ("false" if profile.performance_profile == "performance" else "true"),
    ]
    return "\n".join(lines) + "\n"


def shaderpack_note(profile: PackProfile) -> str | None:
    if profile.shader_mode == SHADER_OFF:
        return None
    recommended = {
        "low": "ComplementaryUnbound (Potato preset)",
        "medium": "ComplementaryReimagined (Medium preset)",
        "high": "BSL / Complementary (High preset)",
    }[profile.shader_quality]
    mode = "auto-enabled" if profile.shader_mode == SHADER_ENABLED else "supported (install a pack to enable)"
    return (
        f"Shader support: {mode}\n"
        f"Recommended shaderpack: {recommended}\n"
        f"Place .zip shaderpacks in this folder. A shader loader (Iris/Oculus) is bundled.\n"
    )


def override_files(profile: PackProfile, mods: list[ModEntry]) -> dict[str, str]:
    """Return a mapping of override path -> file content (relative to overrides/)."""
    pack_info = json.dumps(build_pack_info(profile), indent=2) + "\n"
    files: dict[str, str] = {
        "pack_info.json": pack_info,
        "options.txt": default_options_txt(profile),
        "config/mrpackmaker-profile.json": pack_info,
    }
    note = shaderpack_note(profile)
    if note is not None:
        files["shaderpacks/README.txt"] = note
    if profile.resourcepack_support:
        files["resourcepacks/README.txt"] = "Drop .zip resource packs in this folder.\n"
    return files


def shader_loader_queries(profile: PackProfile, loader: str) -> list[str]:
    """Search queries for the shader loader stack, empty when shaders are off."""
    if profile.shader_mode == SHADER_OFF:
        return []
    loader = (loader or "").casefold()
    if loader == "fabric":
        return ["iris", "sodium"]
    # Forge / NeoForge equivalents
    return ["oculus", "embeddium"]
