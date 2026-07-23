"""1.7.2.1 hotfix regressions."""

import asyncio
from types import SimpleNamespace

from pydantic import BaseModel

from app.config import AIConfig
from app.services.ai_provider import OpenAICompatibleProvider
from app.services.prompt_pipeline import optimize_prompt


class Demo(BaseModel):
    value: int


class FakeCompletions:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='{"value": 1}'))])


class FakeClient:
    def __init__(self, completions: FakeCompletions) -> None:
        self.chat = SimpleNamespace(completions=completions)

    async def close(self) -> None:
        return None


def test_configured_model_skips_model_discovery_for_chat():
    completions = FakeCompletions()
    provider = OpenAICompatibleProvider(AIConfig(provider="ollama", model="local-model", base_url="http://localhost:11434/v1"))
    provider._client = FakeClient(completions)  # type: ignore[assignment]
    result = asyncio.run(provider.chat_json("system", "user", Demo))
    assert result.value == 1
    assert completions.calls[0]["model"] == "local-model"
    assert "response_format" in completions.calls[0]


def test_normalized_prompt_contains_explicit_minecraft_context():
    brief = optimize_prompt("Maak horror", minecraft_version="1.20.1", loader="forge", theme="horror", difficulty="hard", performance_preference="stability")
    assert "Minecraft 1.20.1" in brief.normalized_request
    assert "forge" in brief.normalized_request
