"""Provider boundary for LM Studio, Ollama, LiteLLM and similar APIs.

All currently supported AI backends expose the OpenAI chat-completions shape.
Using one implementation behind a small protocol means adding a provider is a
configuration concern unless it genuinely has a different transport.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Protocol, TypeVar

from openai import AsyncOpenAI
from pydantic import BaseModel, ValidationError

from app.config import AIConfig, config

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class AIProviderError(RuntimeError):
    """A provider could not accept a request or return a usable response."""


def _is_response_format_error(exc: Exception) -> bool:
    """Heuristic: did a provider reject the ``response_format`` parameter?

    Not every OpenAI-compatible server implements JSON mode. Older Ollama
    builds and some LM Studio models return a 400 for the ``response_format``
    field. We detect that by the message text, or fall back to treating any
    Bad Request as a likely unsupported-parameter error, since the safe
    recovery (drop the flag and rely on the prompt) is harmless either way.
    """
    text = str(exc).lower()
    if "response_format" in text or "response format" in text or "json_object" in text:
        return True
    return getattr(exc, "status_code", None) == 400


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
        # Assume native JSON mode until a provider proves it does not support
        # it; once disabled we stop sending response_format for this instance.
        self._supports_json_mode: bool = True

    async def close(self) -> None:
        await self._client.close()

    async def list_models(self) -> list[str]:
        try:
            models = await self._client.models.list()
        except Exception as exc:  # SDK exception types vary by provider.
            raise AIProviderError(
                f"Could not list models from {self.provider_id}: {exc}"
            ) from exc
        # Some OpenAI-compatible servers respond 200 with a body that has no
        # `data` array (e.g. LM Studio reached on `/models` instead of
        # `/v1/models`, or a proxy returning a non-standard shape). Guard
        # against None so a misconfigured endpoint surfaces as 'not reachable'
        # rather than a 500 TypeError.
        return [model.id for model in (models.data or []) if model.id]

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

    async def _create_completion(self, model: str, messages: list[dict[str, str]]) -> Any:
        """Call chat-completions, transparently degrading JSON mode.

        If the provider rejects ``response_format`` (older Ollama builds, some
        models) we retry the same request once without it and rely on the
        prompt to keep the output JSON. The flag is remembered so subsequent
        calls on this instance skip the doomed attempt entirely.
        """
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": self._settings.temperature,
            "max_tokens": self._settings.max_tokens,
        }
        if self._supports_json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        try:
            return await self._client.chat.completions.create(**kwargs)  # type: ignore[arg-type]
        except Exception as exc:
            if self._supports_json_mode and _is_response_format_error(exc):
                logger.info(
                    "%s rejected response_format; retrying without JSON mode",
                    self.provider_id,
                )
                self._supports_json_mode = False
                kwargs.pop("response_format", None)
                return await self._client.chat.completions.create(**kwargs)  # type: ignore[arg-type]
            raise

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
                response = await self._create_completion(model, messages)
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
            except AIProviderError:
                raise
            except Exception as exc:
                raise AIProviderError(
                    f"{self.provider_id} failed while generating {schema.__name__}: {exc}"
                ) from exc

        raise AssertionError("JSON retry loop should either return or raise")


def create_ai_provider(settings: AIConfig | None = None) -> OpenAICompatibleProvider:
    """Create the configured provider without exposing configuration secrets."""
    return OpenAICompatibleProvider(settings or config.ai)
