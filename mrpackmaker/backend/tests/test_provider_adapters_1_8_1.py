import json

import pytest

from app.adapters.ai.openai_compatible_adapter import OpenAICompatibleAdapter
from app.adapters.catalog.curseforge_adapter import CurseForgeAdapter
from app.adapters.catalog.modrinth_adapter import ModrinthAdapter
from app.adapters.errors import InvalidResponseError
from app.domain.common import Loader, ModSource
from app.domain.mods.models import CanonicalModIdentity
from app.domain.providers.protocols import AIProvider, CurseForgeProvider, ModrinthProvider
from app.schemas.ai import ModRanking
from app.schemas.mod import ModEntry, ModHash


def entry(source: str = "modrinth", *, detailed: bool = True) -> ModEntry:
    return ModEntry(id="abc", source=source, name="Example", slug="example", summary="A test mod", downloads=12, categories=["horror"], loaders=["fabric"], selected_version="1.20.1", file_name="example.jar" if detailed else None, download_url="https://example.invalid/example.jar" if detailed else None, hashes=ModHash(sha512="sha512-value" if detailed else None))


class FakeModrinth:
    async def search(self, query, mc_version, loader, **kwargs): return [entry() ], 1
    async def get_mod_detail(self, project_id, mc_version, loader): return entry(detailed=True)


class FakeCurseForge(FakeModrinth):
    pass


@pytest.mark.asyncio
async def test_modrinth_mapping_and_protocol():
    adapter = ModrinthAdapter(FakeModrinth(), "1.20.1", Loader.FABRIC)
    result = await adapter.search("horror", minecraft_version="1.20.1", loader=Loader.FABRIC)
    assert isinstance(adapter, ModrinthProvider)
    assert result[0].identity.sources["modrinth"] == "abc"
    assert json.loads(json.dumps(result[0].to_dict()))["source"] == "modrinth"


@pytest.mark.asyncio
async def test_curseforge_mapping_and_protocol():
    adapter = CurseForgeAdapter(FakeCurseForge(), "1.20.1", Loader.FABRIC)
    result = await adapter.get("abc")
    assert isinstance(adapter, CurseForgeProvider)
    assert result is not None and result.source is ModSource.CURSEFORGE
    assert result.files[0].sha512 == "sha512-value"


@pytest.mark.asyncio
async def test_missing_catalog_fields_raise_typed_error():
    adapter = ModrinthAdapter(FakeModrinth(), "1.20.1", Loader.FABRIC)
    class Missing:
        async def get_mod_detail(self, *args): return entry(detailed=False)
    adapter = ModrinthAdapter(Missing(), "1.20.1", Loader.FABRIC)
    with pytest.raises(InvalidResponseError):
        await adapter.get("abc")


class FakeAI:
    provider_id = "test-provider"
    async def chat_json(self, system_prompt, user_prompt, schema):
        return ModRanking(selected_ids=["abc"], reasoning="matches request")
    async def close(self): pass


@pytest.mark.asyncio
async def test_ai_adapter_capabilities_and_candidate_boundary():
    adapter = OpenAICompatibleAdapter(FakeAI(), minecraft_version="1.20.1", loader=Loader.FABRIC, theme="horror")
    assert isinstance(adapter, AIProvider)
    profile = await adapter.analyze_requirements("horror QoL, minimaal 1 mods")
    brief = await adapter.build_brief(profile)
    identity = CanonicalModIdentity("modrinth:abc", "Example", {ModSource.MODRINTH: "abc"})
    from app.domain.mods.models import ModCandidate
    candidate = ModCandidate(identity, ModSource.MODRINTH, "abc", "example", "Example", "desc", 1, frozenset())
    selected = await adapter.select(brief, [candidate])
    assert selected[0].candidate is candidate and selected[0].reason == "matches request"


@pytest.mark.asyncio
async def test_ai_unknown_candidate_is_rejected():
    class BadAI(FakeAI):
        async def chat_json(self, system_prompt, user_prompt, schema): return ModRanking(selected_ids=["missing"])
    adapter = OpenAICompatibleAdapter(BadAI(), minecraft_version="1.20.1", loader=Loader.FABRIC)
    profile = await adapter.analyze_requirements("horror")
    brief = await adapter.build_brief(profile)
    identity = CanonicalModIdentity("modrinth:abc", "Example", {ModSource.MODRINTH: "abc"})
    from app.domain.mods.models import ModCandidate
    candidate = ModCandidate(identity, ModSource.MODRINTH, "abc", "example", "Example", "desc", 1, frozenset())
    with pytest.raises(InvalidResponseError):
        await adapter.select(brief, [candidate])
