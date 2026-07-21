"""Tests for the AI-free quick generation path (beta 1.3)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models.enums import LoaderType
from app.models.project import Project
from app.schemas.mod import ModEntry, ModHash
from app.services.ai_orchestrator import POPULAR_FALLBACK_QUERIES, AIOrchestrator
from app.services.mod_resolver import ModResolver
from app.services.source_registry import ModSourceRegistry


def _project(theme: str = "technology", theme_custom: str | None = None) -> Project:
    return Project(
        name="Pack",
        description="d",
        minecraft_version="1.20.1",
        loader="fabric",
        theme=theme,
        theme_custom=theme_custom,
        difficulty="normal",
        performance_preference="balanced",
        generation_prompt="futuristic automation machines",
    )


def _mod(source: str, mod_id: str) -> ModEntry:
    return ModEntry(
        id=mod_id,
        source=source,
        name=f"{source}-{mod_id}",
        slug=f"{source}-{mod_id}",
        file_name=f"{source}-{mod_id}.jar",
        file_size=10,
        download_url="https://cdn.modrinth.com/data/AB/versions/1/x.jar",
        hashes=ModHash(sha1="a" * 40),
        downloads=100,
    )


class _FakeSource:
    def __init__(self, source_id: str, *, fail: bool = False) -> None:
        self.source_id = source_id
        self.available = True
        self._fail = fail
        self.queries: list[str] = []

    async def search(self, query, mc_version, loader, category=None, limit=20, offset=0):
        self.queries.append(query)
        if self._fail:
            raise RuntimeError("boom")
        return [_mod(self.source_id, "1")], 1

    async def get_mod_detail(self, mod_id, mc_version, loader):
        return _mod(self.source_id, mod_id)

    async def close(self):
        return None


class FallbackQueriesTests(unittest.TestCase):
    def test_always_non_empty_and_theme_aware(self) -> None:
        queries = AIOrchestrator._fallback_queries(_project(theme="technology"), "automation machines storage")
        self.assertTrue(queries)
        self.assertIn("technology", queries)

    def test_custom_theme_is_included(self) -> None:
        queries = AIOrchestrator._fallback_queries(_project(theme="custom", theme_custom="Steampunk"), "")
        self.assertIn("Steampunk", queries)

    def test_empty_prompt_still_yields_popular_queries(self) -> None:
        queries = AIOrchestrator._fallback_queries(_project(theme="custom"), "")
        for term in POPULAR_FALLBACK_QUERIES:
            self.assertIn(term, queries)


class GatherCandidatesTests(unittest.IsolatedAsyncioTestCase):
    async def test_includes_broad_query_and_dedupes(self) -> None:
        source = _FakeSource("modrinth")
        registry = ModSourceRegistry([source])
        resolver = ModResolver(registry=registry)
        orch = AIOrchestrator()

        result = await orch._gather_candidates(registry, resolver, ["storage"], "1.20.1", LoaderType.FABRIC)

        # The broad popularity query ("") must always be searched.
        self.assertIn("", source.queries)
        # Same mod returned for both queries collapses to one candidate.
        self.assertEqual(len(result), 1)
        await registry.close()

    async def test_one_failing_source_does_not_abort(self) -> None:
        good = _FakeSource("modrinth")
        bad = _FakeSource("curseforge", fail=True)
        registry = ModSourceRegistry([bad, good])
        resolver = ModResolver(registry=registry)
        orch = AIOrchestrator()

        result = await orch._gather_candidates(registry, resolver, ["storage"], "1.20.1", LoaderType.FABRIC)

        self.assertEqual([m.source for m in result], ["modrinth"])
        await registry.close()


if __name__ == "__main__":
    unittest.main()
