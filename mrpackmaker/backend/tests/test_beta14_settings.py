"""Tests for the beta 1.4 secure-settings config additions (no network)."""

from __future__ import annotations

import asyncio
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import AIConfig, MinecraftConfig, SourcesConfig
from app.schemas.settings import ApiTestResult
# Import the module (not the function) so pytest does not collect the imported
# `test_curseforge` coroutine as a test case.
from app.services import api_tester


class AIConfigContextSizeTests(unittest.TestCase):
    def test_default_and_valid_range(self) -> None:
        self.assertEqual(AIConfig().context_size, 4096)
        self.assertEqual(AIConfig(context_size=16384).context_size, 16384)

    def test_out_of_range_rejected(self) -> None:
        with self.assertRaises(ValueError):
            AIConfig(context_size=100)


class MinecraftAndSourcesConfigTests(unittest.TestCase):
    def test_minecraft_defaults(self) -> None:
        mc = MinecraftConfig()
        self.assertEqual(mc.default_version, "1.21.1")
        self.assertEqual(mc.default_loader, "neoforge")

    def test_loader_is_normalised(self) -> None:
        self.assertEqual(MinecraftConfig(default_loader="NeoForge").default_loader, "neoforge")

    def test_sources_default_enabled(self) -> None:
        sources = SourcesConfig()
        self.assertTrue(sources.modrinth_enabled)
        self.assertTrue(sources.curseforge_enabled)


class ApiTestResultTests(unittest.TestCase):
    def test_shape(self) -> None:
        result = ApiTestResult(ok=True, service="ai", status_code=200, latency_ms=42, info={"model": "x"})
        self.assertTrue(result.ok)
        self.assertEqual(result.info["model"], "x")


class CurseForgeTesterTests(unittest.TestCase):
    def test_no_key_returns_actionable_failure_without_network(self) -> None:
        result = asyncio.run(api_tester.test_curseforge(""))
        self.assertFalse(result.ok)
        self.assertEqual(result.service, "curseforge")
        self.assertIn("key", (result.detail or "").lower())


if __name__ == "__main__":
    unittest.main()
