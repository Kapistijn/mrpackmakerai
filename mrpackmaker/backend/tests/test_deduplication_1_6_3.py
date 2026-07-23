"""1.6.3 regression tests for cross-catalog mod deduplication."""

from app.schemas.mod import ModEntry
from app.services.mod_resolver import ModResolver, mod_identity


def mod(source: str, *, slug: str, name: str, downloads: int = 0, file: bool = True) -> ModEntry:
    return ModEntry(
        id=f"{source}-{slug}",
        source=source,
        name=name,
        slug=slug,
        downloads=downloads,
        file_name=f"{slug}.jar" if file else None,
        download_url=f"https://cdn.example/{slug}.jar" if file else None,
    )


def test_modrinth_and_curseforge_same_slug_have_one_identity():
    left = mod("modrinth", slug="create", name="Create")
    right = mod("curseforge", slug="create", name="Create Mod")
    assert mod_identity(left) == mod_identity(right)


def test_deduplicate_keeps_the_richer_entry():
    incomplete = mod("modrinth", slug="create", name="Create", downloads=10, file=False)
    complete = mod("curseforge", slug="create", name="Create", downloads=1, file=True)
    result = ModResolver.deduplicate([incomplete, complete])
    assert len(result) == 1
    assert result[0].source == "curseforge"


def test_deduplicate_keeps_distinct_projects():
    result = ModResolver.deduplicate([
        mod("modrinth", slug="create", name="Create"),
        mod("modrinth", slug="createaddition", name="Create Addition"),
    ])
    assert len(result) == 2
