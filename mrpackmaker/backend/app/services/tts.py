"""Optional Text-to-Speech via an OpenAI-compatible endpoint.

A LiteLLM proxy (or OpenAI itself) exposes ``POST {base}/audio/speech``.  TTS is
disabled by default and requires both an address and a model to be configured
manually, because a proxy's model names are deployment-specific.
"""

from __future__ import annotations

import logging

import httpx

from app.config import VoiceConfig, config

logger = logging.getLogger(__name__)


class TTSError(RuntimeError):
    """TTS is misconfigured or the upstream request failed."""


class TTSClient:
    def __init__(self, settings: VoiceConfig | None = None) -> None:
        self._settings = settings or config.voice

    @property
    def ready(self) -> bool:
        s = self._settings
        return s.tts_enabled and bool(s.tts_base_url) and bool(s.tts_model)

    def _ensure_ready(self) -> None:
        if not self._settings.tts_enabled:
            raise TTSError("TTS is disabled")
        if not self._settings.tts_base_url:
            raise TTSError("TTS requires an address (base URL)")
        if not self._settings.tts_model:
            raise TTSError("TTS requires a model")

    async def synthesize(self, text: str, *, voice: str | None = None) -> tuple[bytes, str]:
        """Return (audio_bytes, content_type). Raises TTSError on any problem."""
        self._ensure_ready()
        text = (text or "").strip()
        if not text:
            raise TTSError("Nothing to synthesize")

        base = self._settings.tts_base_url.rstrip("/")
        headers = {"Content-Type": "application/json"}
        if self._settings.tts_api_key:
            headers["Authorization"] = f"Bearer {self._settings.tts_api_key}"
        payload = {
            "model": self._settings.tts_model,
            "input": text,
            "voice": voice or self._settings.tts_voice or "alloy",
        }
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(f"{base}/audio/speech", json=payload, headers=headers)
                resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error("TTS synthesis failed: %s", exc)
            raise TTSError(f"TTS endpoint returned {exc.response.status_code}") from exc
        except httpx.HTTPError as exc:
            logger.error("TTS synthesis failed: %s", exc)
            raise TTSError(f"Could not reach the TTS endpoint: {exc}") from exc

        content_type = resp.headers.get("content-type", "audio/mpeg")
        return resp.content, content_type
