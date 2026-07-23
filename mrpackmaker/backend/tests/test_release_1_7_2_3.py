"""1.7.2.3 prompt regression tests."""

from app.services.prompt_pipeline import CONTENT_INTENT_CONSTRAINTS, extract_intent, optimize_prompt


def test_content_intents_become_selection_constraints():
    brief = optimize_prompt(
        "Maak een horror modpack, minimaal 15 mods, geen dubbele mods, veel bosses",
        minecraft_version="1.20.1", loader="forge", theme="horror",
        difficulty="hard", performance_preference="stability",
    )
    assert CONTENT_INTENT_CONSTRAINTS["bosses"] in brief.constraints
    assert "select at least 15 compatible mods" in brief.constraints


def test_dutch_horror_content_terms_are_detected():
    intent = extract_intent("horror met monsters en zombies, geen magie")
    assert "horror" in intent.themes
    assert "monsters" in intent.gameplay_styles
    assert "zombies" in intent.gameplay_styles
    assert intent.forbidden_features == ("magic",)
