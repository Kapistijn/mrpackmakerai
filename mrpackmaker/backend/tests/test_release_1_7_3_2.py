"""1.7.3.2 personalization regression tests."""

from app.schemas.mod import ModEntry, ModHash
from app.services.mod_scoring import rank_mods, select_diverse
from app.services.requirements import parse_requirements


def make_mod(name: str, category: str, downloads: int = 100) -> ModEntry:
    return ModEntry(
        id=name,
        source="modrinth",
        name=name,
        slug=name.casefold(),
        summary=category,
        categories=[category],
        downloads=downloads,
        file_name=f"{name}.jar",
        file_size=100,
        download_url="https://cdn.modrinth.com/file.jar",
        hashes=ModHash(sha1=name),
    )


def test_diverse_selection_covers_categories_before_filling_by_score():
    requirements = parse_requirements("horror with bosses")
    ranked = rank_mods([
        make_mod("boss-a", "bosses", 1000),
        make_mod("boss-b", "bosses", 999),
        make_mod("atmosphere", "atmosphere", 10),
        make_mod("mobs", "mobs", 50),
    ], requirements, seed=3)
    selected = select_diverse(ranked, 3)
    assert {category for item in selected for category in item.mod.categories} >= {"bosses", "atmosphere", "mobs"}


def test_zero_project_download_limit_does_not_erase_prompt_semantics():
    requirements = parse_requirements("horror minimum downloads 100000", minimum_downloads=0)
    assert requirements.minimum_downloads == 100000
