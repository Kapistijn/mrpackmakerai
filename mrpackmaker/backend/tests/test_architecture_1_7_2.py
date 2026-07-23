"""High-signal regression tests for the 1.7.2 architecture update."""

import pytest

from app.models.enums import LoaderType
from app.schemas.mod import ModDependency, ModEntry, ModHash
from app.services.dependency_graph import DependencyGraph
from app.services.prompt_pipeline import extract_intent, optimize_prompt, validate_intent
from app.services.mrpack_validation import validate_export_inputs


def entry(source: str, project_id: str, *, deps: list[ModDependency] | None = None, slug: str | None = None) -> ModEntry:
    return ModEntry(
        id=project_id, source=source, name=project_id.title(), slug=slug or project_id,
        dependencies=deps or [], file_name=f"{project_id}.jar", file_size=100,
        download_url="https://cdn.modrinth.com/files/example.jar", hashes=ModHash(sha1=project_id),
    )


def test_dependency_graph_orders_dependencies_first():
    graph = DependencyGraph()
    graph.add_mod(entry("modrinth", "base"))
    graph.add_mod(entry("modrinth", "addon", deps=[ModDependency(project_id="base", source="modrinth")]))
    order = graph.topological_order()
    assert order.index("modrinth:base") < order.index("modrinth:addon")


def test_dependency_graph_reports_cycles_and_refuses_ordering():
    graph = DependencyGraph()
    graph.add_mod(entry("modrinth", "a", deps=[ModDependency(project_id="b", source="modrinth")]))
    graph.add_mod(entry("modrinth", "b", deps=[ModDependency(project_id="a", source="modrinth")]))
    assert graph.get_cycles() == [["modrinth:a", "modrinth:b"]]
    with pytest.raises(ValueError, match="Dependency cycle detected"):
        graph.topological_order()


def test_missing_required_and_optional_dependencies_are_separate():
    graph = DependencyGraph()
    graph.add_mod(entry("modrinth", "a", deps=[
        ModDependency(project_id="required", source="modrinth", dependency_type="required"),
        ModDependency(project_id="optional", source="modrinth", dependency_type="optional"),
    ]))
    assert graph.get_missing_required() == ["modrinth:required"]
    assert graph.get_optional_missing() == ["modrinth:optional"]


def test_prompt_intent_detects_theme_constraints_and_multiplayer():
    intent = extract_intent("horror multiplayer, minimaal 15 mods, geen magie")
    assert "horror" in intent.themes
    assert intent.minimum_mods == 15
    assert intent.multiplayer is True
    assert intent.forbidden_features == ("magic",)


def test_prompt_validation_rejects_impossible_bounds():
    intent = extract_intent("at least 20 mods at most 10 mods")
    assert validate_intent(intent) == ["minimum mod count cannot exceed maximum mod count"]


def test_prompt_brief_hides_original_from_generation_prompt():
    brief = optimize_prompt("secret user wording", minecraft_version="1.20.1", loader="forge", theme="horror", difficulty="hard", performance_preference="stability")
    assert "secret user wording" not in brief.system_prompt
    assert "Minecraft 1.20.1 with forge only" in brief.constraints


def test_export_rejects_duplicate_hashes_and_insecure_urls():
    project = type("Project", (), {"resolved_loader_version": "47.2.0", "loader_version": None})()
    first = entry("modrinth", "a")
    second = entry("curseforge", "b")
    second.download_url = "http://cdn.modrinth.com/files/b.jar"
    second.hashes = ModHash(sha1=first.hashes.sha1)
    issues = validate_export_inputs(project, [first, second])
    codes = {issue.code for issue in issues}
    assert "download_invalid" in codes
    assert "duplicate_hash" in codes
