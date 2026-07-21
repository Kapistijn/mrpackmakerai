"""Provider boundary for LM Studio, LiteLLM/Ollama and similar APIs.

All currently supported AI backends expose the OpenAI chat-completions shape.
Using one implementation behind a small protocol means adding a provider is a
configuration concern unless it genuinely has a different transport.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Protocol, TypeVar

from openai import AsyncOpenAI
from pydantic import BaseModel, ValidationError

from app.config import AIConfig, config

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class AIProviderError(RuntimeError):
    """A provider could not accept a request or return a usable response."""


@dataclass(frozen=True)
class ProviderConnection:
    provider: str
    reachable: bool
    active_model: str | None = None
    detail: str | None = None


class AIProvider(Protocol):
    provider_id: str

    async def list_models(self) -> list[str]: ...

    async def connection_status(self) -> ProviderConnection: ...

    async def chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: type[T],
    ) -> T: ...

    async def close(self) -> None: ...


class OpenAICompatibleProvider:
    """Robust client for a local or remote OpenAI-compatible endpoint."""

    def __init__(self, settings: AIConfig) -> None:
        self.provider_id = settings.provider
        self._settings = settings
        self._client = AsyncOpenAI(
            base_url=settings.base_url,
            # The OpenAI SDK requires a value even when a local provider does
            # not authenticate.  The placeholder is never sent as a real user
            # secret and local endpoints generally ignore it.
            api_key=settings.api_key or "local-provider",
            timeout=settings.timeout_seconds,
            max_retries=1,
        )
        self._model: str | None = settings.model or None

    async def close(self) -> None:
        await self._client.close()

    async def list_models(self) -> list[str]:
        try:
            models = await self._client.models.list()
        except Exception as exc:  # SDK exception types vary by provider.
            raise AIProviderError(
                f"Could not list models from {self.provider_id}: {exc}"
            ) from exc
        return [model.id for model in models.data if model.id]

    async def get_model(self) -> str:
        if self._model:
            return self._model
        models = await self.list_models()
        if not models:
            raise AIProviderError(f"{self.provider_id} did not expose a loaded model")
        self._model = models[0]
        logger.info("Auto-selected model '%s' from %s", self._model, self.provider_id)
        return self._model

    async def connection_status(self) -> ProviderConnection:
        try:
            # Do not treat a configured model name as a successful connection:
            # the models request verifies that the endpoint is actually alive.
            models = await self.list_models()
            model = self._model or (models[0] if models else None)
            if not model:
                raise AIProviderError(f"{self.provider_id} did not expose a loaded model")
            self._model = model
            return ProviderConnection(
                provider=self.provider_id,
                reachable=True,
                active_model=model,
            )
        except AIProviderError as exc:
            return ProviderConnection(
                provider=self.provider_id,
                reachable=False,
                detail=str(exc),
            )

    async def is_available(self) -> bool:
        """Compatibility helper used by the old health endpoint and scripts."""
        return (await self.connection_status()).reachable

    async def chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: type[T],
    ) -> T:
        model = await self.get_model()
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        for attempt in range(2):
            try:
                response = await self._client.chat.completions.create(
                    model=model,
                    messages=messages,  # type: ignore[arg-type]
                    temperature=self._settings.temperature,
                    max_tokens=self._settings.max_tokens,
                    response_format={"type": "json_object"},
                )
                content = response.choices[0].message.content or "{}"
                return schema.model_validate(json.loads(content))
            except (json.JSONDecodeError, ValidationError) as exc:
                if attempt:
                    raise AIProviderError(
                        f"{self.provider_id} returned invalid {schema.__name__} JSON"
                    ) from exc
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "Return only valid JSON that matches "
                            f"the {schema.__name__} schema."
                        ),
                    }
                )
            except Exception as exc:
                raise AIProviderError(
                    f"{self.provider_id} failed while generating {schema.__name__}: {exc}"
                ) from exc

        raise AssertionError("JSON retry loop should either return or raise")


def create_ai_provider(settings: AIConfig | None = None) -> OpenAICompatibleProvider:
    """Create the configured provider without exposing configuration secrets."""
    return OpenAICompatibleProvider(settings or config.ai)
