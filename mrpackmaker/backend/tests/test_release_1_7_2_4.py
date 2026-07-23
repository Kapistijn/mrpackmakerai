"""1.7.2.4 regression coverage for prompt content priorities."""

from app.services.prompt_pipeline import CONTENT_INTENT_CONSTRAINTS, optimize_prompt


def test_bosses_in_prompt_always_produces_boss_constraint():
    brief = optimize_prompt(
        "Maak een horror modpack, minimaal 15 mods, geen dubbele mods, veel bosses",
        minecraft_version="1.20.1", loader="forge", theme="horror",
        difficulty="hard", performance_preference="stability",
    )
    assert "Minecraft 1.20.1" in brief.normalized_request
    assert "select at least 15 compatible mods" in brief.constraints
    assert "deduplicate by project identity, slug, name, file and hashes" in brief.constraints
    assert CONTENT_INTENT_CONSTRAINTS["bosses"] in brief.constraints
