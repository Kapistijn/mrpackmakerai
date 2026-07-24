from app.schemas.mod import ModEntry, ModHash
from app.services.ai_reasoning import (
    alternatives_for,
    build_alternative_map,
    build_mod_memory,
    confidence_for,
    coverage_report,
    critique_pack,
    missing_categories,
    normalize_role,
    recommendation_score,
    roles_for,
    selection_feedback,
)


def mod(name, categories=(), downloads=100, file=True, dependencies=()):
    return ModEntry(
        id=name,
        source="modrinth",
        name=name,
        slug=name.lower().replace(" ", "-"),
        summary=" ".join(categories),
        categories=list(categories),
        downloads=downloads,
        file_name=f"{name}.jar" if file else None,
        download_url=f"https://cdn.modrinth.com/{name}.jar" if file else None,
        hashes=ModHash(sha1="a" * 40) if file else ModHash(),
        dependencies=list(dependencies),
    )


def test_role_aliases_and_missing_categories_are_canonical():
    assert normalize_role("world generation") == "world_generation"
    current = [mod("Terrain", ("worldgen",))]
    assert "automation" in missing_categories(current, ["automation", "world generation"])
    assert "world_generation" not in missing_categories(current, ["world generation"])


def test_mod_memory_contains_evidence_risk_and_reasoning():
    result = build_mod_memory(
        mod("Create", ("technology", "automation"), downloads=1000),
        reason="Matches factory intent",
        confidence=70,
        requested_roles=("automation",),
    )
    assert result["roles"]
    assert result["reason"] == "Matches factory intent"
    assert result["confidence"] > 70
    assert "compatible downloadable file" in result["evidence"]
    assert result["intent_match"] == 25


def test_critique_finds_missing_overlap_and_performance_risks():
    result = critique_pack(
        [
            mod("Terrain A", ("worldgen",)),
            mod("Terrain B", ("worldgen",)),
            mod("Terrain C", ("worldgen",)),
            mod("Terrain D", ("worldgen",)),
        ],
        ["automation", "world generation"],
        ram_gb=4,
        fps_target=120,
        shader_support="enabled",
    )
    assert "automation" in result["missing_categories"]
    assert result["synergy"]["conflicts"]
    assert any(problem["type"] == "redundancy" for problem in result["problems"])
    assert any(problem["type"] == "fps_risk" for problem in result["problems"])


def test_alternatives_are_role_matched_and_deterministic():
    current = mod("Create", ("technology", "automation"), 100)
    better = mod("Tech Reborn", ("technology", "automation"), 900)
    unrelated = mod("Magic", ("magic",), 999999)
    choices = [current, better, unrelated]
    assert alternatives_for(current, choices) == ["Tech Reborn"]
    assert build_alternative_map([current], choices)["modrinth:create"] == ["Tech Reborn"]


def test_selection_feedback_exposes_coverage_confidence_and_alternatives():
    selected = [mod("Factory", ("automation",))]
    candidates = selected + [mod("Factory Plus", ("automation",), 500)]
    result = selection_feedback(selected, candidates, ["automation"])
    assert result["selected_count"] == 1
    assert result["coverage"]["coverage_percent"] == 100
    assert result["confidence"]
    assert result["alternatives"]["modrinth:factory"] == ["Factory Plus"]


def test_quality_score_prefers_intent_and_artifacts_over_raw_downloads():
    compatible = mod("Automation", ("automation",), 100)
    popular_unrelated = mod("Magic", ("magic",), 10_000_000)
    assert recommendation_score(compatible, ["automation"]) > recommendation_score(
        popular_unrelated, ["automation"]
    )
    assert roles_for(compatible)
    assert coverage_report([compatible], ["automation"])["coverage_percent"] == 100
    assert confidence_for(compatible, ["automation"]) >= 50
