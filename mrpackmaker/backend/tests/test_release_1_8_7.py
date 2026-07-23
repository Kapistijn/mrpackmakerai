"""1.8.7 - real intent analysis and functional advanced configuration.

Covers the whole flow the spec asks for: intent analysis, RAM/FPS/shader/
performance driving selection and export, self-check re-search, dependency
repair diagnostics, and the end-to-end "realistic survival + shaders + 16GB +
120 FPS" scenario.
"""

from __future__ import annotations

import asyncio
import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models.enums import LoaderType
from app.models.project import Project
from app.schemas.mod import ModDependency, ModEntry, ModHash
from app.services.intent_analysis import analyze_intent
from app.services.mrpack import MrpackGenerator
from app.services.pack_assets import build_pack_info, override_files, shader_loader_queries
from app.services.pack_profile import SHADER_ENABLED, SHADER_OFF, build_pack_profile, profile_from_project
from app.services.quality_scoring import is_blocked, score_mod_quality
from app.services.requirements import parse_requirements
from app.services.self_check import fill_missing, missing_queries, verify_requirements


def _mod(name, *, categories=(), downloads=1000, summary="", deps=(), source="modrinth", filename=None):
    filename = filename or f"{name}.jar"
    return ModEntry(
        id=name, source=source, name=name, slug=name, summary=summary, downloads=downloads,
        categories=list(categories), loaders=["fabric"], selected_version="1.20.1",
        file_name=filename, file_size=100, download_url=f"https://cdn.modrinth.com/{filename}",
        hashes=ModHash(sha1="a" * 40), dependencies=list(deps),
    )


# --- Part 1: intent analysis -------------------------------------------------

def test_intent_analysis_detects_realism():
    intent = analyze_intent("Make a Minecraft modpack that is as close to real life as possible")
    assert intent.realism_focus
    assert intent.goal == "realism survival"
    assert "weather" in intent.categories and "farming" in intent.categories
    assert "magic" in intent.avoid


def test_intent_analysis_theme_fallback_when_not_realism():
    intent = analyze_intent("a fun automation pack", theme="technology")
    assert not intent.realism_focus
    assert "technology" in intent.categories


# --- Part 3: RAM drives selection --------------------------------------------

def test_ram_scales_content_budget_and_heavy_worldgen():
    low = build_pack_profile(parse_requirements("", target_ram_gb=4))
    high = build_pack_profile(parse_requirements("", target_ram_gb=32))
    assert low.max_content_mods < high.max_content_mods
    assert not low.allow_heavy_worldgen and high.allow_heavy_worldgen
    assert low.performance_floor >= 0.7


def test_low_ram_blocks_heavy_worldgen_mod():
    profile = build_pack_profile(parse_requirements("", target_ram_gb=4))
    intent = analyze_intent("realistic survival")
    heavy = _mod("terrablender", categories=["worldgen"], summary="huge world generation terrain")
    assert is_blocked(score_mod_quality(heavy, intent, profile), profile)


# --- Part 3: shader support has real output ----------------------------------

def test_shader_option_changes_output():
    on = build_pack_profile(parse_requirements("", shader_support="enabled", target_ram_gb=16))
    off = build_pack_profile(parse_requirements("", shader_support="off", target_ram_gb=16))
    assert on.shader_mode == SHADER_ENABLED and off.shader_mode == SHADER_OFF
    assert build_pack_info(on)["shader_support"] is True
    assert build_pack_info(off)["shader_support"] is False
    assert "shaderpacks/README.txt" in override_files(on, [])
    assert "shaderpacks/README.txt" not in override_files(off, [])
    assert shader_loader_queries(on, "fabric") == ["iris", "sodium"]
    assert shader_loader_queries(off, "fabric") == []


def test_shader_downgraded_on_low_ram():
    profile = build_pack_profile(parse_requirements("", shader_support="enabled", target_ram_gb=4))
    assert profile.shader_mode == "optional"


# --- Part 3: FPS drives scoring and performance-mod gating -------------------

def test_fps_target_sets_floor_and_gates_performance_mods():
    fast = build_pack_profile(parse_requirements("", target_fps=240, target_ram_gb=16))
    assert fast.performance_floor >= 0.85 and fast.needs_performance_mods
    balanced = build_pack_profile(parse_requirements("", target_ram_gb=8))
    assert not balanced.needs_performance_mods
    intent = analyze_intent("survival pack", theme="survival")
    sodium = _mod("sodium", categories=["optimization"], summary="performance optimization fps")
    assert score_mod_quality(sodium, intent, balanced).is_performance_mod
    assert is_blocked(score_mod_quality(sodium, intent, balanced), balanced)
    assert not is_blocked(score_mod_quality(sodium, intent, fast), fast)


# --- Part 4: export contains configs + shaders + pack_info -------------------

def test_pack_export_includes_overrides_and_shaders(tmp_path):
    profile = build_pack_profile(parse_requirements("", shader_support="enabled", target_ram_gb=16, resourcepack_support=True))
    project = Project(
        name="Realism", description="realistic survival", minecraft_version="1.20.1",
        loader="fabric", theme="survival", difficulty="normal",
        performance_preference="balanced", resolved_loader_version="0.15.11",
    )
    mods = [
        _mod("farmersdelight", categories=["food", "farming"], summary="realistic farming food"),
        _mod("complementary", categories=["shader"], summary="shaderpack", filename="complementary.zip"),
    ]
    gen = MrpackGenerator()
    index = gen.build_index(project, mods, profile)
    overrides = gen.build_overrides(profile, mods)
    out = gen.write_pack(index, overrides, tmp_path / "realism.mrpack")
    with zipfile.ZipFile(out) as archive:
        names = archive.namelist()
        assert "modrinth.index.json" in names
        assert "overrides/pack_info.json" in names
        assert "overrides/options.txt" in names
        assert "overrides/config/mrpackmaker-profile.json" in names
        assert "overrides/shaderpacks/README.txt" in names
        assert "overrides/resourcepacks/README.txt" in names
        paths = [entry["path"] for entry in json.loads(archive.read("modrinth.index.json"))["files"]]
        assert any(p.startswith("shaderpacks/") for p in paths)
        assert any(p.startswith("mods/") for p in paths)
        info = json.loads(archive.read("overrides/pack_info.json"))
        assert info["shader_support"] is True and info["recommended_ram"] == 16


# --- Part 5: self-check finds missing categories and re-searches -------------

def test_self_check_flags_missing_and_fills_from_candidates():
    intent = analyze_intent("realistic survival with farming and weather")
    selected = [_mod("weather2", categories=["weather"], summary="dynamic weather storms")]
    check = verify_requirements(selected, intent)
    assert not check.complete
    assert "farming" in check.missing
    assert "farming" in missing_queries(check)
    candidates = selected + [_mod("farmersdelight", categories=["farming"], summary="crops agriculture farming")]
    profile = build_pack_profile(parse_requirements("", target_ram_gb=8))
    additions = fill_missing(candidates, selected, check, intent, profile)
    assert any("farm" in " ".join(m.categories) for m in additions)


# --- Part 6: dependency repair reports the specific unresolved dependency ----

def test_dependency_repair_reports_specific_unresolved_dependency():
    from app.services.dependency_resolver import DependencyResolver
    from app.services.mod_resolver import ModResolver
    from app.services.source_registry import ModSourceRegistry

    root = _mod("root", deps=[ModDependency(project_id="ghostlib")])

    class Provider:
        source_id = "modrinth"
        available = True

        async def search(self, *args, **kwargs):
            return [], 0

        async def get_mod_detail(self, mod_id, mc, loader):
            return None  # the dependency can never be resolved

        async def close(self):
            return None

    async def run():
        resolver = DependencyResolver(ModResolver(registry=ModSourceRegistry([Provider()])))
        return await resolver.resolve_pack([root], "1.20.1", LoaderType.FABRIC)

    result = asyncio.run(run())
    assert not result.complete
    messages = " ".join(f.message() for f in result.failures)
    assert "ghostlib" in messages and "No compatible" in messages


# --- Full flow: the exact scenario from the spec -----------------------------

def test_full_flow_realistic_survival_shaders_16gb_120fps():
    prompt = "Make a realistic survival modpack with shaders"
    req = parse_requirements(prompt, target_ram_gb=16, target_fps=120, shader_support="enabled", performance_preference="balanced")
    intent = analyze_intent(prompt, theme="survival")
    profile = build_pack_profile(req)
    assert intent.realism_focus and intent.goal == "realism survival"
    assert profile.recommended_ram_gb == 16
    assert profile.shader_mode == SHADER_ENABLED
    assert profile.shader_quality == "high"
    assert profile.target_fps == 120
    assert profile.needs_performance_mods
    assert json.loads(override_files(profile, [])["pack_info.json"])["target_fps"] == 120


def test_profile_from_project_reads_persisted_fields():
    project = Project(
        name="P", description="realistic survival", minecraft_version="1.20.1", loader="fabric",
        theme="survival", performance_preference="performance", generation_prompt="realistic survival",
        minimum_mods=None, maximum_mods=None, minimum_downloads=0,
        target_ram_gb=32, target_fps=144, shader_support="enabled", shader_quality="high",
        resourcepack_support=True,
    )
    profile = profile_from_project(project)
    assert profile.recommended_ram_gb == 32
    assert profile.shader_mode == SHADER_ENABLED
    assert profile.performance_profile == "performance"


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-q"]))
