"""Regression tests for search, secrets, config and TTS guards."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import AIConfig, VoiceConfig
from app.models.enums import LoaderType
from app.services import modrinth as modrinth_module
from app.services.modrinth import BASE_URL, ModrinthClient
from app.services.secret_store import SecretStore
from app.services.tts import TTSClient, TTSError


class ModrinthFacetsTests(unittest.IsolatedAsyncioTestCase):
    """The original 'no mods' bug: facets must be one JSON array-of-arrays."""

    async def test_facets_are_a_single_json_array_param(self) -> None:
        modrinth_module.search_cache.clear()
        captured: dict[str, list[str]] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["facets"] = request.url.params.get_list("facets")
            return httpx.Response(200, json={"hits": [], "total_hits": 0})

        client = ModrinthClient()
        client._client = httpx.AsyncClient(base_url=BASE_URL, transport=httpx.MockTransport(handler))
        try:
            await client.search("storage automation", "1.20.1", LoaderType.FABRIC)
        finally:
            await client.close()

        self.assertEqual(len(captured["facets"]), 1)
        parsed = json.loads(captured["facets"][0])
        self.assertTrue(parsed and all(isinstance(group, list) for group in parsed))
        self.assertIn(["project_type:mod"], parsed)
        self.assertIn(["versions:1.20.1"], parsed)
        # Modrinth's v2 search index exposes loaders through categories.
        self.assertIn(["categories:fabric"], parsed)
        self.assertNotIn(["loaders:fabric"], parsed)


class SecretStoreTests(unittest.TestCase):
    def test_round_trip_update_and_remove(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = SecretStore(Path(directory))
            store.update({"modrinth_key": "abc123", "ai_api_key": "sk-test"})
            self.assertEqual(store.load()["modrinth_key"], "abc123")
            store.remove(["modrinth_key"])
            reloaded = store.load()
            self.assertNotIn("modrinth_key", reloaded)
            self.assertEqual(reloaded["ai_api_key"], "sk-test")
            store.remove(["does_not_exist"])
            self.assertEqual(store.load()["ai_api_key"], "sk-test")


class ConfigValidationTests(unittest.TestCase):
    def test_base_url_is_normalised(self) -> None:
        self.assertEqual(AIConfig(base_url="http://localhost:1234/v1/").base_url, "http://localhost:1234/v1")

    def test_base_url_scheme_is_validated(self) -> None:
        with self.assertRaises(ValueError):
            AIConfig(base_url="ftp://localhost")

    def test_tts_enabled_reflects_provider(self) -> None:
        self.assertFalse(VoiceConfig(tts_provider="disabled").tts_enabled)
        self.assertFalse(VoiceConfig(tts_provider="").tts_enabled)
        self.assertTrue(VoiceConfig(tts_provider="litellm").tts_enabled)


class TTSGuardTests(unittest.IsolatedAsyncioTestCase):
    async def test_disabled_provider_raises(self) -> None:
        client = TTSClient(VoiceConfig(tts_provider="disabled"))
        self.assertFalse(client.ready)
        with self.assertRaises(TTSError):
            await client.synthesize("hello")

    async def test_missing_address_or_model_raises(self) -> None:
        client = TTSClient(VoiceConfig(tts_provider="litellm", tts_base_url="", tts_model=""))
        self.assertFalse(client.ready)
        with self.assertRaises(TTSError):
            await client.synthesize("hello")


if __name__ == "__main__":
    unittest.main()
