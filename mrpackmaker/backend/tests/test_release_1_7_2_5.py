"""1.7.2.5 regression coverage for the prompt contract."""

from app.services.prompt_pipeline import DEPENDENCY_CONSTRAINT, optimize_prompt


def test_optimized_prompt_requires_recursive_dependencies():
    brief = optimize_prompt(
        "Maak een horror modpack, minimaal 15 mods, geen dubbele mods, veel bosses",
        minecraft_version="1.20.1", loader="forge", theme="horror",
        difficulty="hard", performance_preference="stability",
    )
    assert DEPENDENCY_CONSTRAINT == "resolve required dependencies recursively"
    assert DEPENDENCY_CONSTRAINT in brief.constraints
