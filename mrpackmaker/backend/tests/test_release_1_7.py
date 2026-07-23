"""Release 1.7 regression tests."""

from app.models.enums import LoaderType
from app.schemas.mod import ModEntry, ModHash
from app.services.mod_resolver import ModResolver, mod_identity
from app.services.prompt_pipeline import optimize_prompt


def test_prompt_pipeline_expands_sparse_input_and_preserves_constraints():
    brief = optimize_prompt(
        "Maak een horror modpack, minimaal 15 mods, geen dubbele mods, veel bosses",
        minecraft_version="1.20.1", loader="forge", theme="horror",
        difficulty="hard", performance_preference="stability",
    )
    assert "Minecraft 1.20.1" in brief.normalized_request
    assert "select at least 15 compatible mods" in brief.constraints
    assert "deduplicate by project identity, slug, name, file and hashes" in brief.constraints
    assert "prefer content with bosses when compatible" in brief.constraints
    assert "resolve required dependencies recursively" in brief.constraints


def test_prompt_pipeline_has_safe_defaults_for_empty_text():
    brief = optimize_prompt("", minecraft_version="1.21.1", loader="fabric", theme="survival", difficulty="normal", performance_preference="balanced")
    assert brief.original == ""
    assert "survival" in brief.normalized_request
    assert brief.system_prompt.startswith("You are a senior Minecraft modpack architect")


def test_cross_source_identity_ignores_source_specific_ids():
    a = ModEntry(id="abc", source="modrinth", name="Create", slug="create", hashes=ModHash())
    b = ModEntry(id="123", source="curseforge", name="Create Mod", slug="create", hashes=ModHash())
    assert mod_identity(a) == mod_identity(b)
    assert len(ModResolver.deduplicate([a, b])) == 1
