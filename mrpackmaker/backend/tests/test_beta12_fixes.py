"""Regression tests for the beta 1.2 critical bug fixes."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models.enums import LoaderType
from app.models.project import Project
from app.schemas.mod import ModEntry, ModHash
from app.services import curseforge as cf_module
from app.services.curseforge import BASE_URL as CF_BASE_URL, CurseForgeClient, _pick_best_file
from app.services.modrinth import ModrinthClient
from app.services.mrpack_validation import validate_export_inputs


def _project() -> Project:
    return Project(
        name="Pack",
        description="d",
        minecraft_version="1.20.1",
        loader="fabric",
        theme="technology",
        difficulty="normal",
        performance_preference="balanced",
        resolved_loader_version="0.15.11",
    )


def _mod(url: str) -> ModEntry:
    return ModEntry(
        id="1",
        source="curseforge",
        name="Example",
        slug="example",
        file_name="example.jar",
        file_size=10,
        download_url=url,
        hashes=ModHash(sha1="a" * 40),
    )


class DownloadAllowlistTests(unittest.TestCase):
    def test_forgecdn_host_is_rejected(self) -> None:
        mod = _mod("https://edge.forgecdn.net/files/123/456/example.jar")
        codes = [issue.code for issue in validate_export_inputs(_project(), [mod])]
        self.assertIn("download_host_not_allowed", codes)

    def test_modrinth_cdn_host_is_allowed(self) -> None:
        mod = _mod("https://cdn.modrinth.com/data/AB/versions/1/example.jar")
        codes = [issue.code for issue in validate_export_inputs(_project(), [mod])]
        self.assertNotIn("download_host_not_allowed", codes)


class ModrinthVersionSelectionTests(unittest.TestCase):
    def test_release_is_preferred_over_newer_beta(self) -> None:
        versions = [
            {"version_number": "beta-new", "version_type": "beta", "date_published": "2024-05-01T00:00:00Z"},
            {"version_number": "rel-old", "version_type": "release", "date_published": "2023-01-01T00:00:00Z"},
            {"version_number": "rel-new", "version_type": "release", "date_published": "2023-09-01T00:00:00Z"},
        ]
        best = ModrinthClient.select_best_version(versions)
        self.assertEqual(best["version_number"], "rel-new")

    def test_empty_versions_return_none(self) -> None:
        self.assertIsNone(ModrinthClient.select_best_version([]))


class CurseForgeFileSelectionTests(unittest.TestCase):
    def test_picks_newest_file_matching_loader_and_version(self) -> None:
        files = [
            {"id": 1, "fileDate": "2024-01-01T00:00:00Z", "gameVersions": ["1.20.1", "Fabric"]},
            {"id": 2, "fileDate": "2024-05-01T00:00:00Z", "gameVersions": ["1.20.1", "Forge"]},
            {"id": 3, "fileDate": "2023-01-01T00:00:00Z", "gameVersions": ["1.20.1", "Fabric"]},
        ]
        chosen = _pick_best_file(files, "1.20.1", LoaderType.FABRIC)
        self.assertEqual(chosen["id"], 1)  # newest Fabric build, not the newer Forge one

    def test_no_files_returns_none(self) -> None:
        self.assertIsNone(_pick_best_file([], "1.20.1", LoaderType.FABRIC))


class CurseForgeSearchTests(unittest.IsolatedAsyncioTestCase):
    async def test_search_restricts_to_mods_class(self) -> None:
        cf_module.search_cache.clear()
        captured: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured.update(dict(request.url.params))
            return httpx.Response(200, json={"data": [], "pagination": {"totalCount": 0}})

        client = CurseForgeClient(api_key="test-key")
        client._client = httpx.AsyncClient(base_url=CF_BASE_URL, transport=httpx.MockTransport(handler))
        try:
            await client.search("storage", "1.20.1", LoaderType.FABRIC)
        finally:
            await client.close()

        self.assertEqual(captured.get("classId"), "6")


if __name__ == "__main__":
    unittest.main()
