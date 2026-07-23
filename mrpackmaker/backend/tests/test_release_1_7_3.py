"""1.7.3 intelligence and loader regression tests."""

import asyncio

import pytest

from app.models.enums import LoaderType
from app.schemas.mod import ModEntry, ModHash
from app.services.loader_resolver import LoaderResolver, LoaderResolutionError
from app.services.mod_scoring import rank_mods
from app.services.requirements import parse_requirements, theme_matches


def mod(name: str, categories: list[str], downloads: int = 1000) -> ModEntry:
    return ModEntry(id=name, source="modrinth", name=name, slug=name.casefold(), summary=" ".join(categories), categories=categories, downloads=downloads, file_name=f"{name}.jar", file_size=100, download_url="https://cdn.modrinth.com/file.jar", hashes=ModHash(sha1=name))


def test_horror_policy_excludes_cobblemon_and_technology():
    requirements = parse_requirements("maak een horror modpack met monsters en bosses")
    assert "horror" in requirements.themes
    assert "cobblemon" in requirements.forbidden_features
    assert not theme_matches("Cobblemon pokemon technology", requirements)
    assert theme_matches("Horror mobs atmosphere", requirements)


def test_minimum_150_is_preserved():
    requirements = parse_requirements("horror modpack met minimaal 150 mods")
    assert requirements.minimum_mods == 150
    assert requirements.target_count == 150


def test_scoring_does_not_make_downloads_the_primary_signal():
    requirements = parse_requirements("horror with bosses")
    ranked = rank_mods([mod("Popular Utility", ["utility"], 10_000_000), mod("Horror Bosses", ["horror", "bosses"], 100)], requirements, seed=7)
    assert ranked[0].mod.name == "Horror Bosses"


def test_loader_resolver_honors_manual_version():
    class Client:
        async def get_versions(self, project_id, mc, loader):
            return [{"version_number": "47.2.0", "version_type": "release"}]
    result = asyncio.run(LoaderResolver(Client()).resolve(LoaderType.FORGE, "1.20.1", "47.2.0"))
    assert result.version == "47.2.0" and result.source == "manual"


def test_loader_resolver_rejects_incompatible_manual_version():
    class Client:
        async def get_versions(self, project_id, mc, loader):
            return []
    with pytest.raises(LoaderResolutionError):
        asyncio.run(LoaderResolver(Client()).resolve(LoaderType.FORGE, "1.20.1", "bad"))
