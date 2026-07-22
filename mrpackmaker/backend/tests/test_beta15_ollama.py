"""Tests for beta 1.5: Ollama provider presets and JSON-mode fallback (no network)."""

from __future__ import annotations

import asyncio
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import PROVIDER_PRESETS, AIConfig, default_base_url_for
from app.services.ai_provider import OpenAICompatibleProvider, _is_response_format_error


class _Demo(BaseModel):
    value: int


class _BadRequest(Exception):
    """Stand-in for a provider rejecting an unknown parameter with HTTP 400."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


def _response(content: str) -> SimpleNamespace:
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


class _FakeCompletions:
    """Returns / raises a scripted sequence of outcomes and records each call."""

    def __init__(self, outcomes: list) -> None:
        self._outcomes = outcomes
        self.calls: list[dict] = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        outcome = self._outcomes[len(self.calls) - 1]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class _FakeClient:
    def __init__(self, completions: _FakeCompletions) -> None:
        self.chat = SimpleNamespace(completions=completions)

    async def close(self) -> None:  # pragma: no cover - parity with real client
        return None


class ProviderPresetTests(unittest.TestCase):
    def test_ollama_preset_base_url(self) -> None:
        self.assertEqual(default_base_url_for("ollama"), "http://localhost:11434/v1")
        self.assertEqual(default_base_url_for("OLLAMA"), "http://localhost:11434/v1")

    def test_known_presets_present(self) -> None:
        self.assertIn("lmstudio", PROVIDER_PRESETS)
        self.assertIn("ollama", PROVIDER_PRESETS)
        self.assertIn("litellm", PROVIDER_PRESETS)

    def test_unknown_provider_has_no_preset(self) -> None:
        self.assertIsNone(default_base_url_for("something-custom"))

    def test_ollama_is_a_valid_ai_config(self) -> None:
        cfg = AIConfig(provider="Ollama", base_url="http://localhost:11434/v1")
        self.assertEqual(cfg.provider, "ollama")  # normalised to lowercase
        self.assertEqual(cfg.base_url, "http://localhost:11434/v1")


class ResponseFormatErrorHeuristicTests(unittest.TestCase):
    def test_message_mentioning_response_format(self) -> None:
        self.assertTrue(_is_response_format_error(Exception("unknown field response_format")))

    def test_plain_400_is_treated_as_unsupported_param(self) -> None:
        self.assertTrue(_is_response_format_error(_BadRequest("Bad Request")))

    def test_unrelated_error_is_not_matched(self) -> None:
        self.assertFalse(_is_response_format_error(Exception("connection refused")))


class JsonModeFallbackTests(unittest.TestCase):
    def _provider(self, completions: _FakeCompletions) -> OpenAICompatibleProvider:
        provider = OpenAICompatibleProvider(AIConfig(provider="ollama", base_url="http://localhost:11434/v1"))
        provider._model = "test-model"  # skip network model discovery
        provider._client = _FakeClient(completions)  # type: ignore[assignment]
        return provider

    def test_retries_without_response_format_when_rejected(self) -> None:
        completions = _FakeCompletions([
            _BadRequest("this model does not support response_format"),
            _response('{"value": 7}'),
        ])
        provider = self._provider(completions)

        result = asyncio.run(provider.chat_json("system", "user", _Demo))

        self.assertEqual(result.value, 7)
        self.assertEqual(len(completions.calls), 2)
        self.assertIn("response_format", completions.calls[0])
        self.assertNotIn("response_format", completions.calls[1])
        self.assertFalse(provider._supports_json_mode)

    def test_keeps_json_mode_when_supported(self) -> None:
        completions = _FakeCompletions([_response('{"value": 1}')])
        provider = self._provider(completions)

        result = asyncio.run(provider.chat_json("system", "user", _Demo))

        self.assertEqual(result.value, 1)
        self.assertEqual(len(completions.calls), 1)
        self.assertIn("response_format", completions.calls[0])
        self.assertTrue(provider._supports_json_mode)


if __name__ == "__main__":
    unittest.main()
